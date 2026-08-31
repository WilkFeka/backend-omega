from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Salaries", "0003_salaryadditional"),
    ]

    operations = [
        migrations.AddField(
            model_name="salary",
            name="transferencia_realizada",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="salary",
            name="efectivo_entregado",
            field=models.BooleanField(default=False),
        ),
    ]
