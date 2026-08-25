import json
import traceback

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django.middleware.csrf import get_token

from Tenancy.models import TenantMembership
import pprint as pp

# ============================================================
# CSRF
# ============================================================

@ensure_csrf_cookie
@require_GET
def csrf(request):
    csrf_token = get_token(request)
    return JsonResponse({
        "detail": "CSRF cookie set",
        "csrf_token": csrf_token

    })


# ============================================================
# LOGIN
# ============================================================

@require_POST
def login_view(request):

    try:
        data = json.loads(request.body)

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "detail": "JSON inválido"
            },
            status=400
        )

    username = data.get("username")
    password = data.get("password")
    remember_me = data.get("remember_me", False)

    if not username or not password:

        return JsonResponse(
            {
                "detail": "Username y password son obligatorios"
            },
            status=400
        )

    # --------------------------------------------------------
    # AUTENTICAR
    # --------------------------------------------------------

    user = authenticate(
        request,
        username=username,
        password=password
    )

    if user is None:

        return JsonResponse(
            {
                "detail": "Credenciales inválidas"
            },
            status=401
        )

    if not user.is_active:

        return JsonResponse(
            {
                "detail": "Usuario inactivo"
            },
            status=403
        )

    # --------------------------------------------------------
    # VALIDAR QUE EL USUARIO PERTENEZCA AL TENANT
    # --------------------------------------------------------

    has_access = (
        user.is_superuser
        or
        TenantMembership.objects
        .using("default")
        .filter(
            user=user,
            tenant=request.tenant,
            active=True
        )
        .exists()
    )

    if not has_access:

        return JsonResponse(
            {
                "detail": "No tenés acceso a esta empresa"
            },
            status=403
        )

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    login(request, user)

    # Vinculamos la sesión al tenant actual.
    request.session["tenant_id"] = request.tenant.id

    # --------------------------------------------------------
    # REMEMBER ME
    # --------------------------------------------------------

    if remember_me:

        request.session.set_expiry(
            60 * 60 * 24 * 30
        )

    else:

        request.session.set_expiry(0)

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return JsonResponse({
        "id": user.id,
        "username": user.get_username(),
        "email": user.email,

        "tenant": {
            "id": request.tenant.id,
            "name": request.tenant.name,
            "slug": request.tenant.slug
        }
    })


# ============================================================
# LOGOUT
# ============================================================

@require_POST
def logout_view(request):

    logout(request)

    return JsonResponse({
        "detail": "Sesión cerrada"
    })


# ============================================================
# ME
# ============================================================

@require_GET
def me(request):

    if not request.user.is_authenticated:

        return JsonResponse(
            {
                "authenticated": False
            },
            status=401
        )

    user = request.user

    # --------------------------------------------------------
    # VALIDAR QUE LA SESIÓN SEA DEL TENANT ACTUAL
    # --------------------------------------------------------

    session_tenant_id = request.session.get(
        "tenant_id"
    )

    if session_tenant_id != request.tenant.id:

        logout(request)

        return JsonResponse(
            {
                "authenticated": False,
                "detail": "La sesión no pertenece a esta empresa"
            },
            status=401
        )

    # --------------------------------------------------------
    # VALIDAR QUE TODAVÍA TENGA ACCESO
    # --------------------------------------------------------

    has_access = (
        user.is_superuser
        or
        TenantMembership.objects
        .using("default")
        .filter(
            user=user,
            tenant=request.tenant,
            active=True
        )
        .exists()
    )

    if not has_access:

        logout(request)

        return JsonResponse(
            {
                "authenticated": False,
                "detail": "No tenés acceso a esta empresa"
            },
            status=403
        )

    return JsonResponse({
        "authenticated": True,

        "user": {
            "id": user.id,
            "username": user.get_username(),
            "email": user.email,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },

        "tenant": {
            "id": request.tenant.id,
            "name": request.tenant.name,
            "slug": request.tenant.slug,
            "config": request.tenant.config
        }
    })


from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from Tenancy.models import TenantMembership

from .permissions import IsTenantAdmin


User = get_user_model()


def membership_to_dict(membership):

    user = membership.user

    return {
        "id": user.id,
        "username": user.get_username(),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,

        # Estado global del usuario
        "user_active": user.is_active,

        # Acceso específicamente al tenant actual
        "membership_active": membership.active,

        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


# ============================================================
# USERS
#
# GET  /api/users/
# POST /api/users/
# ============================================================
    
class UserListCreateAPIView(APIView):

    permission_classes = [
        IsTenantAdmin
    ]

    # --------------------------------------------------------
    # LISTAR
    # --------------------------------------------------------

    def get(self, request):

        memberships = (
            TenantMembership.objects
            .using("default")
            .filter(
                tenant=request.tenant
            )
            .select_related("user")
            .order_by(
                "user__first_name",
                "user__last_name",
                "user__username"
            )
        )

        users = [
            membership_to_dict(membership)
            for membership in memberships
        ]

        return Response(
            {
                "tenant": {
                    "id": request.tenant.id,
                    "name": request.tenant.name,
                    "slug": request.tenant.slug,
                },
                "count": len(users),
                "users": users,
            }
        )

    # --------------------------------------------------------
    # CREAR
    # --------------------------------------------------------

    def post(self, request):

        data = request.data

        username = str(
            data.get("username", "")
        ).strip()

        email = str(
            data.get("email", "")
        ).strip()

        password = data.get("password")

        first_name = str(
            data.get("first_name", "")
        ).strip()

        last_name = str(
            data.get("last_name", "")
        ).strip()

        is_staff = bool(
            data.get("is_staff", False)
        )

        # ----------------------------------------------------
        # VALIDACIONES
        # ----------------------------------------------------

        errors = {}

        if not username:
            errors["username"] = "El username es obligatorio."

        if not password:
            errors["password"] = "La contraseña es obligatoria."

        elif len(password) < 6:
            errors["password"] = (
                "La contraseña debe tener al menos 6 caracteres."
            )

        if errors:
            return Response(
                {
                    "detail": "Datos inválidos",
                    "errors": errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if (
            User.objects
            .using("default")
            .filter(username=username)
            .exists()
        ):
            return Response(
                {
                    "detail": "El username ya existe."
                },
                status=status.HTTP_409_CONFLICT
            )

        # ----------------------------------------------------
        # CREAR USER + MEMBERSHIP
        # ----------------------------------------------------

        try:

            with transaction.atomic(
                using="default"
            ):

                user = (
                    User.objects
                    .db_manager("default")
                    .create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        is_staff=is_staff,
                    )
                )

                membership = (
                    TenantMembership.objects
                    .using("default")
                    .create(
                        user=user,
                        tenant=request.tenant,
                        active=True
                    )
                )

        except IntegrityError:

            pp.pprint(traceback.format_exc())

            return Response(
                {
                    "detail":
                        "No se pudo crear el usuario."
                },
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            membership_to_dict(membership),
            status=status.HTTP_201_CREATED
        )


# ============================================================
# USER DETAIL
#
# GET    /api/users/<id>/
# PATCH  /api/users/<id>/
# DELETE /api/users/<id>/
# ============================================================

class UserDetailAPIView(APIView):

    permission_classes = [
        IsTenantAdmin
    ]

    # --------------------------------------------------------
    # Obtener membership del tenant actual
    # --------------------------------------------------------

    def get_membership(self,request,user_id):

        return (
            TenantMembership.objects
            .using("default")
            .filter(
                tenant=request.tenant,
                user_id=user_id
            )
            .select_related("user")
            .first()
        )

    # --------------------------------------------------------
    # DETALLE
    # --------------------------------------------------------

    def get(
        self,
        request,
        user_id
    ):

        membership = self.get_membership(
            request,
            user_id
        )

        if not membership:

            return Response(
                {
                    "detail": "Usuario no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            membership_to_dict(membership)
        )

    # --------------------------------------------------------
    # MODIFICAR
    # --------------------------------------------------------

    def patch(
        self,
        request,
        user_id
    ):

        membership = self.get_membership(
            request,
            user_id
        )

        if not membership:

            return Response(
                {
                    "detail": "Usuario no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user = membership.user
        data = request.data

        # ----------------------------------------------------
        # USERNAME
        # ----------------------------------------------------

        if "username" in data:

            username = str(
                data["username"]
            ).strip()

            if not username:

                return Response(
                    {
                        "detail":
                            "El username no puede estar vacío."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            username_exists = (
                User.objects
                .using("default")
                .filter(
                    username=username
                )
                .exclude(
                    id=user.id
                )
                .exists()
            )

            if username_exists:

                return Response(
                    {
                        "detail":
                            "El username ya existe."
                    },
                    status=status.HTTP_409_CONFLICT
                )

            user.username = username

        # ----------------------------------------------------
        # DATOS GENERALES
        # ----------------------------------------------------

        if "email" in data:
            user.email = str(
                data["email"]
            ).strip()

        if "first_name" in data:
            user.first_name = str(
                data["first_name"]
            ).strip()

        if "last_name" in data:
            user.last_name = str(
                data["last_name"]
            ).strip()

        if "is_staff" in data:
            user.is_staff = bool(
                data["is_staff"]
            )

        if "user_active" in data:
            user.is_active = bool(
                data["user_active"]
            )

        # ----------------------------------------------------
        # PASSWORD
        # ----------------------------------------------------

        if data.get("password"):

            password = data["password"]

            if len(password) < 6:

                return Response(
                    {
                        "detail":
                            "La contraseña debe tener al menos 6 caracteres."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(password)

        # ----------------------------------------------------
        # MEMBERSHIP
        # ----------------------------------------------------

        if "membership_active" in data:

            new_active = bool(
                data["membership_active"]
            )

            # Evitar quitarse acceso a uno mismo
            if (
                user.id == request.user.id
                and not new_active
            ):

                return Response(
                    {
                        "detail":
                            "No podés desactivar tu propio acceso."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            membership.active = new_active

        # ----------------------------------------------------
        # GUARDAR
        # ----------------------------------------------------

        try:

            with transaction.atomic(
                using="default"
            ):

                user.save(
                    using="default"
                )

                membership.save(
                    using="default"
                )

        except IntegrityError:

            return Response(
                {
                    "detail":
                        "No se pudo actualizar el usuario."
                },
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            membership_to_dict(membership)
        )

    # --------------------------------------------------------
    # ELIMINAR DEL TENANT
    # --------------------------------------------------------

    def delete(
        self,
        request,
        user_id
    ):

        membership = self.get_membership(
            request,
            user_id
        )

        if not membership:

            return Response(
                {
                    "detail": "Usuario no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if membership.user_id == request.user.id:

            return Response(
                {
                    "detail":
                        "No podés eliminar tu propio acceso."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # IMPORTANTE:
        # no eliminamos el User global.
        # Solo desactivamos su acceso al tenant actual.

        membership.active = False

        membership.save(
            using="default",
            update_fields=[
                "active"
            ]
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )