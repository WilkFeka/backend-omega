from django.db import models


class Employee(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    direccion = models.CharField(max_length=255, null=True, blank=True)
    matricula = models.CharField(max_length=100, null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)

    fecha_nacimiento = models.DateField()
    fecha_ingreso = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "Employees"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"