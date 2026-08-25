from django.http import JsonResponse

from Tenancy.context import (
    reset_tenant_db,
    set_tenant_db,
)

from Tenancy.models import Tenant


class TenantMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        host = (
            request
            .get_host()
            .split(":")[0]
            .lower()
        )

        try:
            tenant = (
                Tenant.objects
                .using("default")
                .get(
                    domain=host,
                    active=True
                )
            )

        except Tenant.DoesNotExist:
            return JsonResponse(
                {
                    "detail": "Tenant inexistente"
                },
                status=404
            )

        request.tenant = tenant

        token = set_tenant_db(
            tenant.database_alias
        )

        try:
            return self.get_response(
                request
            )

        finally:
            reset_tenant_db(token)