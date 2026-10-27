from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

from core.models import Notification, notify

from .models import CartItem, Coupon, Order, OrderItem, Part


class InsufficientStock(Exception):
    def __init__(self, part, available):
        self.part = part
        self.available = available
        super().__init__(f"Only {available} × {part.name} left in stock")


class CouponError(Exception):
    pass


def _money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def adjust_stock(part, delta):
    """The only place stock_qty changes. Negative delta deducts; raises if it would go below zero."""
    part = Part.objects.select_for_update().get(pk=part.pk)
    if part.stock_qty + delta < 0:
        raise InsufficientStock(part, part.stock_qty)
    Part.objects.filter(pk=part.pk).update(stock_qty=F("stock_qty") + delta)
    part.refresh_from_db(fields=["stock_qty"])
    return part


def validate_coupon(code, subtotal):
    code = (code or "").strip().upper()
    if not code:
        return None
    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        raise CouponError(f"“{code}” isn't a valid coupon code.")
    now = timezone.now()
    if not coupon.is_active or now > coupon.valid_to:
        raise CouponError(f"“{code}” has expired.")
    if now < coupon.valid_from:
        raise CouponError(f"“{code}” isn't active yet.")
    if subtotal < coupon.min_order:
        raise CouponError(f"“{code}” needs a minimum order of ₹{coupon.min_order:,.0f}.")
    return coupon


def coupon_discount(coupon, subtotal):
    if not coupon:
        return Decimal("0")
    if coupon.discount_type == Coupon.DiscountType.PERCENT:
        amount = subtotal * coupon.value / 100
        if coupon.max_discount:
            amount = min(amount, coupon.max_discount)
    else:
        amount = coupon.value
    return _money(min(amount, subtotal))


def compute_totals(subtotal, coupon=None):
    subtotal = _money(subtotal)
    discount = coupon_discount(coupon, subtotal)
    tax = _money((subtotal - discount) * settings.GST_RATE / 100)
    return {"subtotal": subtotal, "discount": discount, "tax": tax, "total": subtotal - discount + tax}


def cart_summary(user, coupon=None):
    items = list(CartItem.objects.filter(user=user).select_related("part__category"))
    subtotal = sum((i.line_total for i in items), Decimal("0"))
    return items, compute_totals(subtotal, coupon)


def add_to_cart(user, part, quantity=1):
    item, created = CartItem.objects.get_or_create(user=user, part=part, defaults={"quantity": 0})
    item.quantity = min(item.quantity + quantity, part.stock_qty)
    item.save()
    return item


@transaction.atomic
def place_order(user, shipping_address, coupon_code=""):
    items, totals = cart_summary(user)
    if not items:
        raise ValueError("Your cart is empty.")
    coupon = validate_coupon(coupon_code, totals["subtotal"])
    totals = compute_totals(totals["subtotal"], coupon)

    order = Order.objects.create(customer=user, coupon=coupon, shipping_address=shipping_address, **totals)
    for item in items:
        adjust_stock(item.part, -item.quantity)
        OrderItem.objects.create(order=order, part=item.part, quantity=item.quantity, unit_price=item.part.price)
    CartItem.objects.filter(user=user).delete()
    return order


def mark_paid(order):
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at"])
    notify(order.customer, f"Payment received for order {order.number}", reverse("store:order_detail", args=[order.pk]),
           Notification.Kind.SUCCESS, "bi-credit-card")


ORDER_FLOW = {"PAID": "SHIPPED", "SHIPPED": "DELIVERED"}


@transaction.atomic
def advance_order(order):
    nxt = ORDER_FLOW.get(order.status)
    if not nxt:
        raise ValueError("This order can't move forward.")
    order.status = nxt
    stamp = "shipped_at" if nxt == "SHIPPED" else "delivered_at"
    setattr(order, stamp, timezone.now())
    order.save(update_fields=["status", stamp])
    icon = "bi-truck" if nxt == "SHIPPED" else "bi-box2-heart"
    notify(order.customer, f"Order {order.number} is {order.get_status_display().lower()}",
           reverse("store:order_detail", args=[order.pk]), Notification.Kind.INFO, icon)
    return order


@transaction.atomic
def cancel_order(order):
    if order.status not in (Order.Status.PENDING, Order.Status.PAID):
        raise ValueError("Only unshipped orders can be cancelled.")
    for item in order.items.select_related("part"):
        adjust_stock(item.part, item.quantity)
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status"])
