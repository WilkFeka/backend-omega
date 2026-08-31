import decimal
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("Expenses", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="expense",
            name="amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))]),
        ),
        migrations.AddField(
            model_name="expense",
            name="copied_from",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="copies", to="Expenses.expense"),
        ),
    ]
