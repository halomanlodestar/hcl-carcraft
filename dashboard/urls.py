from django.urls import path

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.home, name="home"),
    path("analytics/", views.analytics, name="analytics"),
    path("low-stock/", views.low_stock, name="low_stock"),
    path("low-stock/<int:pk>/restock/", views.restock, name="restock"),
]
