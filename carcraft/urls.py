from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "CarCraft Admin"
admin.site.site_title = "CarCraft"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("inventory/", include("inventory.urls")),
    path("store/", include("store.urls")),
    path("service/", include("service.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("", include("core.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
