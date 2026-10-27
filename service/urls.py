from django.urls import path

from . import views

app_name = "service"
urlpatterns = [
    path("garage/", views.garage, name="garage"),
    path("garage/add/", views.garage_add, name="garage_add"),
    path("book/", views.book, name="book"),
    path("jobs/<int:pk>/", views.job_detail, name="job_detail"),
    path("jobs/<int:pk>/advance/", views.job_advance, name="job_advance"),
    path("jobs/<int:pk>/assign/", views.job_assign, name="job_assign"),
    path("jobs/<int:pk>/parts/add/", views.job_add_part, name="job_add_part"),
    path("jobs/<int:pk>/parts/<int:part_pk>/remove/", views.job_remove_part, name="job_remove_part"),
    path("jobs/<int:pk>/invoice/", views.job_invoice, name="job_invoice"),
    path("queue/", views.queue, name="queue"),
    path("manage/", views.manage, name="manage"),
]
