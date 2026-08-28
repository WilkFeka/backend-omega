from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db.models import Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from Users.permissions import IsTenantAdmin
from .models import Expense


def parse_period(value):
    try:
        text = str(value or "")
        if len(text) == 7:
            text += "-01"
        return date.fromisoformat(text).replace(day=1)
    except ValueError:
        return None


def parse_amount(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
        return amount if amount > 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def expense_to_dict(item):
    return {"id": item.id, "period": item.period, "category": item.category, "description": item.description, "amount": item.amount, "observation": item.observation, "copied_from_id": item.copied_from_id}


def add_months(value, months):
    index = value.month - 1 + months
    year = value.year + index // 12
    month = index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def validate_payload(data, current=None):
    period = parse_period(data.get("period", current.period if current else None))
    category = data.get("category", current.category if current else None)
    description = str(data.get("description", current.description if current else "") or "").strip()
    amount = parse_amount(data.get("amount", current.amount if current else None))
    observation = str(data.get("observation", current.observation if current else "") or "").strip()
    errors = {}
    if not period: errors["period"] = "Período inválido."
    if category not in Expense.Category.values: errors["category"] = "Categoría inválida."
    if not description: errors["description"] = "La descripción es obligatoria."
    if amount is None: errors["amount"] = "Ingresá un importe mayor a cero."
    return {"period": period, "category": category, "description": description, "amount": amount, "observation": observation}, errors


class ExpenseListCreateAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get(self, request):
        period = parse_period(request.query_params.get("periodo"))
        if not period:
            return Response({"detail": "Período inválido."}, status=400)
        items = Expense.objects.filter(period=period)
        totals = {category: items.filter(category=category).aggregate(value=Sum("amount"))["value"] or Decimal("0") for category in Expense.Category.values}
        return Response({"period": period, "count": items.count(), "total": sum(totals.values(), Decimal("0")), "totals": totals, "expenses": [expense_to_dict(item) for item in items]})

    def post(self, request):
        cleaned, errors = validate_payload(request.data)
        if errors: return Response({"detail": "Revisá los datos ingresados.", "errors": errors}, status=400)
        item = Expense.objects.create(**cleaned)
        return Response(expense_to_dict(item), status=status.HTTP_201_CREATED)


class ExpenseDetailAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get_item(self, expense_id):
        return Expense.objects.filter(id=expense_id).first()

    def patch(self, request, expense_id):
        item = self.get_item(expense_id)
        if not item: return Response({"detail": "Gasto no encontrado."}, status=404)
        cleaned, errors = validate_payload(request.data, item)
        if errors: return Response({"detail": "Revisá los datos ingresados.", "errors": errors}, status=400)
        for field, value in cleaned.items(): setattr(item, field, value)
        item.save()
        return Response(expense_to_dict(item))

    def delete(self, request, expense_id):
        item = self.get_item(expense_id)
        if not item: return Response({"detail": "Gasto no encontrado."}, status=404)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExpenseCopyPreviousAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get(self, request):
        target_period = parse_period(request.query_params.get("periodo"))
        if not target_period:
            return Response({"detail": "Período inválido."}, status=400)
        previous_period = add_months(target_period, -1)
        items = Expense.objects.filter(period=previous_period)
        return Response({"period": previous_period, "expenses": [expense_to_dict(item) for item in items]})

    def post(self, request):
        target_period = parse_period(request.data.get("period"))
        raw_ids = request.data.get("expense_ids")
        if not target_period or not isinstance(raw_ids, list):
            return Response({"detail": "Revisá el período y la selección."}, status=400)
        previous_period = add_months(target_period, -1)
        selected = list(Expense.objects.filter(id__in=raw_ids, period=previous_period))
        already_copied = set(Expense.objects.filter(period=target_period, copied_from_id__in=[item.id for item in selected]).values_list("copied_from_id", flat=True))
        copies = [Expense(period=target_period, category=item.category, description=item.description, amount=None, observation=item.observation, copied_from=item) for item in selected if item.id not in already_copied]
        Expense.objects.bulk_create(copies)
        return Response({"created": len(copies), "skipped": len(selected) - len(copies)}, status=status.HTTP_201_CREATED)
