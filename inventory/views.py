from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.mixins import role_required
from core.pdf import render_pdf

from . import services
from .forms import OfferForm, SaleForm, TradeInForm
from .models import SPEC_LABELS, Make, Sale, TestDrive, TradeInRequest, Vehicle, VehicleModel

COMPARE_MAX = 4

SORTS = {
    "newest": ("Newest first", "-created_at"),
    "price_asc": ("Price: low to high", "price"),
    "price_desc": ("Price: high to low", "-price"),
    "km": ("Lowest km", "mileage_km"),
    "year": ("Latest model year", "-year"),
}

PRICE_STEPS = [300000, 500000, 800000, 1000000, 1500000, 2000000, 2500000, 3500000]


def _safe_next(request, fallback):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return fallback


def vehicle_list(request):
    qs = Vehicle.objects.exclude(status=Vehicle.Status.SOLD).select_related("vehicle_model__make")
    g = request.GET
    q = g.get("q", "").strip()
    makes = g.getlist("make")
    bodies = g.getlist("body")
    fuels = g.getlist("fuel")
    transmission = g.get("transmission", "")
    condition = g.get("condition", "")
    min_price, max_price = g.get("min_price", ""), g.get("max_price", "")
    sort = g.get("sort", "newest") if g.get("sort") in SORTS else "newest"

    if q:
        vector = (SearchVector("vehicle_model__make__name", weight="A") + SearchVector("vehicle_model__name", weight="A")
                  + SearchVector("variant", weight="B") + SearchVector("color", weight="C"))
        query = SearchQuery(q, search_type="websearch")
        qs = qs.annotate(rank=SearchRank(vector, query)).filter(
            Q(rank__gt=0) | Q(vehicle_model__name__icontains=q) | Q(vehicle_model__make__name__icontains=q)
        )
    if makes:
        qs = qs.filter(vehicle_model__make__slug__in=makes)
    if bodies:
        qs = qs.filter(vehicle_model__body_type__in=bodies)
    if fuels:
        qs = qs.filter(fuel__in=fuels)
    if transmission:
        qs = qs.filter(transmission=transmission)
    if condition:
        qs = qs.filter(condition=condition)
    if min_price.isdigit():
        qs = qs.filter(price__gte=int(min_price))
    if max_price.isdigit():
        qs = qs.filter(price__lte=int(max_price))

    order = SORTS[sort][1]
    qs = qs.order_by("-rank", order) if q and not g.get("sort") else qs.order_by(order)
    page = Paginator(qs, 12).get_page(g.get("page"))

    make_objs = Make.objects.all()
    make_names = {m.slug: m for m in make_objs}
    active = []
    for slug in makes:
        if slug in make_names:
            active.append(("make", slug, make_names[slug].name))
    body_labels = dict(VehicleModel.BodyType.choices)
    active += [("body", b, body_labels.get(b, b)) for b in bodies]
    fuel_labels = dict(Vehicle.Fuel.choices)
    active += [("fuel", f, fuel_labels.get(f, f)) for f in fuels]
    if transmission:
        active.append(("transmission", transmission, dict(Vehicle.Transmission.choices).get(transmission)))
    if condition:
        active.append(("condition", condition, dict(Vehicle.Condition.choices).get(condition)))
    if min_price:
        active.append(("min_price", min_price, f"From ₹{int(min_price) / 100000:g} L"))
    if max_price:
        active.append(("max_price", max_price, f"Up to ₹{int(max_price) / 100000:g} L"))
    if q:
        active.append(("q", q, f"“{q}”"))

    def remove_url(key, value):
        params = g.copy()
        vals = [v for v in params.getlist(key) if v != value]
        params.setlist(key, vals)
        params.pop("page", None)
        return "?" + params.urlencode()

    active = [(label, remove_url(key, value)) for key, value, label in active]

    return render(request, "inventory/vehicle_list.html", {
        "page": page,
        "makes": make_objs,
        "body_types": VehicleModel.BodyType.choices,
        "fuels": Vehicle.Fuel.choices,
        "transmissions": Vehicle.Transmission.choices,
        "conditions": Vehicle.Condition.choices,
        "sorts": [(k, v[0]) for k, v in SORTS.items()],
        "price_steps": PRICE_STEPS,
        "sel": {"q": q, "make": makes, "body": bodies, "fuel": fuels, "transmission": transmission,
                "condition": condition, "min_price": min_price, "max_price": max_price, "sort": sort},
        "active_filters": active,
    })


def vehicle_detail(request, pk):
    v = get_object_or_404(Vehicle.objects.select_related("vehicle_model__make"), pk=pk)
    specs = [(SPEC_LABELS[k][0], v.specs[k], SPEC_LABELS[k][1], SPEC_LABELS[k][2])
             for k in SPEC_LABELS if k in v.specs]
    similar = (Vehicle.objects.exclude(pk=v.pk).exclude(status=Vehicle.Status.SOLD)
               .filter(vehicle_model__body_type=v.vehicle_model.body_type)
               .select_related("vehicle_model__make").order_by("?")[:3])
    passport = None
    if v.reg_number:
        from passport.valuation import passport_for

        passport = passport_for(v.reg_number, v.mileage_km)
    return render(request, "inventory/vehicle_detail.html", {"v": v, "specs": specs, "similar": similar,
                                                             "record": passport[0] if passport else None,
                                                             "passport": passport[1] if passport else None})


@require_POST
def compare_toggle(request, pk):
    ids = request.session.get("compare", [])
    if pk in ids:
        ids.remove(pk)
    elif len(ids) >= COMPARE_MAX:
        messages.warning(request, f"You can compare up to {COMPARE_MAX} cars. Remove one first.")
    else:
        get_object_or_404(Vehicle, pk=pk)
        ids.append(pk)
    request.session["compare"] = ids
    return redirect(_safe_next(request, reverse("inventory:compare")))


@require_POST
def compare_clear(request):
    request.session["compare"] = []
    return redirect("inventory:list")


def compare(request):
    ids = request.session.get("compare", [])
    vehicles = list(Vehicle.objects.filter(pk__in=ids).select_related("vehicle_model__make"))
    vehicles.sort(key=lambda v: ids.index(v.pk))
    rows = []
    if vehicles:
        def best_index(values, prefer):
            nums = [(i, x) for i, x in enumerate(values) if isinstance(x, (int, float))]
            if len(nums) < 2:
                return None
            fn = min if prefer == "min" else max
            target = fn(x for _, x in nums)
            return [i for i, x in nums if x == target]

        prices = [float(v.price) for v in vehicles]
        rows.append(("Price", "bi-currency-rupee", [("price", v.price) for v in vehicles], best_index(prices, "min")))
        rows.append(("Model year", "bi-calendar3", [("text", v.year) for v in vehicles], best_index([v.year for v in vehicles], "max")))
        rows.append(("Fuel", "bi-fuel-pump", [("text", v.get_fuel_display()) for v in vehicles], None))
        rows.append(("Transmission", "bi-gear-wide-connected", [("text", v.get_transmission_display()) for v in vehicles], None))
        rows.append(("Kilometres", "bi-speedometer2", [("km", v.mileage_km) for v in vehicles], best_index([v.mileage_km for v in vehicles], "min")))
        prefer = {"mileage_kmpl": "max", "power_bhp": "max", "torque_nm": "max", "boot_l": "max", "airbags": "max",
                  "seats": "max", "range_km": "max", "ground_clearance_mm": "max", "engine_cc": None, "battery_kwh": "max"}
        for key, (label, unit, icon) in SPEC_LABELS.items():
            values = [v.specs.get(key) for v in vehicles]
            if all(x is None for x in values):
                continue
            best = best_index(values, prefer[key]) if prefer.get(key) else None
            rows.append((label, icon, [("spec", (x, unit)) for x in values], best))
        all_features = sorted({f for v in vehicles for f in v.features})
        feature_rows = [(f, [f in v.features for v in vehicles]) for f in all_features]
    else:
        feature_rows = []
    suggestions = []
    if len(vehicles) < COMPARE_MAX:
        suggestions = (Vehicle.objects.exclude(status=Vehicle.Status.SOLD).exclude(pk__in=ids)
                       .select_related("vehicle_model__make").order_by("?")[:4])
    return render(request, "inventory/compare.html", {
        "vehicles": vehicles, "rows": rows, "feature_rows": feature_rows, "suggestions": suggestions,
        "slots_left": range(COMPARE_MAX - len(vehicles)),
    })


# ---------------------------------------------------------------- test drives

@role_required("CUSTOMER")
def test_drive_book(request, pk):
    v = get_object_or_404(Vehicle.objects.select_related("vehicle_model__make"), pk=pk)
    today = timezone.localdate()
    days = [today + timedelta(days=i) for i in range(1, 8)]
    try:
        selected = datetime.strptime(request.GET.get("date") or request.POST.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        selected = days[0]
    if selected not in days:
        selected = days[0]

    if request.method == "POST":
        slot = request.POST.get("slot", "")
        try:
            hour = int(slot)
            when = timezone.make_aware(datetime.combine(selected, datetime.min.time().replace(hour=hour)))
            services.book_test_drive(v, request.user, when, request.POST.get("notes", "")[:500])
        except (ValueError, TypeError) as e:
            messages.error(request, str(e) if str(e) and not slot == "" else "Please pick a time slot.")
        else:
            messages.success(request, f"Test drive requested for {when:%a %d %b, %I:%M %p}. We'll confirm shortly.")
            return redirect("inventory:my_test_drives")

    taken = services.booked_slots(v, selected)
    slots = [(t.hour, t.strftime("%I:%M %p").lstrip("0"), t in taken) for t in services.TEST_DRIVE_SLOTS]
    return render(request, "inventory/test_drive_form.html", {"v": v, "days": days, "selected": selected, "slots": slots})


@role_required("CUSTOMER")
def my_test_drives(request):
    drives = request.user.test_drives.select_related("vehicle__vehicle_model__make").order_by("-scheduled_at")
    now = timezone.now()
    upcoming = [d for d in drives if d.scheduled_at >= now and d.status in ("REQUESTED", "CONFIRMED")]
    past = [d for d in drives if d not in upcoming]
    return render(request, "inventory/my_test_drives.html", {"upcoming": upcoming, "past": past})


@role_required("CUSTOMER")
@require_POST
def test_drive_cancel(request, pk):
    td = get_object_or_404(TestDrive, pk=pk, customer=request.user, status__in=["REQUESTED", "CONFIRMED"])
    td.status = TestDrive.Status.CANCELLED
    td.save(update_fields=["status"])
    messages.info(request, "Test drive cancelled.")
    return redirect("inventory:my_test_drives")


@role_required("SALES", "ADMIN")
def test_drive_queue(request):
    tab = request.GET.get("tab", "REQUESTED")
    base = TestDrive.objects.select_related("vehicle__vehicle_model__make", "customer", "handled_by")
    counts = dict(base.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    tabs = [(code, label, counts.get(code, 0)) for code, label in TestDrive.Status.choices]
    drives = base.filter(status=tab)
    drives = drives.order_by("scheduled_at") if tab in ("REQUESTED", "CONFIRMED") else drives.order_by("-scheduled_at")
    return render(request, "inventory/test_drive_queue.html", {"drives": drives[:100], "tabs": tabs, "tab": tab})


@role_required("SALES", "ADMIN")
@require_POST
def test_drive_action(request, pk):
    td = get_object_or_404(TestDrive, pk=pk)
    status = request.POST.get("status")
    if status in ("CONFIRMED", "COMPLETED", "CANCELLED"):
        services.set_test_drive_status(td, status, request.user)
        messages.success(request, f"Test drive marked {status.lower()}.")
    return redirect(_safe_next(request, reverse("inventory:test_drives")))


# ---------------------------------------------------------------- trade-ins

def trade_in(request):
    from passport.models import RegistryRecord
    from passport.valuation import passport_for

    initial = {}
    reg = request.GET.get("reg", "").upper()
    rec = RegistryRecord.objects.filter(reg_number=reg).first() if reg else None
    if rec:  # prefill from the registry so the customer only confirms condition
        latest = rec.odometer.order_by("-read_on").first()
        initial = {"reg_number": reg, "vehicle_model": rec.vehicle_model_id, "year": rec.manufacture_year,
                   "km_driven": latest.km if latest else None}
    form = TradeInForm(request.POST or None, initial=initial)
    estimate = valuation = None
    reg_not_found = False
    if request.method == "POST" and form.is_valid():
        d = dict(form.cleaned_data)
        reg = d.pop("reg_number")
        if reg:
            record, valuation = passport_for(reg, d["km_driven"], d["condition_rating"])
            if record:
                d["vehicle_model"], d["year"] = record.vehicle_model, record.manufacture_year
            else:
                reg_not_found = True
        estimate = valuation.final if valuation else services.estimate_trade_in(d["vehicle_model"], d["year"], d["km_driven"], d["condition_rating"])
        if request.user.is_authenticated and request.user.is_customer and request.POST.get("submit_offer"):
            TradeInRequest.objects.create(customer=request.user, estimated_value=estimate, reg_number=reg if valuation else "", **d)
            messages.success(request, "Trade-in submitted! Our team will send you a firm offer within 24 hours.")
            return redirect("inventory:my_trade_ins")
    return render(request, "inventory/trade_in_form.html", {
        "form": form, "estimate": estimate, "valuation": valuation, "reg_not_found": reg_not_found,
        "passport_reg": form.cleaned_data.get("reg_number") if form.is_bound and form.is_valid() else "",
        "condition_icons": {"EXCELLENT": "bi-emoji-heart-eyes", "GOOD": "bi-emoji-smile", "FAIR": "bi-emoji-neutral", "POOR": "bi-emoji-frown"},
        "condition_hints": {"EXCELLENT": "Like new, full service history", "GOOD": "Minor wear, no major repairs",
                            "FAIR": "Visible wear, some repairs due", "POOR": "Needs significant work"},
    })


@role_required("CUSTOMER")
def my_trade_ins(request):
    items = request.user.trade_ins.select_related("vehicle_model__make")
    return render(request, "inventory/my_trade_ins.html", {"items": items})


@role_required("CUSTOMER")
@require_POST
def trade_in_respond(request, pk):
    t = get_object_or_404(TradeInRequest, pk=pk, customer=request.user, status=TradeInRequest.Status.OFFERED)
    if request.POST.get("decision") == "reject":
        t.status = TradeInRequest.Status.REJECTED
        t.save(update_fields=["status"])
        messages.info(request, "Offer declined.")
    else:
        messages.success(request, "Great! Visit the showroom and we'll apply this credit to your new car.")
    return redirect("inventory:my_trade_ins")


@role_required("SALES", "ADMIN")
def trade_in_queue(request):
    tab = request.GET.get("tab", "PENDING")
    base = TradeInRequest.objects.select_related("vehicle_model__make", "customer")
    counts = dict(base.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    tabs = [(code, label, counts.get(code, 0)) for code, label in TradeInRequest.Status.choices]
    from passport.valuation import passport_for

    items = list(base.filter(status=tab))
    for t in items:
        t.passport = passport_for(t.reg_number, t.km_driven, t.condition_rating)[1] if t.reg_number else None
    return render(request, "inventory/trade_in_queue.html", {"items": items, "tabs": tabs, "tab": tab})


@role_required("SALES", "ADMIN")
@require_POST
def trade_in_offer(request, pk):
    t = get_object_or_404(TradeInRequest, pk=pk, status__in=["PENDING", "OFFERED"])
    if request.POST.get("decision") == "reject":
        t.status = TradeInRequest.Status.REJECTED
        t.save(update_fields=["status"])
        messages.info(request, "Trade-in rejected.")
    else:
        form = OfferForm(request.POST)
        if form.is_valid():
            services.make_trade_in_offer(t, form.cleaned_data["offered_value"])
            messages.success(request, f"Offer sent to {t.customer.display_name}.")
        else:
            messages.error(request, "Enter a valid offer amount (at least ₹1,000).")
    return redirect(reverse("inventory:trade_ins") + f"?tab={request.POST.get('tab', 'PENDING')}")


# ---------------------------------------------------------------- sales

@role_required("SALES", "ADMIN")
def sell(request, pk):
    v = get_object_or_404(Vehicle.objects.select_related("vehicle_model__make"), pk=pk)
    if v.status == Vehicle.Status.SOLD:
        messages.warning(request, "This vehicle has already been sold.")
        return redirect("inventory:detail", pk=pk)
    form = SaleForm(request.POST or None, initial={"sale_price": v.price})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        sale = services.record_sale(v, d["customer"], request.user, d["sale_price"], d["trade_in"])
        messages.success(request, f"Sale recorded. {v.title} is now with {d['customer'].display_name}.")
        return redirect("inventory:sale_detail", pk=sale.pk)
    return render(request, "inventory/sell_form.html", {"v": v, "form": form})


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("vehicle__vehicle_model__make", "customer", "salesperson", "trade_in__vehicle_model"), pk=pk)
    if not (request.user.is_admin_role or request.user.is_sales or sale.customer_id == request.user.pk):
        return redirect("core:home")
    return render(request, "inventory/sale_detail.html", {"sale": sale})


@login_required
def sale_invoice(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("vehicle__vehicle_model__make", "customer", "salesperson", "trade_in__vehicle_model"), pk=pk)
    if not (request.user.is_admin_role or request.user.is_sales or sale.customer_id == request.user.pk):
        return redirect("core:home")
    return render_pdf("invoices/sale.html", {"sale": sale}, f"carcraft-sale-{sale.pk}.pdf")


@role_required("SALES", "ADMIN")
def sales_list(request):
    sales = Sale.objects.select_related("vehicle__vehicle_model__make", "customer", "salesperson")
    if request.user.is_sales and request.GET.get("mine"):
        sales = sales.filter(salesperson=request.user)
    page = Paginator(sales, 20).get_page(request.GET.get("page"))
    return render(request, "inventory/sales_list.html", {"page": page})


# ---------------------------------------------------------------- upgrade planner

TENURES = [36, 48, 60, 72, 84]


def _num(value, default, lo=0, hi=10**8):
    try:
        return max(lo, min(hi, Decimal(str(value).replace(",", ""))))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


@role_required("CUSTOMER")
def upgrade(request):
    from passport.valuation import passport_for

    cars = list(request.user.garage.select_related("vehicle_model__make"))
    if not cars:
        messages.info(request, "Add your current car to your garage to see what you can upgrade to.")
        return redirect("service:garage_add")
    g = request.GET
    car = next((c for c in cars if str(c.pk) == g.get("car")), None) or min(cars, key=lambda c: c.year)

    record, valuation = passport_for(car.reg_number, car.km_driven)
    trade_value = valuation.final if valuation else services.estimate_trade_in(car.vehicle_model, car.year, car.km_driven, "GOOD")
    outstanding = _num(g.get("loan"), car.loan_outstanding)
    current_emi = _num(g.get("emi"), car.current_emi)
    extra_down = _num(g.get("down"), 0, hi=5_000_000)
    rate = _num(g.get("rate"), "9.5", lo=6, hi=18)
    months = int(g.get("months")) if g.get("months", "").isdigit() and int(g.get("months")) in TENURES else 60

    equity, bands = services.upgrade_options(trade_value, outstanding, current_emi, extra_down, rate, months,
                                            car.vehicle_model, car.year)
    total = max(trade_value, outstanding) or 1
    return render(request, "inventory/upgrade.html", {
        "cars": cars, "car": car, "valuation": valuation, "trade_value": trade_value,
        "outstanding": outstanding, "current_emi": current_emi, "extra_down": extra_down, "rate": rate, "months": months,
        "tenures": TENURES, "equity": equity, "bands": bands, "matches": sum(len(b[3]) for b in bands),
        "equity_pct": float(min(trade_value, outstanding) / total * 100) if outstanding else 0,
    })
