from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.mixins import role_required
from inventory.models import Sale, TestDrive, TradeInRequest, Vehicle
from service.models import ServiceJob
from store.models import Order, Part
from store.services import adjust_stock

from . import queries


@login_required
def home(request):
    user = request.user
    if user.is_mechanic:
        return redirect("service:queue")
    if user.is_admin_role:
        return admin_dashboard(request)
    if user.is_sales:
        return sales_dashboard(request)
    return customer_dashboard(request)


def customer_dashboard(request):
    user = request.user
    garage = list(user.garage.select_related("vehicle_model__make"))
    active_jobs = (ServiceJob.objects.filter(customer_vehicle__owner=user, status__in=ServiceJob.ACTIVE_STATUSES)
                   .select_related("customer_vehicle__vehicle_model__make", "service_type"))
    upcoming = (user.test_drives.filter(scheduled_at__gte=timezone.now(), status__in=["REQUESTED", "CONFIRMED"])
                .select_related("vehicle__vehicle_model__make")[:3])
    orders = user.orders.exclude(status="CANCELLED")[:4]
    offers = user.trade_ins.filter(status="OFFERED").select_related("vehicle_model__make")
    return render(request, "dashboard/customer.html", {
        "garage": garage, "due": [c for c in garage if c.is_service_due and not c.active_job],
        "active_jobs": active_jobs, "upcoming": upcoming, "orders": orders, "offers": offers,
    })


def sales_dashboard(request):
    user = request.user
    month_start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mine = Sale.objects.filter(salesperson=user)
    mine_month = mine.filter(sold_at__gte=month_start)
    today = timezone.localdate()
    drives = (TestDrive.objects.filter(status__in=["REQUESTED", "CONFIRMED"], scheduled_at__date__gte=today)
              .select_related("vehicle__vehicle_model__make", "customer").order_by("scheduled_at")[:6])
    months = queries.month_starts(6)
    my_series = queries._monthly(mine, "sold_at", Sum("sale_price"), months)
    return render(request, "dashboard/sales.html", {
        "kpi": {
            "my_sales_month": mine_month.count(),
            "my_revenue_month": mine_month.aggregate(v=Sum("sale_price"))["v"] or 0,
            "pending_drives": TestDrive.objects.filter(status="REQUESTED").count(),
            "pending_trade_ins": TradeInRequest.objects.filter(status="PENDING").count(),
            "in_stock": Vehicle.objects.exclude(status="SOLD").count(),
        },
        "drives": drives,
        "trade_ins": TradeInRequest.objects.filter(status="PENDING").select_related("vehicle_model__make", "customer")[:5],
        "recent_sales": mine.select_related("vehicle__vehicle_model__make", "customer")[:5],
        "chart": {"labels": [m.strftime("%b") for m in months], "values": my_series},
    })


def admin_dashboard(request):
    months = queries.month_starts(6)
    series = queries.revenue_series(months)
    return render(request, "dashboard/admin.html", {
        "kpi": queries.kpis(),
        "low_stock": Part.objects.filter(stock_qty__lte=F("reorder_level")).select_related("category").order_by("stock_qty")[:6],
        "unassigned": (ServiceJob.objects.filter(status__in=ServiceJob.ACTIVE_STATUSES, mechanic__isnull=True)
                       .select_related("customer_vehicle__vehicle_model__make", "service_type")[:5]),
        "to_ship": Order.objects.filter(status="PAID").select_related("customer")[:5],
        "recent_sales": Sale.objects.select_related("vehicle__vehicle_model__make", "customer", "salesperson")[:5],
        "chart": {"labels": [m.strftime("%b") for m in months], **series},
    })


@role_required("ADMIN", "SALES")
def analytics(request):
    months = queries.month_starts(12)
    series = queries.revenue_series(months)
    top = queries.top_models()
    jobs = queries.active_jobs_by_stage()
    parts = queries.top_parts()
    people = queries.sales_by_person(months)
    fuel = queries.fuel_mix()
    data = {
        "months": [m.strftime("%b %y") for m in months],
        "revenue": series,
        "top_models": {"labels": [f"{r['vehicle__vehicle_model__make__name']} {r['vehicle__vehicle_model__name']}" for r in top],
                       "values": [r["n"] for r in top]},
        "jobs": {"labels": [j[0] for j in jobs], "values": [j[1] for j in jobs]},
        "parts": {"labels": [p["part__name"] for p in parts], "values": [p["qty"] for p in parts]},
        "people": {"labels": [f"{p['salesperson__first_name']} {p['salesperson__last_name'][:1]}." for p in people],
                   "values": [float(p["revenue"]) for p in people]},
        "fuel": {"labels": [dict(Vehicle.Fuel.choices).get(f["vehicle__fuel"]) for f in fuel], "values": [f["n"] for f in fuel]},
    }
    total_12m = sum(series["cars"]) + sum(series["parts"]) + sum(series["service"])
    best_month_idx = max(range(12), key=lambda i: series["cars"][i] + series["parts"][i] + series["service"][i])
    return render(request, "dashboard/analytics.html", {
        "data": data, "kpi": queries.kpis(), "total_12m": total_12m,
        "best_month": months[best_month_idx], "sales_only": request.user.is_sales,
    })


@role_required("ADMIN", "MECHANIC")
def low_stock(request):
    show_all = request.GET.get("all") == "1"
    parts = Part.objects.select_related("category")
    if not show_all:
        parts = parts.filter(stock_qty__lte=F("reorder_level"))
    parts = parts.order_by("stock_qty", "name")
    return render(request, "dashboard/low_stock.html", {"parts": parts, "show_all": show_all})


@role_required("ADMIN")
@require_POST
def restock(request, pk):
    part = get_object_or_404(Part, pk=pk)
    try:
        qty = int(request.POST.get("qty", 0))
    except ValueError:
        qty = 0
    if qty > 0:
        adjust_stock(part, qty)
        messages.success(request, f"Restocked {part.name}: +{qty} units.")
    return redirect(request.POST.get("next") or "dashboard:low_stock")
