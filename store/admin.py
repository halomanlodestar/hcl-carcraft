from django.contrib import admin

from .models import Coupon, Order, OrderItem, Part, PartCategory


@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "brand", "price", "stock_qty", "reorder_level", "is_universal"]
    list_filter = ["category", "brand", "is_universal"]
    search_fields = ["sku", "name", "brand"]
    filter_horizontal = ["compatible_models"]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_type", "value", "min_order", "valid_to", "is_active"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["number", "customer", "status", "total", "created_at"]
    list_filter = ["status"]
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
