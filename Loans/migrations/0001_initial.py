import decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("Employees", "0006_employeeposition_employee_position")]

    operations = [
        migrations.CreateModel(
            name="Loan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("person_type", models.CharField(choices=[("EMPLEADO", "Empleado"), ("EXTERNO", "Persona externa")], max_length=10)),
                ("external_name", models.CharField(blank=True, max_length=200)),
                ("external_document", models.CharField(blank=True, max_length=50)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])),
                ("delivery_date", models.DateField()),
                ("first_installment_period", models.DateField()),
                ("installment_count", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("delivery_method", models.CharField(choices=[("TRANSFERENCIA", "Transferencia"), ("EFECTIVO", "Efectivo"), ("OTRO", "Otro")], default="TRANSFERENCIA", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("ACTIVO", "Activo"), ("PAGADO", "Pagado"), ("ANULADO", "Anulado")], default="ACTIVO", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="loans", to="Employees.employee")),
            ],
            options={"db_table": "Loans", "ordering": ["-delivery_date", "-id"]},
        ),
        migrations.CreateModel(
            name="LoanInstallment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveIntegerField()),
                ("period", models.DateField()),
                ("expected_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("paid_amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("status", models.CharField(choices=[("PENDIENTE", "Pendiente"), ("PARCIAL", "Pagada parcialmente"), ("PAGADA", "Pagada"), ("OMITIDA", "Omitida")], default="PENDIENTE", max_length=12)),
                ("payment_date", models.DateField(blank=True, null=True)),
                ("payment_method", models.CharField(blank=True, choices=[("DESCUENTO_SUELDO", "Descuento de sueldo"), ("TRANSFERENCIA", "Transferencia"), ("EFECTIVO", "Efectivo"), ("OTRO", "Otro")], max_length=20)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("loan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="installments", to="Loans.loan")),
            ],
            options={"db_table": "LoanInstallments", "ordering": ["number"]},
        ),
        migrations.AddConstraint(model_name="loaninstallment", constraint=models.UniqueConstraint(fields=("loan", "number"), name="unique_loan_installment_number")),
    ]
