from django.urls import path

from . import views

app_name = "store"
urlpatterns = [
    path("", views.part_list, name="list"),
    path("part/<str:sku>/", views.part_detail, name="part_detail"),
    path("api/models/", views.api_models, name="api_models"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/coupon/", views.apply_coupon, name="apply_coupon"),
    path("checkout/", views.checkout, name="checkout"),
    path("pay/<int:pk>/", views.pay, name="pay"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/<int:pk>/invoice/", views.order_invoice, name="order_invoice"),
    path("manage/orders/", views.manage_orders, name="manage_orders"),
    path("manage/orders/<int:pk>/advance/", views.order_advance, name="order_advance"),
]
