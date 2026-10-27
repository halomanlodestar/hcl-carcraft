def globals(request):
    compare_ids = request.session.get("compare", [])
    ctx = {"compare_count": len(compare_ids), "compare_ids": compare_ids}
    user = request.user
    if user.is_authenticated:
        ctx["unread_notifications"] = user.notifications.filter(is_read=False).count()
        ctx["recent_notifications"] = user.notifications.all()[:5]
        if user.is_customer:
            from django.db.models import Sum

            ctx["cart_count"] = user.cart_items.aggregate(n=Sum("quantity"))["n"] or 0
    return ctx
