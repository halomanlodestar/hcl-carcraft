from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from inventory.models import Sale, TestDrive, TradeInRequest, Vehicle
from service.models import ServiceJob, ServicePart
from store.models import Order, OrderItem, Part

PAID_STATES = ["PAID", "SHIPPED", "DELIVERED"]
ZERO = Decimal("0")


def month_starts(n=12):
    """First day of each of the last n months (oldest first), timezone-aware."""
    now = timezone.localtime()
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    months = []
    for _ in range(n):
        months.append(first)
        first = (first - timedelta(days=1)).replace(day=1)
    return list(reversed(months))


def _monthly(qs, date_field, value_expr, months):
    rows = (qs.filter(**{f"{date_field}__gte": months[0]})
            .annotate(m=TruncMonth(date_field)).values("m").annotate(v=value_expr).values_list("m", "v"))
    by_month = {timezone.localtime(m).date().replace(day=1): v or 0 for m, v in rows}
    return [float(by_month.get(m.date(), 0)) for m in months]


def revenue_series(months):
    cars = _monthly(Sale.objects.all(), "sold_at", Sum("sale_price"), months)
    parts = _monthly(Order.objects.filter(status__in=PAID_STATES), "paid_at", Sum("subtotal") - Sum("discount"), months)
    labour = _monthly(ServiceJob.objects.filter(status="DELIVERED"), "completed_at", Sum("labour_charge"), months)
    line = ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField())
    svc_parts = _monthly(ServicePart.objects.filter(job__status="DELIVERED").annotate(line=line), "job__completed_at", Sum("line"), months)
    service = [a + b for a, b in zip(labour, svc_parts)]
    return {"cars": cars, "parts": parts, "service": service}


def kpis():
    now = timezone.localtime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_start = (month_start - timedelta(days=1)).replace(day=1)

    def rev(start, end):
        cars = Sale.objects.filter(sold_at__gte=start, sold_at__lt=end).aggregate(v=Coalesce(Sum("sale_price"), ZERO))["v"]
        parts = Order.objects.filter(status__in=PAID_STATES, paid_at__gte=start, paid_at__lt=end).aggregate(
            v=Coalesce(Sum("total"), ZERO))["v"]
        service = ServiceJob.objects.filter(status="DELIVERED", completed_at__gte=start, completed_at__lt=end).aggregate(
            v=Coalesce(Sum("labour_charge"), ZERO))["v"]
        return cars + parts + service

    this_month, last_month = rev(month_start, now + timedelta(days=1)), rev(prev_start, month_start)
    change = float((this_month - last_month) / last_month * 100) if last_month else None
    days_to_sell = Sale.objects.annotate(d=F("sold_at") - F("vehicle__created_at")).aggregate(a=Avg("d"))["a"]
    return {
        "revenue_month": this_month,
        "revenue_change": change,
        "in_stock": Vehicle.objects.exclude(status="SOLD").count(),
        "stock_value": Vehicle.objects.exclude(status="SOLD").aggregate(v=Coalesce(Sum("price"), ZERO))["v"],
        "cars_sold_month": Sale.objects.filter(sold_at__gte=month_start).count(),
        "open_jobs": ServiceJob.objects.filter(status__in=ServiceJob.ACTIVE_STATUSES).count(),
        "unassigned_jobs": ServiceJob.objects.filter(status__in=ServiceJob.ACTIVE_STATUSES, mechanic__isnull=True).count(),
        "low_stock": Part.objects.filter(stock_qty__lte=F("reorder_level")).count(),
        "orders_to_ship": Order.objects.filter(status="PAID").count(),
        "avg_days_to_sell": round(days_to_sell.days) if days_to_sell else None,
        "pending_test_drives": TestDrive.objects.filter(status="REQUESTED").count(),
        "pending_trade_ins": TradeInRequest.objects.filter(status="PENDING").count(),
    }


def top_models(limit=6):
    return list(Sale.objects.values("vehicle__vehicle_model__make__name", "vehicle__vehicle_model__name")
                .annotate(n=Count("id"), revenue=Sum("sale_price")).order_by("-n", "-revenue")[:limit])


def active_jobs_by_stage():
    counts = dict(ServiceJob.objects.filter(status__in=ServiceJob.ACTIVE_STATUSES)
                  .values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    return [(ServiceJob.Status(code).label, counts.get(code, 0)) for code in ServiceJob.ACTIVE_STATUSES]


def top_parts(limit=6):
    return list(OrderItem.objects.filter(order__status__in=PAID_STATES).values("part__name")
                .annotate(qty=Sum("quantity")).order_by("-qty")[:limit])


def sales_by_person(months):
    return list(Sale.objects.filter(sold_at__gte=months[0]).values("salesperson__first_name", "salesperson__last_name")
                .annotate(n=Count("id"), revenue=Sum("sale_price")).order_by("-revenue"))


def fuel_mix():
    return list(Sale.objects.values("vehicle__fuel").annotate(n=Count("id")).order_by("-n"))
