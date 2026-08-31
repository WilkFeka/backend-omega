from datetime import date
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from Users.permissions import IsTenantAdmin

from .models import VatBeneficiary, VatRefundDetail


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


def beneficiary_to_dict(item, period=None):
    data = {"id": item.id, "nombre": item.nombre, "apellido": item.apellido, "delivery_method": item.delivery_method}
    if period:
        summary = item.details.filter(period=period).aggregate(total=Sum("amount"), count=Count("id"))
        data.update({"period": period, "total": summary["total"] or Decimal("0"), "detail_count": summary["count"]})
    return data


def detail_to_dict(item):
    return {
        "id": item.id,
        "beneficiary_id": item.beneficiary_id,
        "period": item.period,
        "amount": item.amount,
        "observation": item.observation,
    }


class VatBeneficiaryListCreateAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get(self, request):
        period = parse_period(request.query_params.get("periodo"))
        if not period:
            return Response({"detail": "Período inválido."}, status=400)
        beneficiaries = VatBeneficiary.objects.all()
        rows = [beneficiary_to_dict(item, period) for item in beneficiaries]
        cash_total = sum((row["total"] for row in rows if row["delivery_method"] == VatBeneficiary.DeliveryMethod.CASH), Decimal("0"))
        transfer_total = sum((row["total"] for row in rows if row["delivery_method"] == VatBeneficiary.DeliveryMethod.TRANSFER), Decimal("0"))
        return Response({
            "count": len(rows),
            "period": period,
            "total": sum((row["total"] for row in rows), Decimal("0")),
            "cash_total": cash_total,
            "transfer_total": transfer_total,
            "beneficiaries_with_details": sum(1 for row in rows if row["detail_count"]),
            "beneficiaries": rows,
        })

    def post(self, request):
        nombre = str(request.data.get("nombre") or "").strip()
        apellido = str(request.data.get("apellido") or "").strip()
        delivery_method = request.data.get("delivery_method")
        errors = {}
        if not nombre:
            errors["nombre"] = "El nombre es obligatorio."
        if not apellido:
            errors["apellido"] = "El apellido es obligatorio."
        if delivery_method not in VatBeneficiary.DeliveryMethod.values:
            errors["delivery_method"] = "Seleccioná un medio de entrega válido."
        if errors:
            return Response({"detail": "Revisá los datos ingresados.", "errors": errors}, status=400)
        item = VatBeneficiary.objects.create(nombre=nombre, apellido=apellido, delivery_method=delivery_method)
        return Response(beneficiary_to_dict(item), status=status.HTTP_201_CREATED)


class VatBeneficiaryDetailAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get_item(self, beneficiary_id):
        return VatBeneficiary.objects.filter(id=beneficiary_id).first()

    def get(self, request, beneficiary_id):
        item = self.get_item(beneficiary_id)
        return Response(beneficiary_to_dict(item)) if item else Response({"detail": "Beneficiario no encontrado."}, status=404)

    def patch(self, request, beneficiary_id):
        item = self.get_item(beneficiary_id)
        if not item:
            return Response({"detail": "Beneficiario no encontrado."}, status=404)
        nombre = str(request.data.get("nombre", item.nombre)).strip()
        apellido = str(request.data.get("apellido", item.apellido)).strip()
        delivery_method = request.data.get("delivery_method", item.delivery_method)
        if not nombre or not apellido:
            return Response({"detail": "El nombre y el apellido son obligatorios."}, status=400)
        if delivery_method not in VatBeneficiary.DeliveryMethod.values:
            return Response({"detail": "Seleccioná un medio de entrega válido."}, status=400)
        item.nombre = nombre
        item.apellido = apellido
        item.delivery_method = delivery_method
        item.save(update_fields=["nombre", "apellido", "delivery_method", "updated_at"])
        return Response(beneficiary_to_dict(item))

    def delete(self, request, beneficiary_id):
        item = self.get_item(beneficiary_id)
        if not item:
            return Response({"detail": "Beneficiario no encontrado."}, status=404)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VatRefundDetailListCreateAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get_beneficiary(self, beneficiary_id):
        return VatBeneficiary.objects.filter(id=beneficiary_id).first()

    def get(self, request, beneficiary_id):
        beneficiary = self.get_beneficiary(beneficiary_id)
        if not beneficiary:
            return Response({"detail": "Beneficiario no encontrado."}, status=404)
        period = parse_period(request.query_params.get("periodo"))
        if not period:
            return Response({"detail": "Período inválido."}, status=400)
        items = beneficiary.details.filter(period=period)
        return Response({
            "beneficiary": beneficiary_to_dict(beneficiary),
            "period": period,
            "total": items.aggregate(value=Sum("amount"))["value"] or Decimal("0"),
            "count": items.count(),
            "details": [detail_to_dict(item) for item in items],
        })

    def post(self, request, beneficiary_id):
        beneficiary = self.get_beneficiary(beneficiary_id)
        if not beneficiary:
            return Response({"detail": "Beneficiario no encontrado."}, status=404)
        period = parse_period(request.data.get("period"))
        amount = parse_amount(request.data.get("amount"))
        errors = {}
        if not period:
            errors["period"] = "Período inválido."
        if amount is None:
            errors["amount"] = "Ingresá un importe mayor a cero."
        if errors:
            return Response({"detail": "Revisá los datos ingresados.", "errors": errors}, status=400)
        item = VatRefundDetail.objects.create(
            beneficiary=beneficiary,
            period=period,
            amount=amount,
            observation=str(request.data.get("observation") or "").strip(),
        )
        return Response(detail_to_dict(item), status=status.HTTP_201_CREATED)


class VatRefundDetailAPIView(APIView):
    permission_classes = [IsTenantAdmin]

    def get_item(self, beneficiary_id, detail_id):
        return VatRefundDetail.objects.filter(id=detail_id, beneficiary_id=beneficiary_id).first()

    def patch(self, request, beneficiary_id, detail_id):
        item = self.get_item(beneficiary_id, detail_id)
        if not item:
            return Response({"detail": "Detalle no encontrado."}, status=404)
        period = parse_period(request.data.get("period", item.period))
        amount = parse_amount(request.data.get("amount", item.amount))
        if not period or amount is None:
            return Response({"detail": "Revisá el período y el importe."}, status=400)
        item.period = period
        item.amount = amount
        item.observation = str(request.data.get("observation", item.observation) or "").strip()
        item.save(update_fields=["period", "amount", "observation", "updated_at"])
        return Response(detail_to_dict(item))

    def delete(self, request, beneficiary_id, detail_id):
        item = self.get_item(beneficiary_id, detail_id)
        if not item:
            return Response({"detail": "Detalle no encontrado."}, status=404)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
