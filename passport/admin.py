from django.contrib import admin

from .models import Challan, InsuranceClaim, OdometerReading, OwnershipPeriod, RegistryRecord


class OwnershipInline(admin.TabularInline):
    model = OwnershipPeriod
    extra = 0


class ChallanInline(admin.TabularInline):
    model = Challan
    extra = 0


class ClaimInline(admin.TabularInline):
    model = InsuranceClaim
    extra = 0


class OdometerInline(admin.TabularInline):
    model = OdometerReading
    extra = 0


@admin.register(RegistryRecord)
class RegistryRecordAdmin(admin.ModelAdmin):
    list_display = ["reg_number", "vehicle_model", "manufacture_year", "rto", "hypothecated_to"]
    search_fields = ["reg_number"]
    inlines = [OwnershipInline, ChallanInline, ClaimInline, OdometerInline]
