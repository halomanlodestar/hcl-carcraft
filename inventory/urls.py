from django.urls import path

from . import views

app_name = "inventory"
urlpatterns = [
    path("", views.vehicle_list, name="list"),
    path("<int:pk>/", views.vehicle_detail, name="detail"),
    path("compare/", views.compare, name="compare"),
    path("compare/toggle/<int:pk>/", views.compare_toggle, name="compare_toggle"),
    path("compare/clear/", views.compare_clear, name="compare_clear"),
    path("<int:pk>/test-drive/", views.test_drive_book, name="test_drive_book"),
    path("my/test-drives/", views.my_test_drives, name="my_test_drives"),
    path("test-drives/<int:pk>/cancel/", views.test_drive_cancel, name="test_drive_cancel"),
    path("test-drives/", views.test_drive_queue, name="test_drives"),
    path("test-drives/<int:pk>/action/", views.test_drive_action, name="test_drive_action"),
    path("trade-in/", views.trade_in, name="trade_in"),
    path("my/trade-ins/", views.my_trade_ins, name="my_trade_ins"),
    path("my/trade-ins/<int:pk>/respond/", views.trade_in_respond, name="trade_in_respond"),
    path("trade-ins/", views.trade_in_queue, name="trade_ins"),
    path("trade-ins/<int:pk>/offer/", views.trade_in_offer, name="trade_in_offer"),
    path("<int:pk>/sell/", views.sell, name="sell"),
    path("sales/", views.sales_list, name="sales"),
    path("sales/<int:pk>/", views.sale_detail, name="sale_detail"),
    path("sales/<int:pk>/invoice/", views.sale_invoice, name="sale_invoice"),
]
