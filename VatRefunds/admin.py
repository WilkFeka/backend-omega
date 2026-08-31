from django.contrib import admin

from .models import VatBeneficiary, VatRefundDetail

admin.site.register(VatBeneficiary)
admin.site.register(VatRefundDetail)
