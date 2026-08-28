from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from Employees.models import Employee


class Loan(models.Model):
    class PersonType(models.TextChoices):
        EMPLOYEE = "EMPLEADO", "Empleado"
        EXTERNAL = "EXTERNO", "Persona externa"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVO", "Activo"
        PAID = "PAGADO", "Pagado"
        CANCELLED = "ANULADO", "Anulado"

    class DeliveryMethod(models.TextChoices):
        TRANSFER = "TRANSFERENCIA", "Transferencia"
        CASH = "EFECTIVO", "Efectivo"
        OTHER = "OTRO", "Otro"

    person_type = models.CharField(max_length=10, choices=PersonType.choices)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="loans",
        null=True,
        blank=True,
    )
    external_name = models.CharField(max_length=200, blank=True)
    external_document = models.CharField(max_length=50, blank=True)
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    delivery_date = models.DateField()
    first_installment_period = models.DateField()
    installment_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    delivery_method = models.CharField(
        max_length=20,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.TRANSFER,
    )
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Loans"
        ordering = ["-delivery_date", "-id"]

    @property
    def person_name(self):
        if self.employee_id:
            return f"{self.employee.apellido}, {self.employee.nombre}"
        return self.external_name

    @property
    def paid_amount(self):
        return self.installments.aggregate(total=models.Sum("paid_amount"))["total"] or Decimal("0")

    @property
    def balance(self):
        return max(self.total_amount - self.paid_amount, Decimal("0"))

    def refresh_status(self):
        if self.status == self.Status.CANCELLED:
            return
        new_status = self.Status.PAID if self.balance <= 0 else self.Status.ACTIVE
        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])


class LoanInstallment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDIENTE", "Pendiente"
        PARTIAL = "PARCIAL", "Pagada parcialmente"
        PAID = "PAGADA", "Pagada"
        SKIPPED = "OMITIDA", "Omitida"

    class PaymentMethod(models.TextChoices):
        SALARY = "DESCUENTO_SUELDO", "Descuento de sueldo"
        TRANSFER = "TRANSFERENCIA", "Transferencia"
        CASH = "EFECTIVO", "Efectivo"
        OTHER = "OTRO", "Otro"

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="installments")
    number = models.PositiveIntegerField()
    period = models.DateField()
    expected_amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "LoanInstallments"
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["loan", "number"], name="unique_loan_installment_number")]

