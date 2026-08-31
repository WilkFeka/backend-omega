from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from Employees.models import Employee


class Salary(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="salaries"
    )

    periodo = models.DateField()

    fecha_liquidacion = models.DateField(auto_now_add=True)
    fecha_pago_prevista = models.DateField(null=True, blank=True)

    importe_recibo = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    ajuste_efectivo = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    moneda = models.CharField(max_length=3, default="ARS")

    recibo_entregado = models.BooleanField(default=False)
    fecha_entrega_recibo = models.DateField(null=True, blank=True)
    recibo_firmado = models.BooleanField(default=False)

    transferencia_realizada = models.BooleanField(default=False)
    efectivo_entregado = models.BooleanField(default=False)

    observaciones = models.TextField(blank=True)

    anulado = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Salaries"
        ordering = ["-periodo", "employee__apellido", "employee__nombre"]

        constraints = [
            models.UniqueConstraint(
                fields=["employee", "periodo"],
                name="unique_employee_salary_period"
            )
        ]

    def __str__(self):
        return f"{self.employee} - {self.periodo:%m/%Y}"

    @property
    def descuentos_total(self):
        return sum(
            (discount.importe for discount in self.discounts.all()),
            Decimal("0.00")
        )

    @property
    def adicionales_total(self):
        return sum(
            (additional.importe for additional in self.additionals.all()),
            Decimal("0.00")
        )

    @property
    def transferencia_real(self):
        return self.importe_recibo - self.descuentos_total

    @property
    def efectivo(self):
        return self.ajuste_efectivo

    @property
    def sueldo_total(self):
        return (
            self.transferencia_real
            + self.ajuste_efectivo
            + self.adicionales_total
        )

    @property
    def estado(self):
        if self.anulado:
            return "ANULADO"

        return "LIQUIDADO"


class SalaryDiscount(models.Model):

    salary = models.ForeignKey(
        Salary,
        on_delete=models.CASCADE,
        related_name="discounts"
    )

    descripcion = models.CharField(max_length=255)

    importe = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "SalaryDiscounts"
        ordering = ["id"]

    def __str__(self):
        return f"{self.salary} - {self.descripcion}"


class SalaryAdditional(models.Model):

    salary = models.ForeignKey(
        Salary,
        on_delete=models.CASCADE,
        related_name="additionals"
    )

    descripcion = models.CharField(max_length=255)

    importe = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "SalaryAdditionals"
        ordering = ["id"]

    def __str__(self):
        return f"{self.salary} - {self.descripcion}"
