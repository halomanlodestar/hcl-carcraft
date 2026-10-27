from django.contrib import admin

from .models import Make, Sale, TestDrive, TradeInRequest, Vehicle, VehicleModel


class VehicleModelInline(admin.TabularInline):
    model = VehicleModel
    extra = 0


@admin.register(Make)
class MakeAdmin(admin.ModelAdmin):
    list_display = ["name", "country"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [VehicleModelInline]


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ["__str__", "body_type", "base_price"]
    list_filter = ["make", "body_type"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["__str__", "condition", "fuel", "transmission", "price", "status", "created_at"]
    list_filter = ["status", "condition", "fuel", "transmission", "vehicle_model__make"]
    search_fields = ["vin", "variant", "vehicle_model__name"]


@admin.register(TestDrive)
class TestDriveAdmin(admin.ModelAdmin):
    list_display = ["vehicle", "customer", "scheduled_at", "status"]
    list_filter = ["status"]


@admin.register(TradeInRequest)
class TradeInAdmin(admin.ModelAdmin):
    list_display = ["__str__", "estimated_value", "offered_value", "status"]
    list_filter = ["status"]


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ["vehicle", "customer", "salesperson", "sale_price", "sold_at"]
    date_hierarchy = "sold_at"
