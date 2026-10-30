import random
import string
from datetime import time
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from core.models import Notification, notify

from .models import Sale, TestDrive, TradeInRequest, Vehicle

FIRST_YEAR_RETAINED = Decimal("0.85")
LATER_YEARS_RETAINED = Decimal("0.90")
CONDITION_FACTOR = {"EXCELLENT": Decimal("1.00"), "GOOD": Decimal("0.90"), "FAIR": Decimal("0.78"), "POOR": Decimal("0.62")}
AVG_KM_PER_YEAR = 12_000
TEST_DRIVE_SLOTS = [time(h) for h in range(10, 18)]


def estimate_trade_in(vehicle_model, year, km_driven, condition):
    """See docs/DESIGN.md §7.4."""
    base = Decimal(vehicle_model.base_price)
    age = max(0, timezone.now().year - int(year))
    value = base * (FIRST_YEAR_RETAINED * LATER_YEARS_RETAINED ** (age - 1) if age else 1)
    value *= CONDITION_FACTOR[condition]
    km_excess = max(0, int(km_driven) - age * AVG_KM_PER_YEAR)
    value *= max(Decimal("0.70"), 1 - Decimal(km_excess) / 10_000 * Decimal("0.01"))
    value = max(value, base * Decimal("0.10"))
    return Decimal(int(round(value, -3)))


def book_test_drive(vehicle, customer, scheduled_at, notes=""):
    if not vehicle.is_available:
        raise ValueError("This car has already been sold.")
    if scheduled_at <= timezone.now():
        raise ValueError("Please choose a time in the future.")
    try:
        with transaction.atomic():
            return TestDrive.objects.create(vehicle=vehicle, customer=customer, scheduled_at=scheduled_at, notes=notes)
    except IntegrityError:
        raise ValueError("That slot was just taken. Please pick another time.")


def booked_slots(vehicle, date):
    return {
        timezone.localtime(td.scheduled_at).time()
        for td in vehicle.test_drives.exclude(status=TestDrive.Status.CANCELLED).filter(scheduled_at__date=date)
    }


TEST_DRIVE_MESSAGES = {
    "CONFIRMED": ("Your test drive of the {car} on {when} is confirmed", Notification.Kind.SUCCESS, "bi-calendar-check"),
    "CANCELLED": ("Your test drive of the {car} on {when} was cancelled", Notification.Kind.WARNING, "bi-calendar-x"),
    "COMPLETED": ("Thanks for test driving the {car}! Ready to make it yours?", Notification.Kind.INFO, "bi-car-front"),
}


def set_test_drive_status(test_drive, status, by_user):
    test_drive.status = status
    test_drive.handled_by = by_user
    test_drive.save(update_fields=["status", "handled_by"])
    template, kind, icon = TEST_DRIVE_MESSAGES[status]
    when = timezone.localtime(test_drive.scheduled_at).strftime("%d %b, %I:%M %p")
    notify(test_drive.customer, template.format(car=test_drive.vehicle.title, when=when),
           reverse("inventory:detail", args=[test_drive.vehicle_id]), kind, icon)


def make_trade_in_offer(trade_in, value):
    trade_in.offered_value = value
    trade_in.status = TradeInRequest.Status.OFFERED
    trade_in.save(update_fields=["offered_value", "status"])
    notify(trade_in.customer, f"We've made an offer of ₹{value:,.0f} for your {trade_in.vehicle_model}",
           reverse("inventory:my_trade_ins"), Notification.Kind.SUCCESS, "bi-tag")


RTO_CODES = ["MH12"] * 6 + ["MH14"] * 3 + ["MH01", "MH02", "MH04", "MH15", "DL01", "KA05", "GJ01", "HR26", "TS09"]


def random_reg_number():
    return f"{random.choice(RTO_CODES)}{''.join(random.choices(string.ascii_uppercase, k=2))}{random.randint(1000, 9999)}"


@transaction.atomic
def record_sale(vehicle, customer, salesperson, sale_price, trade_in=None, sold_at=None, notify_customer=True):
    from service.models import CustomerVehicle

    vehicle = Vehicle.objects.select_for_update().get(pk=vehicle.pk)
    if vehicle.status == Vehicle.Status.SOLD:
        raise ValueError("This vehicle is already sold.")
    sold_at = sold_at or timezone.now()
    sale = Sale.objects.create(
        vehicle=vehicle, customer=customer, salesperson=salesperson, sale_price=sale_price, trade_in=trade_in, sold_at=sold_at
    )
    vehicle.status = Vehicle.Status.SOLD
    vehicle.save(update_fields=["status"])
    if trade_in:
        trade_in.status = TradeInRequest.Status.ACCEPTED
        trade_in.save(update_fields=["status"])

    reg = vehicle.reg_number or random_reg_number()
    while not vehicle.reg_number and CustomerVehicle.objects.filter(reg_number=reg).exists():
        reg = random_reg_number()
    CustomerVehicle.objects.create(
        owner=customer, vehicle_model=vehicle.vehicle_model, year=vehicle.year, reg_number=reg,
        km_driven=vehicle.mileage_km, color_hex=vehicle.color_hex, purchased_vehicle=vehicle, created_at=sold_at,
    )
    if notify_customer:
        notify(customer, f"Congratulations on your new {vehicle.title}! It's been added to your garage.",
               reverse("service:garage"), Notification.Kind.SUCCESS, "bi-trophy")
    return sale


def monthly_emi(principal, annual_rate, months):
    principal = Decimal(principal)
    if principal <= 0:
        return Decimal("0")
    r = Decimal(str(annual_rate)) / 1200
    if not r:
        return principal / months
    f = (1 + r) ** months
    return principal * r * f / (f - 1)


UPGRADE_BANDS = [
    ("same", "Same EMI or less", "bi-check2-circle", 1000),
    ("step", "A small step up", "bi-arrow-up-right", 4000),
    ("stretch", "Worth the stretch", "bi-rocket-takeoff", 10000),
]


def upgrade_options(trade_value, outstanding, current_emi, extra_down, rate, months, exclude_model=None, current_year=0):
    """In-stock cars that are a real step up (much pricier, or clearly newer), priced as
    (price − equity − extra down payment) financed at rate/months, compared with today's EMI."""
    from django.db.models import Q

    equity = Decimal(trade_value) - Decimal(outstanding)
    bands = {key: [] for key, *_ in UPGRADE_BANDS}
    step_up = Q(price__gte=Decimal(trade_value) * Decimal("1.6")) | Q(year__gte=current_year + 2, price__gt=trade_value)
    stock = (Vehicle.objects.filter(step_up, status=Vehicle.Status.AVAILABLE)
             .select_related("vehicle_model__make"))
    if exclude_model:
        stock = stock.exclude(vehicle_model=exclude_model)
    for v in stock:
        loan = max(Decimal("0"), v.price - equity - Decimal(extra_down))
        emi = monthly_emi(loan, rate, months)
        delta = emi - Decimal(current_emi)
        for key, _, _, limit in UPGRADE_BANDS:
            if delta <= limit:
                bands[key].append({"v": v, "loan": loan, "emi": emi.quantize(Decimal("1")), "delta": delta.quantize(Decimal("1"))})
                break
    for key in bands:
        bands[key].sort(key=lambda o: o["v"].price, reverse=True)
        bands[key] = bands[key][:6]
    return equity, [(key, label, icon, bands[key]) for key, label, icon, _ in UPGRADE_BANDS]
