from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:pk>/open/", views.notification_open, name="notification_open"),
    path("notifications/read/", views.notifications_read, name="notifications_read"),
]
