import traceback
import pprint as pp

from django.db import IntegrityError, transaction

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Employee, EmployeeGroup
from Users.permissions import IsTenantAdmin


def employee_to_dict(employee):
    return {
        "id": employee.id,
        "nombre": employee.nombre,
        "apellido": employee.apellido,
        "direccion": employee.direccion,
        "matricula": employee.matricula,
        "gremio": employee.gremio,
        "telefono": employee.telefono,
        "fecha_nacimiento": employee.fecha_nacimiento,
        "fecha_ingreso": employee.fecha_ingreso,
        "fecha_baja": employee.fecha_baja,
        "group": (
            {"id": employee.group_id, "nombre": employee.group.nombre}
            if employee.group_id else None
        )
    }


# ====================== EMPLOYEES ======================
# GET  /api/employees/
# POST /api/employees/

class EmployeeListCreateAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    # Lista
    def get(self, request):
        employees = Employee.objects.select_related("group").all().order_by(
            "apellido", "nombre"
        )

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
        gremio = data.get("gremio")
        telefono = data.get("telefono")

        fecha_nacimiento = data.get("fecha_nacimiento")
        fecha_ingreso = data.get("fecha_ingreso")
        group_id = data.get("group_id")

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

        group = None

        if group_id:
            group = EmployeeGroup.objects.filter(id=group_id).first()

            if not group:
                return Response(
                    {"detail": "Grupo no encontrado."},
                    status=status.HTTP_404_NOT_FOUND
                )

        try:
            with transaction.atomic():
                employee = Employee.objects.create(
                    nombre=nombre,
                    apellido=apellido,
                    direccion=direccion or None,
                    matricula=matricula or None,
                    gremio=gremio or None,
                    telefono=telefono or None,
                    fecha_nacimiento=fecha_nacimiento,
                    fecha_ingreso=fecha_ingreso or None,
                    group=group
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

        if "gremio" in data:
            employee.gremio = data["gremio"] or None

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

        if "fecha_baja" in data:
            employee.fecha_baja = data["fecha_baja"] or None

        if "group_id" in data:
            group_id = data["group_id"]

            if group_id:
                group = EmployeeGroup.objects.filter(id=group_id).first()

                if not group:
                    return Response(
                        {"detail": "Grupo no encontrado."},
                        status=status.HTTP_404_NOT_FOUND
                    )

                employee.group = group
            else:
                employee.group = None

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


# ====================== EMPLOYEE GROUPS ======================

def group_to_dict(group):
    return {
        "id": group.id,
        "nombre": group.nombre,
        "employee_count": group.employees.count()
    }


class EmployeeGroupListCreateAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get(self, request):
        groups = EmployeeGroup.objects.all().order_by("nombre")
        data = [group_to_dict(group) for group in groups]
        return Response({"count": len(data), "groups": data})

    def post(self, request):
        nombre = str(request.data.get("nombre", "")).strip()

        if not nombre:
            return Response(
                {"detail": "El nombre del grupo es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if EmployeeGroup.objects.filter(nombre__iexact=nombre).exists():
            return Response(
                {"detail": "Ya existe un grupo con ese nombre."},
                status=status.HTTP_409_CONFLICT
            )

        group = EmployeeGroup.objects.create(nombre=nombre)
        return Response(group_to_dict(group), status=status.HTTP_201_CREATED)


class EmployeeGroupDetailAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get_group(self, group_id):
        return EmployeeGroup.objects.filter(id=group_id).first()

    def patch(self, request, group_id):
        group = self.get_group(group_id)

        if not group:
            return Response(
                {"detail": "Grupo no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        nombre = str(request.data.get("nombre", "")).strip()

        if not nombre:
            return Response(
                {"detail": "El nombre del grupo es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if EmployeeGroup.objects.filter(nombre__iexact=nombre).exclude(
            id=group.id
        ).exists():
            return Response(
                {"detail": "Ya existe un grupo con ese nombre."},
                status=status.HTTP_409_CONFLICT
            )

        group.nombre = nombre
        group.save(update_fields=["nombre"])
        return Response(group_to_dict(group))

    def delete(self, request, group_id):
        group = self.get_group(group_id)

        if not group:
            return Response(
                {"detail": "Grupo no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
