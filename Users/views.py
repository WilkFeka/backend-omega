import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from Tenancy.models import TenantMembership


# ============================================================
# CSRF
# ============================================================

@ensure_csrf_cookie
@require_GET
def csrf(request):

    return JsonResponse({
        "detail": "CSRF cookie set"
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