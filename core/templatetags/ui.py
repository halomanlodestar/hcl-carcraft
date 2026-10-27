from decimal import Decimal, InvalidOperation

from django import template
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()


def _indian_group(int_str):
    if len(int_str) <= 3:
        return int_str
    head, tail = int_str[:-3], int_str[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


@register.filter
def inr(value, decimals=0):
    """₹12,34,567 — Indian digit grouping."""
    try:
        value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    negative = value < 0
    value = abs(value).quantize(Decimal(1) if not int(decimals) else Decimal("0.01"))
    int_part, _, frac = f"{value}".partition(".")
    out = "₹" + _indian_group(int_part) + (f".{frac}" if frac else "")
    return f"-{out}" if negative else out


@register.filter
def lakh(value):
    """₹12.45 L / ₹1.2 Cr — compact price for cards."""
    try:
        value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    if value >= 10_000_000:
        return f"₹{value / 10_000_000:.2f} Cr"
    if value >= 100_000:
        return f"₹{value / 100_000:.2f} L"
    return inr(value)


@register.filter
def km(value):
    try:
        return _indian_group(str(int(value))) + " km"
    except (TypeError, ValueError):
        return value


STATUS_STYLES = {
    # vehicles
    "AVAILABLE": "success", "RESERVED": "warning", "SOLD": "secondary",
    # test drives
    "REQUESTED": "warning", "CONFIRMED": "primary", "COMPLETED": "success",
    # trade-ins
    "PENDING": "warning", "OFFERED": "primary", "ACCEPTED": "success", "REJECTED": "danger",
    # orders
    "PAID": "primary", "SHIPPED": "info", "DELIVERED": "success",
    # service jobs
    "BOOKED": "secondary", "INSPECTION": "info", "IN_PROGRESS": "primary", "READY": "success",
    "CANCELLED": "danger",
}

STATUS_ICONS = {
    "AVAILABLE": "bi-check-circle", "RESERVED": "bi-bookmark", "SOLD": "bi-bag-check",
    "REQUESTED": "bi-hourglass-split", "CONFIRMED": "bi-calendar-check", "COMPLETED": "bi-check2-all",
    "PENDING": "bi-hourglass-split", "OFFERED": "bi-tag", "ACCEPTED": "bi-hand-thumbs-up", "REJECTED": "bi-x-circle",
    "PAID": "bi-credit-card", "SHIPPED": "bi-truck", "DELIVERED": "bi-box2-heart",
    "BOOKED": "bi-calendar-check", "INSPECTION": "bi-search", "IN_PROGRESS": "bi-wrench-adjustable",
    "READY": "bi-check2-circle", "CANCELLED": "bi-x-circle",
}


@register.simple_tag
def status_badge(code, label=None):
    style = STATUS_STYLES.get(code, "secondary")
    icon = STATUS_ICONS.get(code, "bi-dot")
    label = label or code.replace("_", " ").title()
    return format_html(
        '<span class="badge-status badge-status-{}"><i class="bi {}"></i>{}</span>', style, icon, label
    )


@register.simple_tag
def brand_logo(make, size="md", extra=""):
    """Brand mark rendered via CSS mask so it inherits the text colour (works in dark mode)."""
    if not make or not getattr(make, "logo", ""):
        return format_html('<span class="brand-fallback brand-{}">{}</span>', size, getattr(make, "name", "")[:1])
    url = static(f"brands/{make.logo}.svg")
    wide = "brand-wide" if make.logo in WORDMARK_LOGOS else ""
    return format_html(
        '<span class="brand-logo brand-{} {} {}" style="--logo:url({})" role="img" aria-label="{}" title="{}"></span>',
        size, wide, extra, url, make.name, make.name,
    )


# Logos that are wordmarks rather than badges need a wider box to stay legible
WORDMARK_LOGOS = {"mahindra"}


FUEL_ICONS = {
    "PETROL": "bi-fuel-pump", "DIESEL": "bi-fuel-pump-diesel", "CNG": "bi-cloud-haze2",
    "EV": "bi-lightning-charge-fill", "HYBRID": "bi-recycle",
}


@register.filter
def fuel_icon(code):
    return FUEL_ICONS.get(code, "bi-fuel-pump")


@register.filter
def trans_icon(code):
    return "bi-gear-wide" if code == "MANUAL" else "bi-gear-wide-connected"


@register.inclusion_tag("partials/car_art.html")
def car_art(body_type, color="#9ca3af", size=""):
    return {"body": (body_type or "SEDAN").upper(), "color": color, "size": size}


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Keep current filters in the querystring while changing one (e.g. page)."""
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        if v in (None, ""):
            params.pop(k, None)
        else:
            params[k] = v
    return params.urlencode()


@register.filter
def initials(name):
    return "".join(p[0] for p in str(name).split()[:2]).upper()


@register.filter
def rs(value):
    """Rs. 12,34,567.00 — for PDFs, where the default fonts lack the ₹ glyph."""
    return inr(value, 2).replace("₹", "Rs. ")
