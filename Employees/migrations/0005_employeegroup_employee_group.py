from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("Employees", "0004_employee_fecha_baja"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100, unique=True)),
            ],
            options={
                "db_table": "EmployeeGroups",
                "ordering": ["nombre"],
            },
        ),
        migrations.AddField(
            model_name="employee",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="employees",
                to="Employees.employeegroup",
            ),
        ),
    ]
