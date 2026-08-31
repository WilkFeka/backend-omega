from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("Expenses", "0002_expense_copied_from_alter_amount")]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="payment_method",
            field=models.CharField(choices=[("TRANSFERENCIA", "Transferencia"), ("EFECTIVO", "Efectivo")], default="TRANSFERENCIA", max_length=16),
        ),
        migrations.AddField(model_name="expense", name="is_paid", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="expense", name="paid_at", field=models.DateField(blank=True, null=True)),
        migrations.CreateModel(
            name="ExpenseAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="expenses/receipts/%Y/%m/")),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size", models.PositiveBigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expense", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="Expenses.expense")),
            ],
            options={"db_table": "ExpenseAttachments", "ordering": ["-created_at", "-id"]},
        ),
    ]
