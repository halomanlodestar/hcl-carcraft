from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.mixins import role_required
from core.pdf import render_pdf
from inventory.models import Make, VehicleModel

from . import services
from .models import CartItem, Order, Part, PartCategory

CATEGORY_TINTS = {
    "engine-oil": "#f79009", "brakes": "#e0313b", "filters": "#12b76a", "electrical": "#2e90fa",
    "tyres-wheels": "#475467", "body-exterior": "#7a5af8", "interior": "#ee46bc", "car-care": "#0ba5ec",
}

SORTS = {"popular": ("Most popular", "name"), "price_asc": ("Price: low to high", "price"),
         "price_desc": ("Price: high to low", "-price"), "name": ("Name A–Z", "name")}


def _garage_models(user):
    if user.is_authenticated and user.is_customer:
        return [cv.vehicle_model for cv in user.garage.select_related("vehicle_model__make")]
    return []


def part_list(request):
    g = request.GET
    qs = Part.objects.select_related("category").prefetch_related("compatible_models")
    q = g.get("q", "").strip()
    category = g.get("category", "")
    model_id = g.get("model", "")
    make_slug = g.get("make", "")
    in_stock = g.get("in_stock") == "1"
    sort = g.get("sort") if g.get("sort") in SORTS else "popular"

    if q:
        vector = SearchVector("name", weight="A") + SearchVector("brand", weight="B") + SearchVector("description", weight="C")
        qs = qs.annotate(search=vector).filter(Q(search=SearchQuery(q, search_type="websearch")) | Q(name__icontains=q) | Q(sku__iexact=q))
    if category:
        qs = qs.filter(category__slug=category)
    fit_model = None
    if model_id.isdigit():
        fit_model = VehicleModel.objects.select_related("make").filter(pk=model_id).first()
        if fit_model:
            qs = qs.filter(Q(compatible_models=fit_model) | Q(is_universal=True)).distinct()
    if in_stock:
        qs = qs.filter(stock_qty__gt=0)
    if sort == "popular":
        qs = qs.annotate(sold=Count("orderitem")).order_by("-sold", "name")
    else:
        qs = qs.order_by(SORTS[sort][1])

    page = Paginator(qs, 16).get_page(g.get("page"))
    selected_make = Make.objects.filter(slug=make_slug).first() or (fit_model.make if fit_model else None)
    return render(request, "store/part_list.html", {
        "page": page,
        "categories": PartCategory.objects.annotate(n=Count("parts")),
        "tints": CATEGORY_TINTS,
        "makes": Make.objects.all(),
        "selected_make": selected_make,
        "make_models": selected_make.models.all() if selected_make else [],
        "fit_model": fit_model,
        "garage_models": _garage_models(request.user),
        "sel": {"q": q, "category": category, "in_stock": in_stock, "sort": sort},
        "sorts": [(k, v[0]) for k, v in SORTS.items()],
    })


def api_models(request):
    make = get_object_or_404(Make, slug=request.GET.get("make", ""))
    return JsonResponse({"models": [{"id": m.pk, "name": m.name} for m in make.models.all()]})


def part_detail(request, sku):
    part = get_object_or_404(Part.objects.select_related("category"), sku=sku)
    models_by_make = {}
    for m in part.compatible_models.select_related("make"):
        models_by_make.setdefault(m.make, []).append(m)
    garage = _garage_models(request.user)
    fits_mine = [m for m in garage if part.is_universal or m in part.compatible_models.all()]
    related = Part.objects.filter(category=part.category).exclude(pk=part.pk).order_by("?")[:4]
    return render(request, "store/part_detail.html", {
        "part": part, "models_by_make": models_by_make, "fits_mine": fits_mine, "garage": garage,
        "related": related, "tints": CATEGORY_TINTS,
    })


@role_required("CUSTOMER")
@require_POST
def cart_add(request, pk):
    part = get_object_or_404(Part, pk=pk)
    if not part.in_stock:
        messages.error(request, f"{part.name} is out of stock.")
    else:
        qty = max(1, int(request.POST.get("qty", 1) or 1))
        services.add_to_cart(request.user, part, qty)
        messages.success(request, f"Added {part.name} to your cart.")
    return redirect(request.POST.get("next") or reverse("store:cart"))


@role_required("CUSTOMER")
@require_POST
def cart_update(request, pk):
    item = get_object_or_404(CartItem, pk=pk, user=request.user)
    action = request.POST.get("action")
    if action == "inc":
        item.quantity = min(item.quantity + 1, item.part.stock_qty)
    elif action == "dec":
        item.quantity -= 1
    if action == "remove" or item.quantity <= 0:
        item.delete()
    else:
        item.save()
    return redirect("store:cart")


@role_required("CUSTOMER")
def cart(request):
    coupon, coupon_error = None, None
    code = request.session.get("coupon", "")
    items, totals = services.cart_summary(request.user)
    if code:
        try:
            coupon = services.validate_coupon(code, totals["subtotal"])
        except services.CouponError as e:
            coupon_error = str(e)
            request.session.pop("coupon", None)
        totals = services.compute_totals(totals["subtotal"], coupon)
    suggestions = Part.objects.filter(is_universal=True, stock_qty__gt=0).exclude(
        pk__in=[i.part_id for i in items]).order_by("?")[:4]
    return render(request, "store/cart.html", {
        "items": items, "totals": totals, "coupon": coupon, "coupon_error": coupon_error,
        "suggestions": suggestions, "tints": CATEGORY_TINTS,
    })


@role_required("CUSTOMER")
@require_POST
def apply_coupon(request):
    code = request.POST.get("code", "").strip().upper()
    if request.POST.get("remove"):
        request.session.pop("coupon", None)
        return redirect("store:cart")
    _, totals = services.cart_summary(request.user)
    try:
        coupon = services.validate_coupon(code, totals["subtotal"])
    except services.CouponError as e:
        messages.error(request, str(e))
    else:
        if coupon:
            request.session["coupon"] = coupon.code
            messages.success(request, f"Coupon {coupon.code} applied. You save {services.coupon_discount(coupon, totals['subtotal']):,.0f} rupees!")
    return redirect("store:cart")


@role_required("CUSTOMER")
def checkout(request):
    items, totals = services.cart_summary(request.user)
    if not items:
        return redirect("store:cart")
    code = request.session.get("coupon", "")
    coupon = None
    try:
        coupon = services.validate_coupon(code, totals["subtotal"])
    except services.CouponError:
        request.session.pop("coupon", None)
    totals = services.compute_totals(totals["subtotal"], coupon)

    if request.method == "POST":
        address = request.POST.get("address", "").strip()
        if not address:
            messages.error(request, "Please enter a delivery address.")
        else:
            try:
                order = services.place_order(request.user, address, coupon.code if coupon else "")
            except services.InsufficientStock as e:
                messages.error(request, str(e))
                return redirect("store:cart")
            except (services.CouponError, ValueError) as e:
                messages.error(request, str(e))
                return redirect("store:cart")
            request.session.pop("coupon", None)
            return redirect("store:pay", pk=order.pk)
    default_address = ", ".join(x for x in [request.user.address, request.user.city] if x)
    return render(request, "store/checkout.html", {"items": items, "totals": totals, "coupon": coupon,
                                                   "default_address": default_address})


@role_required("CUSTOMER")
def pay(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    if order.status != Order.Status.PENDING:
        return redirect("store:order_detail", pk=order.pk)
    if request.method == "POST":
        services.mark_paid(order)
        messages.success(request, f"Payment successful! Order {order.number} is confirmed.")
        return redirect("store:order_detail", pk=order.pk)
    return render(request, "store/pay.html", {"order": order})


@login_required
def order_list(request):
    if request.user.is_admin_role:
        return redirect("store:manage_orders")
    orders = request.user.orders.prefetch_related("items__part__category")
    return render(request, "store/order_list.html", {"orders": orders, "tints": CATEGORY_TINTS})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("customer", "coupon").prefetch_related("items__part__category"), pk=pk)
    if not (request.user.is_admin_role or order.customer_id == request.user.pk):
        return redirect("store:orders")
    steps = [("PAID", "Paid", "bi-credit-card", order.paid_at), ("SHIPPED", "Shipped", "bi-truck", order.shipped_at),
             ("DELIVERED", "Delivered", "bi-box2-heart", order.delivered_at)]
    flow = ["PENDING", "PAID", "SHIPPED", "DELIVERED"]
    current = flow.index(order.status) if order.status in flow else -1
    return render(request, "store/order_detail.html", {
        "order": order, "steps": steps, "current": current, "tints": CATEGORY_TINTS,
        "progress": max(0, (current - 1)) * 40,
    })


@login_required
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if not (request.user.is_admin_role or order.customer_id == request.user.pk):
        return redirect("store:orders")
    try:
        services.cancel_order(order)
        messages.info(request, f"Order {order.number} cancelled and items returned to stock.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect("store:order_detail", pk=pk)


@login_required
def order_invoice(request, pk):
    order = get_object_or_404(Order.objects.select_related("customer", "coupon").prefetch_related("items__part"), pk=pk)
    if not (request.user.is_admin_role or order.customer_id == request.user.pk):
        return redirect("store:orders")
    return render_pdf("invoices/order.html", {"order": order}, f"carcraft-{order.number}.pdf")


@role_required("ADMIN")
def manage_orders(request):
    tab = request.GET.get("tab", "PAID")
    base = Order.objects.select_related("customer")
    counts = dict(base.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    tabs = [(code, label, counts.get(code, 0)) for code, label in Order.Status.choices]
    page = Paginator(base.filter(status=tab).annotate(n_items=Count("items")).order_by("-created_at"), 25).get_page(request.GET.get("page"))
    return render(request, "store/manage_orders.html", {"page": page, "tabs": tabs, "tab": tab})


@role_required("ADMIN")
@require_POST
def order_advance(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        services.advance_order(order)
        messages.success(request, f"Order {order.number} marked {order.get_status_display().lower()}.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect(request.POST.get("next") or reverse("store:manage_orders"))
