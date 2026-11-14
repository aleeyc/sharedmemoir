from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, render

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

@staff_required
def order_list(request):
    orders = (
        Order.objects.select_related("customer", "cover", "tier")
        .annotate(photo_count=Count("photos"))
        .order_by("-created_at")
    )

    # Filter by status
    selected_status = request.GET.get("status", "")
    if selected_status == "action":
        orders = orders.filter(status__in=STUDIO_ACTION_STATUSES)
    elif selected_status:
        orders = orders.filter(status=selected_status)

    # Search by order number, title, customer username, name or email
    query = request.GET.get("q", "").strip()
    if query:
        search = (Q(title__icontains=query)
                  | Q(customer__username__icontains=query)
                  | Q(contact_name__icontains=query)
                  | Q(contact_email__icontains=query))
        number = query.upper().removeprefix("MEM-")
        if number.isdigit():
            search |= Q(pk=int(number))
        orders = orders.filter(search)

    page = Paginator(orders, 15).get_page(request.GET.get("page"))
    return render(request, "staffpanel/order_list.html", {
        "page": page,
        "statuses": Order.Status.choices,
        "selected_status": selected_status,
        "query": query,
    })


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("customer", "cover", "tier", "gift_box", "recommended_tier"),
        pk=pk,
    )
    return render(request, "staffpanel/order_detail.html", {
        "order": order,
        "photos": order.photos.all(),
        "events": order.events.select_related("actor"),
    })