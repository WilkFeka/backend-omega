from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("VatRefunds", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="vatbeneficiary",
            name="delivery_method",
            field=models.CharField(
                choices=[("EFECTIVO", "Efectivo"), ("TRANSFERENCIA", "Transferencia")],
                default="TRANSFERENCIA",
                max_length=20,
            ),
            preserve_default=False,
        ),
    ]
