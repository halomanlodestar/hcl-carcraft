"""History-adjusted valuation: turns a registry record into an itemised price waterfall and a trust score.

Every rule here is deliberately simple and explainable — each adjustment carries the reason shown to the customer.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from django.utils import timezone

from inventory.services import estimate_trade_in

OWNER_PENALTY = {1: Decimal("0"), 2: Decimal("0.03"), 3: Decimal("0.06")}
CLAIM_PENALTY = {"MINOR": Decimal("0.02"), "GLASS": Decimal("0.005"), "MAJOR": Decimal("0.06"), "FLOOD": Decimal("0.15")}
CLAIM_CAP = Decimal("0.25")


@dataclass
class Adjustment:
    label: str
    detail: str
    icon: str
    amount: Decimal  # signed rupees


@dataclass
class Flag:
    title: str
    text: str
    icon: str
    tone: str  # danger | warning | info | success


@dataclass
class Valuation:
    base: Decimal
    adjustments: list
    final: Decimal
    score: int
    flags: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    rollback: dict | None = None

    @property
    def grade(self):
        if self.score >= 85:
            return "A", "Excellent history", "success"
        if self.score >= 70:
            return "B", "Good history", "primary"
        if self.score >= 50:
            return "C", "Review the flags", "warning"
        return "D", "High risk", "danger"

    @property
    def total_adjustment(self):
        return self.final - self.base


def _pct(base, rate):
    return (base * rate).quantize(Decimal("1"))


def detect_rollback(readings):
    """First reading that is lower than the highest reading before it."""
    peak = None
    for r in readings:
        if peak and r.km < peak.km:
            return {"before": peak, "after": r, "drop": peak.km - r.km}
        if not peak or r.km > peak.km:
            peak = r
    return None


def value_record(record, km_driven=None, condition="GOOD", carcraft_services=0):
    readings = list(record.odometer.all())
    km = km_driven if km_driven is not None else (readings[-1].km if readings else 0)
    base = estimate_trade_in(record.vehicle_model, record.manufacture_year, km, condition)
    adjustments, flags = [], []
    score = 100

    # 1. Number of owners
    owners = record.ownerships.count()
    rate = OWNER_PENALTY.get(owners, Decimal("0.10"))
    if owners > 1:
        adjustments.append(Adjustment(f"{owners}{'nd' if owners == 2 else 'rd' if owners == 3 else 'th'} owner",
                                      f"Each change of hands lowers resale value; {owners} registered owners so far.",
                                      "bi-people", -_pct(base, rate)))
        score -= 5 * (owners - 1)

    # 2. Interstate move: re-registration and NOC paperwork
    if record.ownerships.filter(event="INTERSTATE").exists():
        adjustments.append(Adjustment("Interstate history", "Moved between states; needs an NOC trail to be complete.",
                                      "bi-signpost-split", -_pct(base, Decimal("0.01"))))
        score -= 3

    # 3. Driving behaviour from challans
    challans = list(record.challans.all())
    wear = [c for c in challans if c.affects_wear]
    n = len(wear)
    if n == 0:
        adjustments.append(Adjustment("Clean driving record", "No overspeeding, red-light or dangerous-driving challans.",
                                      "bi-hand-thumbs-up", _pct(base, Decimal("0.01"))))
    else:
        rate = Decimal("0.01") if n <= 2 else Decimal("0.03") if n <= 5 else Decimal("0.05")
        kinds = {}
        for c in wear:
            kinds[c.get_offence_display().lower()] = kinds.get(c.get_offence_display().lower(), 0) + 1
        detail = ", ".join(f"{v}× {k}" for k, v in kinds.items())
        adjustments.append(Adjustment(f"{n} hard-driving challan{'s' if n > 1 else ''}",
                                      f"{detail}. Suggests harder use of brakes, clutch and suspension.",
                                      "bi-speedometer", -_pct(base, rate)))
        score -= min(25, 4 * n)

    # 4. Unpaid challans travel with the car
    unpaid = [c for c in challans if c.is_unpaid]
    if unpaid:
        dues = sum((c.amount for c in unpaid), Decimal("0"))
        adjustments.append(Adjustment(f"Pending challans ({len(unpaid)})",
                                      "Deducted rupee-for-rupee; we clear them before the RC transfer.",
                                      "bi-receipt-cutoff", -dues))
        flags.append(Flag("Unpaid challans", f"₹{dues:,.0f} in pending fines must be cleared before the RC can be transferred.",
                          "bi-receipt-cutoff", "warning"))
        score -= 5

    # 5. Insurance claims
    claims = list(record.claims.all())
    if claims:
        rate = min(CLAIM_CAP, sum((CLAIM_PENALTY[c.kind] for c in claims), Decimal("0")))
        major = sum(1 for c in claims if c.kind == "MAJOR")
        flood = sum(1 for c in claims if c.kind == "FLOOD")
        adjustments.append(Adjustment(f"{len(claims)} insurance claim{'s' if len(claims) > 1 else ''}",
                                      ", ".join(c.get_kind_display().lower() for c in claims).capitalize() + ".",
                                      "bi-shield-exclamation", -_pct(base, rate)))
        score -= 4 * (len(claims) - major - flood) + 12 * major + 30 * flood
        if any(c.kind == "FLOOD" for c in claims):
            flags.append(Flag("Flood damage on record", "Water damage often surfaces later as electrical faults. Insist on a full electrical inspection.",
                              "bi-water", "danger"))

    # 6. Odometer consistency
    rollback = detect_rollback(readings)
    if rollback:
        adjustments.append(Adjustment("Odometer inconsistency",
                                      f"Reading fell by {rollback['drop']:,} km between {rollback['before'].read_on:%b %Y} and {rollback['after'].read_on:%b %Y}.",
                                      "bi-speedometer2", -_pct(base, Decimal("0.08"))))
        flags.append(Flag("Possible odometer rollback",
                          f"Recorded {rollback['before'].km:,} km in {rollback['before'].read_on:%b %Y}, then {rollback['after'].km:,} km in {rollback['after'].read_on:%b %Y}.",
                          "bi-speedometer2", "danger"))
        score -= 45

    # 7. Our own service records
    if carcraft_services >= 2:
        adjustments.append(Adjustment("Serviced at CarCraft", f"{carcraft_services} documented services in our workshop.",
                                      "bi-patch-check", _pct(base, Decimal("0.02"))))
        score += 3

    # Informational flags (no price impact)
    if record.hypothecated_to:
        flags.append(Flag("Active car loan", f"Hypothecated to {record.hypothecated_to}. The lender's NOC is needed before sale.",
                          "bi-bank", "info"))
    if not record.insurance_active:
        flags.append(Flag("Insurance expired", f"Lapsed on {record.insurance_valid_till:%d %b %Y}.", "bi-shield-x", "warning"))
        score -= 5
    if not flags:
        flags.append(Flag("No red flags", "Registry, challan and claim records are all clear.", "bi-shield-check", "success"))

    raw = max(base + sum((a.amount for a in adjustments), Decimal("0")), base * Decimal("0.4"))
    final = (raw / 1000).quantize(Decimal("1")) * 1000
    v = Valuation(base=base, adjustments=adjustments, final=final, score=max(5, min(100, score)), flags=flags, rollback=rollback)
    v.steps = _waterfall(v)
    return v


def _waterfall(v):
    """Positions (in %) for a horizontal waterfall: base bar, one floating bar per adjustment, final bar."""
    running = [v.base]
    for a in v.adjustments:
        running.append(running[-1] + a.amount)
    lo = min(running + [v.final]) * Decimal("0.85")
    hi = max(running + [v.final])
    span = (hi - lo) or Decimal("1")

    def pos(x):
        return float((x - lo) / span * 100)

    steps = [{"label": "Base value", "detail": "Age, kilometres and condition", "icon": "bi-calculator",
              "amount": v.base, "left": 0, "width": pos(v.base), "kind": "total"}]
    for i, a in enumerate(v.adjustments):
        start, end = running[i], running[i + 1]
        steps.append({"label": a.label, "detail": a.detail, "icon": a.icon, "amount": a.amount,
                      "left": pos(min(start, end)), "width": max(abs(pos(end) - pos(start)), 0.8),
                      "kind": "up" if a.amount > 0 else "down"})
    steps.append({"label": "History-adjusted value", "detail": "Rounded to the nearest ₹1,000", "icon": "bi-check2-circle",
                  "amount": v.final, "left": 0, "width": pos(v.final), "kind": "final"})
    return steps


def carcraft_service_count(reg_number):
    from service.models import ServiceJob

    return ServiceJob.objects.filter(customer_vehicle__reg_number=reg_number, status="DELIVERED").count()


def passport_for(reg_number, km_driven=None, condition="GOOD"):
    from .models import RegistryRecord

    record = (RegistryRecord.objects.select_related("vehicle_model__make")
              .prefetch_related("ownerships", "challans", "claims", "odometer")
              .filter(reg_number=reg_number.upper().replace(" ", "")).first())
    if not record:
        return None, None
    return record, value_record(record, km_driven, condition, carcraft_service_count(record.reg_number))


def age_years(record):
    return max(0, timezone.localdate().year - record.manufacture_year)
