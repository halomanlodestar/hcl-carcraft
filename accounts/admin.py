from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CarCraftUserAdmin(UserAdmin):
    list_display = ["username", "first_name", "last_name", "role", "phone", "city", "is_active"]
    list_filter = ["role", "is_active", "is_staff"]
    fieldsets = UserAdmin.fieldsets + (("CarCraft", {"fields": ("role", "phone", "address", "city")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("CarCraft", {"fields": ("role", "phone")}),)
