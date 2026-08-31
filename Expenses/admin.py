from django.contrib import admin
from .models import Expense, ExpenseAttachment

admin.site.register(Expense)
admin.site.register(ExpenseAttachment)
