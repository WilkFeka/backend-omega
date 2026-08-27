from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Employees", "0003_employee_gremio"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="fecha_baja",
            field=models.DateField(blank=True, null=True),
        ),
    ]
