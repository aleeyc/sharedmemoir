from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Order
from orders.services import TransitionError, can_transition, deliver_pdf, transition
from shop.models import GiftBox

from .decorators import staff_required
from .forms import DeliverPdfForm, ShipForm
    
STUDIO_ACTION_STATUSES = [
    Order.Status.SUBMITTED,
    Order.Status.PRODUCING,
    Order.Status.REVISION,
    Order.Status.PRINTING,
]

# Studio view at different status points
WAITING_ON_CUSTOMER = {
    Order.Status.WAITING: "Waiting for the customer to upload and submit photos.",
    Order.Status.DELIVERED: "Waiting for the customer to approve the PDF or request their free revision.",
    Order.Status.SHIPPED: "Waiting for the customer to confirm they received the book.",
    Order.Status.COMPLETED: "This order is complete.",
    Order.Status.CANCELLED: "The customer cancelled this order and was refunded.",
}


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


def _order_context(order, user, deliver_form=None, ship_form=None):
    return {
        "order": order,
        "photos": order.photos.all(),
        "events": order.events.select_related("actor"),
        "versions": order.versions.select_related("uploaded_by"),
        "can_start": can_transition(order, "start", user),
        "can_deliver": can_transition(order, "deliver", user),
        "can_ship": can_transition(order, "ship", user),
        "deliver_form": deliver_form or DeliverPdfForm(),
        "ship_form": ship_form or ShipForm(),
        "waiting_message": WAITING_ON_CUSTOMER.get(order.status, ""),
    }


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("customer", "cover", "tier", "gift_box", "recommended_tier"),
        pk=pk,
    )
    return render(request, "staffpanel/order_detail.html", _order_context(order, request.user))


@staff_required
@require_POST
def order_start(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        transition(order, "start", request.user, "Studio started designing the memory book.")
    except TransitionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Production started for {order.number}.")
    return redirect("staff_order_detail", pk=pk)


@staff_required
@require_POST
def order_deliver(request, pk):
    order = get_object_or_404(Order, pk=pk)
    form = DeliverPdfForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            deliver_pdf(order, request.user, form.cleaned_data["pdf"], form.cleaned_data["note"])
        except TransitionError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"PDF delivered to the customer for {order.number}.")
        return redirect("staff_order_detail", pk=pk)
    return render(request, "staffpanel/order_detail.html",
                  _order_context(order, request.user, deliver_form=form))


@staff_required
@require_POST
def order_ship(request, pk):
    order = get_object_or_404(Order, pk=pk)
    form = ShipForm(request.POST)
    if form.is_valid():
        courier = form.cleaned_data["courier"]
        tracking = form.cleaned_data["tracking_number"]
        try:
            transition(order, "ship", request.user,
                       f"Shipped with {courier}, tracking number {tracking}.",
                       courier=courier, tracking_number=tracking)
        except TransitionError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"{order.number} marked as shipped.")
        return redirect("staff_order_detail", pk=pk)
    return render(request, "staffpanel/order_detail.html",
                  _order_context(order, request.user, ship_form=form))