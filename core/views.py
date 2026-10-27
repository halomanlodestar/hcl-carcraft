from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from inventory.models import Make, Sale, Vehicle, VehicleModel
from store.models import Part, PartCategory

from .models import Notification

CATEGORY_TINTS = ["#e0313b", "#2e90fa", "#12b76a", "#f79009", "#7a5af8", "#ee46bc", "#0ba5ec", "#667085"]


def home(request):
    available = Vehicle.objects.exclude(status=Vehicle.Status.SOLD)
    featured = available.select_related("vehicle_model__make").order_by("-created_at")[:6]
    makes = Make.objects.annotate(n=Count("models__vehicles", filter=~Q(models__vehicles__status="SOLD")))
    categories = PartCategory.objects.annotate(n=Count("parts"))
    body_counts = dict(
        available.values_list("vehicle_model__body_type").annotate(n=Count("id")).values_list("vehicle_model__body_type", "n")
    )
    body_types = [(code, label, body_counts.get(code, 0)) for code, label in VehicleModel.BodyType.choices]
    return render(request, "core/home.html", {
        "featured": featured,
        "makes": makes,
        "categories": [(c, CATEGORY_TINTS[i % len(CATEGORY_TINTS)]) for i, c in enumerate(categories)],
        "body_types": body_types,
        "stats": {
            "in_stock": available.count(),
            "brands": makes.count(),
            "sold": Sale.objects.count(),
            "parts": Part.objects.count(),
        },
    })


@login_required
def notifications(request):
    qs = request.user.notifications.all()
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "core/notifications.html", {"page": page})


@login_required
def notification_open(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])
    return redirect(n.link or "core:notifications")


@login_required
@require_POST
def notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER") or "core:notifications")
