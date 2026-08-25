from rest_framework.permissions import BasePermission

from Tenancy.models import TenantMembership


class IsTenantAdmin(BasePermission):

    message = "No tenés permisos para administrar usuarios."

    def has_permission(self, request, view):

        user = request.user

        if not user.is_authenticated:
            return False

        # La sesión debe pertenecer al tenant actual
        if request.session.get("tenant_id") != request.tenant.id:
            return False

        # Superuser puede administrar cualquier tenant
        if user.is_superuser:
            return True

        # Debe pertenecer al tenant actual
        has_membership = (
            TenantMembership.objects
            .using("default")
            .filter(
                user=user,
                tenant=request.tenant,
                active=True
            )
            .exists()
        )

        if not has_membership:
            return False

        # Por ahora usamos is_staff como administrador
        return user.is_staff