from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN

from django.db import transaction
from django.db.models import Count, Max, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from Employees.models import Employee
from Users.permissions import IsTenantAdmin

from .models import Loan, LoanInstallment


def add_months(value, months):
    index = value.month - 1 + months
    year = value.year + index // 12
    month = index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def parse_decimal(value, field, errors, allow_zero=False):
    try:
        result = Decimal(str(value))
        if result < 0 or (result == 0 and not allow_zero):
            raise InvalidOperation
        return result
    except (InvalidOperation, TypeError, ValueError):
        errors[field] = "Ingresá un importe válido."
        return None


def installment_to_dict(item):
    return {
        "id": item.id,
        "number": item.number,
        "period": item.period,
        "expected_amount": item.expected_amount,
        "paid_amount": item.paid_amount,
        "status": item.status,
        "payment_date": item.payment_date,
        "payment_method": item.payment_method,
        "notes": item.notes,
    }


def loan_to_dict(loan, include_installments=False):
    paid = loan.paid_amount
    data = {
        "id": loan.id,
        "person_type": loan.person_type,
        "person_name": loan.person_name,
        "employee": ({"id": loan.employee_id, "nombre": loan.employee.nombre, "apellido": loan.employee.apellido} if loan.employee_id else None),
        "external_name": loan.external_name,
        "external_document": loan.external_document,
        "total_amount": loan.total_amount,
        "paid_amount": paid,
        "balance": max(loan.total_amount - paid, Decimal("0")),
        "delivery_date": loan.delivery_date,
        "first_installment_period": loan.first_installment_period,
        "installment_count": loan.installment_count,
        "delivery_method": loan.delivery_method,
        "notes": loan.notes,
        "status": loan.status,
        "next_installment": None,
    }
    pending = loan.installments.exclude(
        status__in=[LoanInstallment.Status.PAID, LoanInstallment.Status.SKIPPED]
    ).order_by("number").first()
    if pending:
        data["next_installment"] = installment_to_dict(pending)
    if include_installments:
        data["installments"] = [installment_to_dict(item) for item in loan.installments.all()]
    return data


def validate_loan_payload(data, partial=False):
    errors = {}
    cleaned = {}
    required = ["person_type", "total_amount", "delivery_date", "first_installment_period", "installment_count"]
    if not partial:
        for field in required:
            if data.get(field) in (None, ""):
                errors[field] = "Este campo es obligatorio."

    person_type = data.get("person_type")
    if person_type is not None:
        if person_type not in Loan.PersonType.values:
            errors["person_type"] = "Tipo de persona inválido."
        else:
            cleaned["person_type"] = person_type

    if "total_amount" in data:
        cleaned["total_amount"] = parse_decimal(data.get("total_amount"), "total_amount", errors)

    if "installment_count" in data:
        try:
            count = int(data.get("installment_count"))
            if count < 1 or count > 240:
                raise ValueError
            cleaned["installment_count"] = count
        except (TypeError, ValueError):
            errors["installment_count"] = "La cantidad de cuotas debe estar entre 1 y 240."

    for field in ["delivery_date", "first_installment_period", "delivery_method", "notes", "external_document"]:
        if field in data:
            cleaned[field] = data.get(field) or ""

    if "first_installment_period" in cleaned and cleaned["first_installment_period"]:
        try:
            parsed = date.fromisoformat(str(cleaned["first_installment_period"]))
            cleaned["first_installment_period"] = parsed.replace(day=1)
        except ValueError:
            errors["first_installment_period"] = "Período inválido."

    if "delivery_date" in cleaned and cleaned["delivery_date"]:
        try:
            cleaned["delivery_date"] = date.fromisoformat(str(cleaned["delivery_date"]))
        except ValueError:
            errors["delivery_date"] = "Fecha inválida."

    if person_type == Loan.PersonType.EMPLOYEE:
        employee = Employee.objects.filter(id=data.get("employee_id")).first()
        if not employee:
            errors["employee_id"] = "Seleccioná un empleado válido."
        else:
            cleaned["employee"] = employee
        cleaned["external_name"] = ""
    elif person_type == Loan.PersonType.EXTERNAL:
        name = str(data.get("external_name", "")).strip()
        if not name:
            errors["external_name"] = "El nombre de la persona es obligatorio."
        cleaned["external_name"] = name
        cleaned["employee"] = None

    return cleaned, errors


def create_installments(loan):
    base = (loan.total_amount / loan.installment_count).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    allocated = Decimal("0")
    items = []
    for index in range(loan.installment_count):
        amount = loan.total_amount - allocated if index == loan.installment_count - 1 else base
        allocated += amount
        items.append(LoanInstallment(loan=loan, number=index + 1, period=add_months(loan.first_installment_period, index), expected_amount=amount))
    LoanInstallment.objects.bulk_create(items)


def sync_loan_totals(loan):
    """Keep the loan summary in sync with its persisted installment schedule."""
    summary = loan.installments.aggregate(
        count=Count("id"),
        total=Sum("expected_amount"),
    )
    loan.installment_count = summary["count"]
    loan.total_amount = summary["total"] or Decimal("0")
    loan.save(update_fields=["installment_count", "total_amount", "updated_at"])
    loan.refresh_status()


class LoanListCreateAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get(self, request):
        loans = Loan.objects.select_related("employee").prefetch_related("installments").all()
        visible = loans.exclude(status=Loan.Status.CANCELLED)
        today = timezone.localdate().replace(day=1)
        kpis = {
            "total_lent": visible.aggregate(value=Sum("total_amount"))["value"] or Decimal("0"),
            "outstanding_balance": sum((loan.balance for loan in visible), Decimal("0")),
            "collected_this_month": LoanInstallment.objects.filter(loan__status__in=[Loan.Status.ACTIVE, Loan.Status.PAID], payment_date__year=today.year, payment_date__month=today.month).aggregate(value=Sum("paid_amount"))["value"] or Decimal("0"),
            "overdue_installments": LoanInstallment.objects.filter(loan__status=Loan.Status.ACTIVE, period__lt=today, status__in=[LoanInstallment.Status.PENDING, LoanInstallment.Status.PARTIAL]).count(),
            "active_loans": visible.filter(status=Loan.Status.ACTIVE).count(),
        }
        return Response({"count": loans.count(), "loans": [loan_to_dict(loan) for loan in loans], "kpis": kpis})

    def post(self, request):
        cleaned, errors = validate_loan_payload(request.data)
        if errors:
            return Response({"detail": "Revisá los datos ingresados.", "errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            loan = Loan.objects.create(**cleaned)
            create_installments(loan)
        loan = Loan.objects.select_related("employee").prefetch_related("installments").get(id=loan.id)
        return Response(loan_to_dict(loan, True), status=status.HTTP_201_CREATED)


class LoanDetailAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get_loan(self, loan_id):
        return Loan.objects.select_related("employee").prefetch_related("installments").filter(id=loan_id).first()

    def get(self, request, loan_id):
        loan = self.get_loan(loan_id)
        return Response(loan_to_dict(loan, True)) if loan else Response({"detail": "Préstamo no encontrado."}, status=404)

    def patch(self, request, loan_id):
        loan = self.get_loan(loan_id)
        if not loan:
            return Response({"detail": "Préstamo no encontrado."}, status=404)
        if "status" in request.data:
            value = request.data["status"]
            if value not in Loan.Status.values:
                return Response({"detail": "Estado inválido."}, status=400)
            loan.status = value
        for field in ["delivery_method", "notes", "external_document"]:
            if field in request.data:
                setattr(loan, field, request.data.get(field) or "")
        loan.save()
        return Response(loan_to_dict(loan, True))

    def delete(self, request, loan_id):
        loan = self.get_loan(loan_id)
        if not loan:
            return Response({"detail": "Préstamo no encontrado."}, status=404)
        loan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoanInstallmentDetailAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    @transaction.atomic
    def patch(self, request, loan_id, installment_id):
        item = LoanInstallment.objects.select_related("loan").filter(id=installment_id, loan_id=loan_id).first()
        if not item:
            return Response({"detail": "Cuota no encontrada."}, status=404)
        errors = {}
        if "expected_amount" in request.data:
            value = parse_decimal(request.data["expected_amount"], "expected_amount", errors)
            if value is not None:
                item.expected_amount = value
        if "period" in request.data:
            try:
                item.period = date.fromisoformat(str(request.data["period"])).replace(day=1)
            except (TypeError, ValueError):
                errors["period"] = "Período inválido."
        if "paid_amount" in request.data:
            value = parse_decimal(request.data["paid_amount"], "paid_amount", errors, allow_zero=True)
            if value is not None:
                item.paid_amount = value
        requested_status = request.data.get("status")
        if requested_status == LoanInstallment.Status.SKIPPED:
            item.status = requested_status
            item.paid_amount = Decimal("0")
            item.payment_date = None
        elif requested_status is not None and requested_status not in LoanInstallment.Status.values:
            errors["status"] = "Estado inválido."
        elif requested_status is not None:
            item.status = requested_status
        else:
            item.status = LoanInstallment.Status.PAID if item.paid_amount >= item.expected_amount else (LoanInstallment.Status.PARTIAL if item.paid_amount > 0 else LoanInstallment.Status.PENDING)
        for field in ["payment_method", "notes"]:
            if field in request.data:
                setattr(item, field, request.data.get(field) or "")
        if "payment_date" in request.data:
            item.payment_date = request.data.get("payment_date") or None
        if errors:
            return Response({"detail": "Revisá los datos ingresados.", "errors": errors}, status=400)
        item.save()
        sync_loan_totals(item.loan)
        return Response(installment_to_dict(item))

    @transaction.atomic
    def delete(self, request, loan_id, installment_id):
        item = LoanInstallment.objects.select_related("loan").filter(
            id=installment_id,
            loan_id=loan_id,
        ).first()
        if not item:
            return Response({"detail": "Cuota no encontrada."}, status=404)
        loan = item.loan
        if loan.installments.count() <= 1:
            return Response(
                {"detail": "El préstamo debe conservar al menos una cuota."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item.delete()
        remaining = list(loan.installments.order_by("number"))
        for number, installment in enumerate(remaining, start=1):
            if installment.number != number:
                installment.number = number
        LoanInstallment.objects.bulk_update(remaining, ["number"])
        sync_loan_totals(loan)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoanInstallmentListCreateAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    @transaction.atomic
    def post(self, request, loan_id):
        loan = Loan.objects.filter(id=loan_id).first()
        if not loan:
            return Response({"detail": "Préstamo no encontrado."}, status=404)
        if loan.installments.count() >= 240:
            return Response(
                {"detail": "El préstamo no puede tener más de 240 cuotas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        errors = {}
        expected_amount = parse_decimal(request.data.get("expected_amount"), "expected_amount", errors)
        try:
            period = date.fromisoformat(str(request.data.get("period"))).replace(day=1)
        except (TypeError, ValueError):
            period = None
            errors["period"] = "Seleccioná un período válido."

        if errors:
            return Response(
                {"detail": "Revisá los datos ingresados.", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        last_number = loan.installments.aggregate(value=Max("number"))["value"] or 0
        item = LoanInstallment.objects.create(
            loan=loan,
            number=last_number + 1,
            period=period,
            expected_amount=expected_amount,
            notes=str(request.data.get("notes") or "").strip(),
        )
        sync_loan_totals(loan)
        return Response(installment_to_dict(item), status=status.HTTP_201_CREATED)
