from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Employees", "0002_alter_employee_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="gremio",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
