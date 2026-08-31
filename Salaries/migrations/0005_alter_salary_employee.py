from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("Employees", "0004_employee_fecha_baja"),
        ("Salaries", "0004_salary_payment_indicators"),
    ]

    operations = [
        migrations.AlterField(
            model_name="salary",
            name="employee",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="salaries",
                to="Employees.employee",
            ),
        ),
    ]
