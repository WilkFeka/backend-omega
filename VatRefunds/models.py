from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class VatBeneficiary(models.Model):
    class DeliveryMethod(models.TextChoices):
        CASH = "EFECTIVO", "Efectivo"
        TRANSFER = "TRANSFERENCIA", "Transferencia"

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    delivery_method = models.CharField(max_length=20, choices=DeliveryMethod.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "VatBeneficiaries"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"


class VatRefundDetail(models.Model):
    beneficiary = models.ForeignKey(
        VatBeneficiary,
        on_delete=models.CASCADE,
        related_name="details",
    )
    period = models.DateField()
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    observation = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "VatRefundDetails"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["beneficiary", "period"], name="vat_beneficiary_period_idx")]
