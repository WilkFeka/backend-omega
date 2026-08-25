import traceback
import pprint as pp

from django.db import IntegrityError, transaction

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Employee
from Users.permissions import IsTenantAdmin


def employee_to_dict(employee):
    return {
        "id": employee.id,
        "nombre": employee.nombre,
        "apellido": employee.apellido,
        "direccion": employee.direccion,
        "matricula": employee.matricula,
        "telefono": employee.telefono,
        "fecha_nacimiento": employee.fecha_nacimiento,
        "fecha_ingreso": employee.fecha_ingreso
    }


# ====================== EMPLOYEES ======================
# GET  /api/employees/
# POST /api/employees/

class EmployeeListCreateAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    # Lista
    def get(self, request):
        employees = Employee.objects.all().order_by("apellido", "nombre")

        data = [employee_to_dict(employee) for employee in employees]

        return Response({
            "count": len(data),
            "employees": data
        })

    # Crear
    def post(self, request):
        data = request.data

        nombre = str(data.get("nombre", "")).strip()
        apellido = str(data.get("apellido", "")).strip()

        direccion = data.get("direccion")
        matricula = data.get("matricula")
        telefono = data.get("telefono")

        fecha_nacimiento = data.get("fecha_nacimiento")
        fecha_ingreso = data.get("fecha_ingreso")

        errors = {}

        if not nombre:
            errors["nombre"] = "El nombre es obligatorio."

        if not apellido:
            errors["apellido"] = "El apellido es obligatorio."

        if not fecha_nacimiento:
            errors["fecha_nacimiento"] = "La fecha de nacimiento es obligatoria."

        if errors:
            return Response(
                {
                    "detail": "Datos inválidos",
                    "errors": errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                employee = Employee.objects.create(
                    nombre=nombre,
                    apellido=apellido,
                    direccion=direccion or None,
                    matricula=matricula or None,
                    telefono=telefono or None,
                    fecha_nacimiento=fecha_nacimiento,
                    fecha_ingreso=fecha_ingreso or None
                )

        except (IntegrityError, ValueError):
            pp.pprint(traceback.format_exc())

            return Response(
                {"detail": "No se pudo crear el empleado."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            employee_to_dict(employee),
            status=status.HTTP_201_CREATED
        )


# ====================== EMPLOYEE DETAIL ======================
# GET    /api/employees/<id>/
# PATCH  /api/employees/<id>/
# DELETE /api/employees/<id>/

class EmployeeDetailAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get_employee(self, employee_id):
        return Employee.objects.filter(id=employee_id).first()

    # Detalle
    def get(self, request, employee_id):
        employee = self.get_employee(employee_id)

        if not employee:
            return Response(
                {"detail": "Empleado no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(employee_to_dict(employee))

    # Modificar
    def patch(self, request, employee_id):
        employee = self.get_employee(employee_id)

        if not employee:
            return Response(
                {"detail": "Empleado no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data

        if "nombre" in data:
            nombre = str(data["nombre"]).strip()

            if not nombre:
                return Response(
                    {"detail": "El nombre no puede estar vacío."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            employee.nombre = nombre

        if "apellido" in data:
            apellido = str(data["apellido"]).strip()

            if not apellido:
                return Response(
                    {"detail": "El apellido no puede estar vacío."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            employee.apellido = apellido

        if "direccion" in data:
            employee.direccion = data["direccion"] or None

        if "matricula" in data:
            employee.matricula = data["matricula"] or None

        if "telefono" in data:
            employee.telefono = data["telefono"] or None

        if "fecha_nacimiento" in data:
            if not data["fecha_nacimiento"]:
                return Response(
                    {"detail": "La fecha de nacimiento no puede estar vacía."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            employee.fecha_nacimiento = data["fecha_nacimiento"]

        if "fecha_ingreso" in data:
            employee.fecha_ingreso = data["fecha_ingreso"] or None

        try:
            employee.save()

        except (IntegrityError, ValueError):
            pp.pprint(traceback.format_exc())

            return Response(
                {"detail": "No se pudo actualizar el empleado."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(employee_to_dict(employee))

    # Eliminar
    def delete(self, request, employee_id):
        employee = self.get_employee(employee_id)

        if not employee:
            return Response(
                {"detail": "Empleado no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        employee.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)