from django.contrib import admin

from .models import CustomerVehicle, ServiceJob, ServicePart, ServiceStatusLog, ServiceType


@admin.register(CustomerVehicle)
class CustomerVehicleAdmin(admin.ModelAdmin):
    list_display = ["reg_number", "vehicle_model", "year", "owner"]
    search_fields = ["reg_number", "owner__username"]


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "labour_charge", "est_hours"]


class ServicePartInline(admin.TabularInline):
    model = ServicePart
    extra = 0


class StatusLogInline(admin.TabularInline):
    model = ServiceStatusLog
    extra = 0


@admin.register(ServiceJob)
class ServiceJobAdmin(admin.ModelAdmin):
    list_display = ["number", "customer_vehicle", "service_type", "scheduled_date", "status", "mechanic"]
    list_filter = ["status", "service_type", "mechanic"]
    inlines = [ServicePartInline, StatusLogInline]
