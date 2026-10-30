from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from inventory.models import TradeInRequest, Vehicle
from service.models import CustomerVehicle

from core.seed_data.history import STORY_REGS

from .models import RegistryRecord
from .valuation import passport_for

# Registrations that tell a good story in a demo; shown as one-tap chips on the search page
SAMPLE_STORIES = [
    ("clean", "bi-shield-check", "Clean, one owner"),
    ("challans", "bi-speedometer", "Heavy challans"),
    ("rollback", "bi-speedometer2", "Odometer rollback"),
    ("flood", "bi-water", "Flood claim"),
]


PAINT_BY_NAME = {"white": "#f4f4f2", "black": "#17191e", "silver": "#b9bdc3", "grey": "#5d636b", "red": "#c3282f",
                 "blue": "#1f4fa3", "green": "#2f5d46", "bronze": "#8a6a4a", "orange": "#d9622b"}


def _paint_for(color_name):
    name = (color_name or "").lower()
    return next((hexv for key, hexv in PAINT_BY_NAME.items() if key in name), "#9ca3af")


def check(request):
    reg = request.GET.get("reg", "").upper().replace(" ", "").replace("-", "")
    if reg:
        if RegistryRecord.objects.filter(reg_number=reg).exists():
            return redirect("passport:detail", reg=reg)
        messages.error(request, f"No registry record found for {reg}. Try one of the sample registrations.")
    samples = []
    for story, icon, label in SAMPLE_STORIES:
        rec = RegistryRecord.objects.filter(reg_number=STORY_REGS[story]).select_related("vehicle_model__make").first()
        if rec:
            samples.append((rec, icon, label))
    return render(request, "passport/check.html", {"samples": samples, "reg": reg})


def detail(request, reg):
    km = request.GET.get("km")
    condition = request.GET.get("condition", "GOOD")
    if condition not in ("EXCELLENT", "GOOD", "FAIR", "POOR"):
        condition = "GOOD"
    record, valuation = passport_for(reg, int(km) if km and km.isdigit() else None, condition)
    if not record:
        return get_object_or_404(RegistryRecord, reg_number=reg)

    readings = list(record.odometer.all())
    rollback_idx = readings.index(valuation.rollback["after"]) if valuation.rollback else None
    challans = list(record.challans.all())
    listing = Vehicle.objects.filter(reg_number=record.reg_number).exclude(status="SOLD").first()
    mine = None
    if request.user.is_authenticated and request.user.is_customer:
        mine = CustomerVehicle.objects.filter(owner=request.user, reg_number=record.reg_number).first()
    return render(request, "passport/detail.html", {
        "record": record, "v": valuation, "listing": listing, "mine": mine,
        "paint": (listing or mine).color_hex if (listing or mine) else _paint_for(record.color),
        "ownerships": record.ownerships.all(),
        "challans": challans,
        "wear_count": sum(1 for c in challans if c.affects_wear),
        "unpaid_total": sum((c.amount for c in challans if c.is_unpaid), 0),
        "claims": record.claims.all(),
        "readings": readings,
        "odo_chart": {
            "labels": [r.read_on.strftime("%b %Y") for r in readings],
            "km": [r.km for r in readings],
            "sources": [r.get_source_display() for r in readings],
            "flag": rollback_idx,
        },
        "condition": condition,
        "conditions": TradeInRequest.ConditionRating.choices,
    })
