from django.contrib.auth.models import User
from django.db.models import Count, F, Sum
from django.shortcuts import render

from orders.models import Order
from shop.models import GiftBox

from .decorators import staff_required
    
STUDIO_ACTION_STATUSES = [
    Order.Status.SUBMITTED,
    Order.Status.PRODUCING,
    Order.Status.REVISION,
    Order.Status.PRINTING,
]


@staff_required
def dashboard(request):
    orders = Order.objects.all()
    paid_orders = orders.exclude(status=Order.Status.CANCELLED)

    counts = {
        row["status"]: row["total"]
        for row in orders.order_by().values("status").annotate(total=Count("id"))
    }
    status_rows = [(label, counts.get(value, 0)) for value, label in Order.Status.choices]

    # How often customers bought the package the model recommended
    with_recommendation = paid_orders.filter(recommended_tier__isnull=False)
    recommended_total = with_recommendation.count()
    followed = with_recommendation.filter(tier=F("recommended_tier")).count()
    follow_rate = round(100 * followed / recommended_total) if recommended_total else None

    return render(request, "staffpanel/dashboard.html", {
        "revenue": paid_orders.aggregate(total=Sum("amount"))["total"] or 0,
        "order_total": orders.count(),
        "needs_action": orders.filter(status__in=STUDIO_ACTION_STATUSES).count(),
        "customer_total": User.objects.filter(is_staff=False).count(),
        "status_rows": status_rows,
        "low_stock": GiftBox.objects.filter(stock__lte=F("reorder_level")),
        "follow_rate": follow_rate,
        "followed": followed,
        "recommended_total": recommended_total,
        "recent_orders": orders.select_related("customer", "cover", "tier")[:5],
    })