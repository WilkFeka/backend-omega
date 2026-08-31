from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Expense(models.Model):
    class Category(models.TextChoices):
        TAXES = "IMPUESTOS", "Impuestos"
        SERVICES = "SERVICIOS", "Servicios"
        MISC = "VARIOS", "Varios"

    class PaymentMethod(models.TextChoices):
        TRANSFER = "TRANSFERENCIA", "Transferencia"
        CASH = "EFECTIVO", "Efectivo"

    period = models.DateField()
    category = models.CharField(max_length=12, choices=Category.choices)
    description = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0.01"))])
    copied_from = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="copies")
    observation = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=16, choices=PaymentMethod.choices, default=PaymentMethod.TRANSFER)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Expenses"
        ordering = ["category", "description", "id"]
        indexes = [models.Index(fields=["period", "category"], name="expense_period_category_idx")]


class ExpenseAttachment(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="expenses/receipts/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ExpenseAttachments"
        ordering = ["-created_at", "-id"]
