import decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="VatBeneficiary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100)),
                ("apellido", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "VatBeneficiaries", "ordering": ["apellido", "nombre"]},
        ),
        migrations.CreateModel(
            name="VatRefundDetail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])),
                ("observation", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("beneficiary", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="details", to="VatRefunds.vatbeneficiary")),
            ],
            options={"db_table": "VatRefundDetails", "ordering": ["created_at", "id"]},
        ),
        migrations.AddIndex(
            model_name="vatrefunddetail",
            index=models.Index(fields=["beneficiary", "period"], name="vat_beneficiary_period_idx"),
        ),
    ]
