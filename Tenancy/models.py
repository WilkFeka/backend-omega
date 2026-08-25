from django.conf import settings
from django.db import models


class Tenant(models.Model):
    name = models.CharField(
        max_length=150
    )

    slug = models.SlugField(
        max_length=100,
        unique=True
    )

    domain = models.CharField(
        max_length=255,
        unique=True
    )

    database_alias = models.CharField(
        max_length=100
    )

    active = models.BooleanField(
        default=True
    )

    config = models.JSONField(
        default=dict,
        blank=True
    )

    def __str__(self):
        return self.name


class TenantMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE
    )

    active = models.BooleanField(
        default=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tenant"],
                name="unique_user_tenant"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.tenant}"