from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Expense(models.Model):
    class Category(models.TextChoices):
        TAXES = "IMPUESTOS", "Impuestos"
        SERVICES = "SERVICIOS", "Servicios"
        MISC = "VARIOS", "Varios"

    period = models.DateField()
    category = models.CharField(max_length=12, choices=Category.choices)
    description = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0.01"))])
    copied_from = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="copies")
    observation = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Expenses"
        ordering = ["category", "description", "id"]
        indexes = [models.Index(fields=["period", "category"], name="expense_period_category_idx")]
