from django.urls import path

from . import views

app_name = "passport"
urlpatterns = [
    path("", views.check, name="check"),
    path("<str:reg>/", views.detail, name="detail"),
]
