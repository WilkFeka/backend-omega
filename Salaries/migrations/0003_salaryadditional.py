from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("Salaries", "0002_remove_salarypayment_salary_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalaryAdditional",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("descripcion", models.CharField(max_length=255)),
                ("importe", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("salary", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="additionals", to="Salaries.salary")),
            ],
            options={
                "db_table": "SalaryAdditionals",
                "ordering": ["id"],
            },
        ),
    ]
