import traceback
import pprint as pp

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, models, transaction

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from Employees.models import Employee
from Tenancy.context import get_tenant_db
from Users.permissions import IsTenantAdmin

from .models import Salary, SalaryAdditional, SalaryDiscount


# ====================== HELPERS ======================

def employee_to_dict(employee):
    return {
        "id": employee.id,
        "nombre": employee.nombre,
        "apellido": employee.apellido,
        "matricula": employee.matricula,
        "gremio": employee.gremio,
        "group": (
            {"id": employee.group_id, "nombre": employee.group.nombre}
            if employee.group_id else None
        )
    }


def discount_to_dict(discount):
    return {
        "id": discount.id,
        "descripcion": discount.descripcion,
        "importe": str(discount.importe)
    }


def additional_to_dict(additional):
    return {
        "id": additional.id,
        "descripcion": additional.descripcion,
        "importe": str(additional.importe)
    }


def salary_to_dict(salary, detail=False):
    data = {
        "id": salary.id,
        "employee": employee_to_dict(salary.employee),

        "periodo": salary.periodo.strftime("%Y-%m"),
        "fecha_liquidacion": salary.fecha_liquidacion,
        "fecha_pago_prevista": salary.fecha_pago_prevista,

        "importe_recibo": str(salary.importe_recibo),

        "descuentos_total": str(salary.descuentos_total),
        "adicionales_total": str(salary.adicionales_total),

        "transferencia_real": str(salary.transferencia_real),

        "ajuste_efectivo": str(salary.ajuste_efectivo),

        "efectivo": str(salary.efectivo),

        "sueldo_total": str(salary.sueldo_total),

        "estado": salary.estado,
        "moneda": salary.moneda,

        "recibo_entregado": salary.recibo_entregado,
        "fecha_entrega_recibo": salary.fecha_entrega_recibo,
        "recibo_firmado": salary.recibo_firmado,
        "transferencia_realizada": salary.transferencia_realizada,
        "efectivo_entregado": salary.efectivo_entregado,

        "observaciones": salary.observaciones,
        "anulado": salary.anulado,

        "created_at": salary.created_at,
        "updated_at": salary.updated_at
    }

    if detail:
        data["discounts"] = [
            discount_to_dict(discount)
            for discount in salary.discounts.all()
        ]
        data["additionals"] = [
            additional_to_dict(additional)
            for additional in salary.additionals.all()
        ]

    return data


def parse_period(value):
    if not value:
        today = date.today()
        return date(today.year, today.month, 1)

    try:
        if len(value) == 7:
            parsed = datetime.strptime(value, "%Y-%m").date()
        else:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()

        return date(parsed.year, parsed.month, 1)

    except ValueError:
        raise ValueError("El período debe tener formato YYYY-MM.")


def parse_decimal(value, field, default=Decimal("0.00")):
    if value in (None, ""):
        return default

    try:
        amount = Decimal(str(value))

    except InvalidOperation:
        raise ValueError(f"{field} debe ser un número válido.")

    if amount < 0:
        raise ValueError(f"{field} no puede ser negativo.")

    return amount


def parse_positive_decimal(value, field):
    amount = parse_decimal(value, field)

    if amount <= 0:
        raise ValueError(f"{field} debe ser mayor a cero.")

    return amount


# ====================== SALARIES ======================

class SalaryListCreateAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get(self, request):
        try:
            periodo = parse_period(request.query_params.get("periodo"))

        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        if periodo.month == 12:
            next_period = date(periodo.year + 1, 1, 1)
        else:
            next_period = date(periodo.year, periodo.month + 1, 1)

        employees = Employee.objects.filter(
            models.Q(fecha_baja__isnull=True)
            | models.Q(fecha_baja__gte=next_period)
        ).order_by("apellido", "nombre")

        salaries = Salary.objects.filter(
            periodo=periodo
        ).select_related(
            "employee",
            "employee__group"
        ).prefetch_related(
            "discounts",
            "additionals"
        )

        salaries_by_employee = {
            salary.employee_id: salary
            for salary in salaries
        }

        rows = []

        for employee in employees:
            salary = salaries_by_employee.get(employee.id)

            rows.append({
                "employee": employee_to_dict(employee),
                "salary": salary_to_dict(salary) if salary else None
            })

        return Response({
            "periodo": periodo.strftime("%Y-%m"),
            "count": len(rows),
            "employees": rows
        })

    def post(self, request):
        data = request.data

        employee_id = data.get("employee_id")

        if not employee_id:
            return Response(
                {"detail": "El empleado es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        employee = Employee.objects.filter(id=employee_id).first()

        if not employee:
            return Response(
                {"detail": "Empleado no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            periodo = parse_period(data.get("periodo"))

            importe_recibo = parse_decimal(
                data.get("importe_recibo"),
                "El importe del recibo"
            )

            ajuste_efectivo = parse_decimal(
                data.get("ajuste_efectivo"),
                "El ajuste en efectivo"
            )

        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Salary.objects.filter(employee=employee, periodo=periodo).exists():
            return Response(
                {
                    "detail":
                    "Ya existe una liquidación para este empleado en ese período."
                },
                status=status.HTTP_409_CONFLICT
            )

        try:
            db = get_tenant_db()

            with transaction.atomic(using=db):
                salary = Salary.objects.create(
                    employee=employee,
                    periodo=periodo,
                    fecha_pago_prevista=data.get("fecha_pago_prevista") or None,
                    importe_recibo=importe_recibo,
                    ajuste_efectivo=ajuste_efectivo,
                    moneda=str(data.get("moneda", "ARS")).upper(),
                    recibo_entregado=bool(data.get("recibo_entregado", False)),
                    fecha_entrega_recibo=data.get("fecha_entrega_recibo") or None,
                    recibo_firmado=bool(data.get("recibo_firmado", False)),
                    transferencia_realizada=bool(
                        data.get("transferencia_realizada", False)
                    ),
                    efectivo_entregado=bool(
                        data.get("efectivo_entregado", False)
                    ),
                    observaciones=str(data.get("observaciones", "")).strip()
                )

        except (IntegrityError, ValueError):
            pp.pprint(traceback.format_exc())

            return Response(
                {"detail": "No se pudo crear la liquidación."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            salary_to_dict(salary, detail=True),
            status=status.HTTP_201_CREATED
        )


# ====================== SALARY DETAIL ======================

class SalaryDetailAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get_salary(self, salary_id):
        return Salary.objects.filter(
            id=salary_id
        ).select_related(
            "employee",
            "employee__group"
        ).prefetch_related(
            "discounts",
            "additionals"
        ).first()

    def get(self, request, salary_id):
        salary = self.get_salary(salary_id)

        if not salary:
            return Response(
                {"detail": "Liquidación no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(salary_to_dict(salary, detail=True))

    def patch(self, request, salary_id):
        salary = self.get_salary(salary_id)

        if not salary:
            return Response(
                {"detail": "Liquidación no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data

        try:
            if "periodo" in data:
                periodo = parse_period(data["periodo"])

                exists = Salary.objects.filter(
                    employee=salary.employee,
                    periodo=periodo
                ).exclude(id=salary.id).exists()

                if exists:
                    return Response(
                        {"detail": "Ya existe una liquidación para ese período."},
                        status=status.HTTP_409_CONFLICT
                    )

                salary.periodo = periodo

            if "importe_recibo" in data:
                importe_recibo = parse_decimal(
                    data["importe_recibo"],
                    "El importe del recibo"
                )

                if salary.descuentos_total > importe_recibo:
                    return Response(
                        {
                            "detail":
                            "El recibo no puede ser menor al total de descuentos."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                salary.importe_recibo = importe_recibo

            if "ajuste_efectivo" in data:
                salary.ajuste_efectivo = parse_decimal(
                    data["ajuste_efectivo"],
                    "El ajuste en efectivo"
                )

            if "fecha_pago_prevista" in data:
                salary.fecha_pago_prevista = data["fecha_pago_prevista"] or None

            if "moneda" in data:
                salary.moneda = str(data["moneda"]).upper()

            if "recibo_entregado" in data:
                salary.recibo_entregado = bool(data["recibo_entregado"])

            if "fecha_entrega_recibo" in data:
                salary.fecha_entrega_recibo = data["fecha_entrega_recibo"] or None

            if "recibo_firmado" in data:
                salary.recibo_firmado = bool(data["recibo_firmado"])

            if "transferencia_realizada" in data:
                salary.transferencia_realizada = bool(
                    data["transferencia_realizada"]
                )

            if "efectivo_entregado" in data:
                salary.efectivo_entregado = bool(data["efectivo_entregado"])

            if "observaciones" in data:
                salary.observaciones = str(data["observaciones"]).strip()

            if "anulado" in data:
                salary.anulado = bool(data["anulado"])

            db = get_tenant_db()

            with transaction.atomic(using=db):
                salary.save()

        except (IntegrityError, ValueError) as e:
            pp.pprint(traceback.format_exc())

            return Response(
                {"detail": str(e) or "No se pudo actualizar la liquidación."},
                status=status.HTTP_400_BAD_REQUEST
            )

        salary = self.get_salary(salary.id)

        return Response(salary_to_dict(salary, detail=True))

    def delete(self, request, salary_id):
        salary = self.get_salary(salary_id)

        if not salary:
            return Response(
                {"detail": "Liquidación no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        db = get_tenant_db()

        with transaction.atomic(using=db):
            salary.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# ====================== EMPLOYEE SALARY ======================

class EmployeeSalaryAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get(self, request, employee_id):
        employee = Employee.objects.filter(id=employee_id).first()

        if not employee:
            return Response(
                {"detail": "Empleado no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            periodo = parse_period(request.query_params.get("periodo"))

        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        salary = Salary.objects.filter(
            employee=employee,
            periodo=periodo
        ).prefetch_related(
            "discounts",
            "additionals"
        ).first()

        return Response({
            "employee": employee_to_dict(employee),
            "periodo": periodo.strftime("%Y-%m"),
            "salary": salary_to_dict(salary, detail=True) if salary else None
        })


# ====================== DISCOUNTS ======================

class SalaryDiscountListCreateAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get_salary(self, salary_id):
        return Salary.objects.filter(id=salary_id).prefetch_related(
            "discounts"
        ).first()

    def get(self, request, salary_id):
        salary = self.get_salary(salary_id)

        if not salary:
            return Response(
                {"detail": "Liquidación no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "count": salary.discounts.count(),
            "discounts": [
                discount_to_dict(discount)
                for discount in salary.discounts.all()
            ]
        })

    def post(self, request, salary_id):
        salary = self.get_salary(salary_id)

        if not salary:
            return Response(
                {"detail": "Liquidación no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data

        descripcion = str(data.get("descripcion", "")).strip()

        if not descripcion:
            return Response(
                {"detail": "La descripción es obligatoria."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            importe = parse_positive_decimal(
                data.get("importe"),
                "El importe"
            )

        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        if salary.descuentos_total + importe > salary.importe_recibo:
            return Response(
                {
                    "detail":
                    "Los descuentos no pueden superar el importe del recibo."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            discount = SalaryDiscount.objects.create(
                salary=salary,
                descripcion=descripcion,
                importe=importe
            )

        except IntegrityError:
            pp.pprint(traceback.format_exc())

            return Response(
                {"detail": "No se pudo crear el descuento."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            discount_to_dict(discount),
            status=status.HTTP_201_CREATED
        )


class SalaryDiscountDetailAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get_discount(self, salary_id, discount_id):
        return SalaryDiscount.objects.filter(
            id=discount_id,
            salary_id=salary_id
        ).select_related(
            "salary"
        ).first()

    def patch(self, request, salary_id, discount_id):
        discount = self.get_discount(salary_id, discount_id)

        if not discount:
            return Response(
                {"detail": "Descuento no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data

        if "descripcion" in data:
            descripcion = str(data["descripcion"]).strip()

            if not descripcion:
                return Response(
                    {"detail": "La descripción no puede estar vacía."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            discount.descripcion = descripcion

        if "importe" in data:
            try:
                importe = parse_positive_decimal(
                    data["importe"],
                    "El importe"
                )

            except ValueError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            otros_descuentos = discount.salary.descuentos_total - discount.importe

            if otros_descuentos + importe > discount.salary.importe_recibo:
                return Response(
                    {
                        "detail":
                        "Los descuentos no pueden superar el importe del recibo."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            discount.importe = importe

        discount.save()

        return Response(discount_to_dict(discount))

    def delete(self, request, salary_id, discount_id):
        discount = self.get_discount(salary_id, discount_id)

        if not discount:
            return Response(
                {"detail": "Descuento no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        discount.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# ====================== ADDITIONALS ======================

class SalaryAdditionalListCreateAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get_salary(self, salary_id):
        return Salary.objects.filter(id=salary_id).prefetch_related(
            "additionals"
        ).first()

    def get(self, request, salary_id):
        salary = self.get_salary(salary_id)

        if not salary:
            return Response(
                {"detail": "Liquidación no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "count": salary.additionals.count(),
            "additionals": [
                additional_to_dict(additional)
                for additional in salary.additionals.all()
            ]
        })

    def post(self, request, salary_id):
        salary = self.get_salary(salary_id)

        if not salary:
            return Response(
                {"detail": "Liquidación no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        descripcion = str(request.data.get("descripcion", "")).strip()

        if not descripcion:
            return Response(
                {"detail": "La descripción es obligatoria."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            importe = parse_positive_decimal(
                request.data.get("importe"),
                "El importe"
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            additional = SalaryAdditional.objects.create(
                salary=salary,
                descripcion=descripcion,
                importe=importe
            )
        except IntegrityError:
            pp.pprint(traceback.format_exc())
            return Response(
                {"detail": "No se pudo crear el adicional."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            additional_to_dict(additional),
            status=status.HTTP_201_CREATED
        )


class SalaryAdditionalDetailAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get_additional(self, salary_id, additional_id):
        return SalaryAdditional.objects.filter(
            id=additional_id,
            salary_id=salary_id
        ).first()

    def patch(self, request, salary_id, additional_id):
        additional = self.get_additional(salary_id, additional_id)

        if not additional:
            return Response(
                {"detail": "Adicional no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        if "descripcion" in request.data:
            descripcion = str(request.data["descripcion"]).strip()

            if not descripcion:
                return Response(
                    {"detail": "La descripción no puede estar vacía."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            additional.descripcion = descripcion

        if "importe" in request.data:
            try:
                additional.importe = parse_positive_decimal(
                    request.data["importe"],
                    "El importe"
                )
            except ValueError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        additional.save()
        return Response(additional_to_dict(additional))

    def delete(self, request, salary_id, additional_id):
        additional = self.get_additional(salary_id, additional_id)

        if not additional:
            return Response(
                {"detail": "Adicional no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        additional.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
