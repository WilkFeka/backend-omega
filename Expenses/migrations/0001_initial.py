import decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.DateField()),
                ("category", models.CharField(choices=[("IMPUESTOS", "Impuestos"), ("SERVICIOS", "Servicios"), ("VARIOS", "Varios")], max_length=12)),
                ("description", models.CharField(max_length=160)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])),
                ("observation", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "Expenses", "ordering": ["category", "description", "id"]},
        ),
        migrations.AddIndex(model_name="expense", index=models.Index(fields=["period", "category"], name="expense_period_category_idx")),
    ]
