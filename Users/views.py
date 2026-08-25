import traceback
import pprint as pp

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from Tenancy.models import TenantMembership
from .permissions import IsTenantAdmin


User = get_user_model()

# ====================== CSRF ======================

@api_view(["GET"])
def csrf(request):
    csrf_token = get_token(request)

    return Response({
        "detail": "CSRF cookie set",
        "csrf_token": csrf_token
    })


# ====================== LOGIN ======================

@api_view(["POST"])
@csrf_protect
def login_view(request):
    try:
        data = request.data

        username = data.get("username")
        password = data.get("password")
        remember_me = data.get("remember_me", False)

        if not username or not password:
            return Response(
                {"detail": "Username y password son obligatorios"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Autenticar
        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response(
                {"detail": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {"detail": "Usuario inactivo"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validar acceso al tenant
        has_access = (
            user.is_superuser
            or TenantMembership.objects.using("default").filter(
                user=user,
                tenant=request.tenant,
                active=True
            ).exists()
        )

        if not has_access:
            return Response(
                {"detail": "No tenés acceso a esta empresa"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Login
        login(request, user)

        request.session["tenant_id"] = request.tenant.id

        if remember_me:
            request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            request.session.set_expiry(0)

        # Django rota el CSRF al hacer login
        csrf_token = get_token(request)

        return Response({
            "id": user.id,
            "username": user.get_username(),
            "email": user.email,
            "csrf_token": csrf_token,
            "tenant": {
                "id": request.tenant.id,
                "name": request.tenant.name,
                "slug": request.tenant.slug
            }
        })

    except Exception:
        pp.pprint(traceback.format_exc())

        return Response(
            {"detail": "Error interno del servidor"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ====================== LOGOUT ======================

@api_view(["POST"])
@csrf_protect
def logout_view(request):
    try:
        logout(request)

        return Response({
            "detail": "Sesión cerrada"
        })

    except Exception:
        pp.pprint(traceback.format_exc())

        return Response(
            {"detail": "Error interno del servidor"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ====================== ME ======================

@api_view(["GET"])
def me(request):
    try:
        if not request.user.is_authenticated:
            return Response(
                {"authenticated": False},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = request.user

        # Validar sesión del tenant actual
        session_tenant_id = request.session.get("tenant_id")

        if session_tenant_id != request.tenant.id:
            logout(request)

            return Response(
                {
                    "authenticated": False,
                    "detail": "La sesión no pertenece a esta empresa"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validar acceso al tenant
        has_access = (
            user.is_superuser
            or TenantMembership.objects.using("default").filter(
                user=user,
                tenant=request.tenant,
                active=True
            ).exists()
        )

        if not has_access:
            logout(request)

            return Response(
                {
                    "authenticated": False,
                    "detail": "No tenés acceso a esta empresa"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            "authenticated": True,
            "user": {
                "id": user.id,
                "username": user.get_username(),
                "email": user.email,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser
            },
            "tenant": {
                "id": request.tenant.id,
                "name": request.tenant.name,
                "slug": request.tenant.slug,
                "config": request.tenant.config
            }
        })

    except Exception:
        pp.pprint(traceback.format_exc())

        return Response(
            {"detail": "Error interno del servidor"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ====================== HELPERS ======================

def membership_to_dict(membership):
    user = membership.user

    return {
        "id": user.id,
        "username": user.get_username(),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "user_active": user.is_active,
        "membership_active": membership.active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser
    }


# ====================== USERS ======================
# GET  /api/users/
# POST /api/users/

class UserListCreateAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    # Lista
    def get(self, request):
        memberships = TenantMembership.objects.using("default").filter(
            tenant=request.tenant
        ).select_related("user").order_by(
            "user__first_name",
            "user__last_name",
            "user__username"
        )

        users = [membership_to_dict(membership) for membership in memberships]

        return Response({
            "tenant": {
                "id": request.tenant.id,
                "name": request.tenant.name,
                "slug": request.tenant.slug
            },
            "count": len(users),
            "users": users
        })

    # Crear
    def post(self, request):
        data = request.data

        username = str(data.get("username", "")).strip()
        email = str(data.get("email", "")).strip()
        password = data.get("password")
        first_name = str(data.get("first_name", "")).strip()
        last_name = str(data.get("last_name", "")).strip()
        is_staff = bool(data.get("is_staff", False))

        errors = {}

        if not username:
            errors["username"] = "El username es obligatorio."

        if not password:
            errors["password"] = "La contraseña es obligatoria."
        elif len(password) < 6:
            errors["password"] = "La contraseña debe tener al menos 6 caracteres."

        if errors:
            return Response(
                {
                    "detail": "Datos inválidos",
                    "errors": errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.using("default").filter(username=username).exists():
            return Response(
                {"detail": "El username ya existe."},
                status=status.HTTP_409_CONFLICT
            )

        try:
            with transaction.atomic(using="default"):
                user = User.objects.db_manager("default").create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=is_staff
                )

                membership = TenantMembership.objects.using("default").create(
                    user=user,
                    tenant=request.tenant,
                    active=True
                )

        except IntegrityError:
            pp.pprint(traceback.format_exc())

            return Response(
                {"detail": "No se pudo crear el usuario."},
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            membership_to_dict(membership),
            status=status.HTTP_201_CREATED
        )


# ====================== USER DETAIL ======================
# GET    /api/users/<id>/
# PATCH  /api/users/<id>/
# DELETE /api/users/<id>/

class UserDetailAPIView(APIView):

    permission_classes = [IsTenantAdmin]

    def get_membership(self, request, user_id):
        return TenantMembership.objects.using("default").filter(
            tenant=request.tenant,
            user_id=user_id
        ).select_related("user").first()

    # Detalle
    def get(self, request, user_id):
        membership = self.get_membership(request, user_id)

        if not membership:
            return Response(
                {"detail": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(membership_to_dict(membership))

    # Modificar
    def patch(self, request, user_id):
        membership = self.get_membership(request, user_id)

        if not membership:
            return Response(
                {"detail": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        user = membership.user
        data = request.data

        # Username
        if "username" in data:
            username = str(data["username"]).strip()

            if not username:
                return Response(
                    {"detail": "El username no puede estar vacío."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            username_exists = User.objects.using("default").filter(
                username=username
            ).exclude(id=user.id).exists()

            if username_exists:
                return Response(
                    {"detail": "El username ya existe."},
                    status=status.HTTP_409_CONFLICT
                )

            user.username = username

        # Datos generales
        if "email" in data:
            user.email = str(data["email"]).strip()

        if "first_name" in data:
            user.first_name = str(data["first_name"]).strip()

        if "last_name" in data:
            user.last_name = str(data["last_name"]).strip()

        if "is_staff" in data:
            user.is_staff = bool(data["is_staff"])

        if "user_active" in data:
            user.is_active = bool(data["user_active"])

        # Password
        if data.get("password"):
            password = data["password"]

            if len(password) < 6:
                return Response(
                    {"detail": "La contraseña debe tener al menos 6 caracteres."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(password)

        # Membership
        if "membership_active" in data:
            new_active = bool(data["membership_active"])

            if user.id == request.user.id and not new_active:
                return Response(
                    {"detail": "No podés desactivar tu propio acceso."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            membership.active = new_active

        try:
            with transaction.atomic(using="default"):
                user.save(using="default")
                membership.save(using="default")

        except IntegrityError:
            pp.pprint(traceback.format_exc())

            return Response(
                {"detail": "No se pudo actualizar el usuario."},
                status=status.HTTP_409_CONFLICT
            )

        return Response(membership_to_dict(membership))

    # Desactivar acceso al tenant
    def delete(self, request, user_id):
        membership = self.get_membership(request, user_id)

        if not membership:
            return Response(
                {"detail": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        if membership.user_id == request.user.id:
            return Response(
                {"detail": "No podés eliminar tu propio acceso."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # No eliminamos el User global, solo desactivamos el acceso al tenant.
        membership.active = False
        membership.save(using="default", update_fields=["active"])

        return Response(status=status.HTTP_204_NO_CONTENT)