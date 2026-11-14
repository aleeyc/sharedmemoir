from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse

from orders.models import Order, Review
from orders.services import TransitionError, can_transition, deliver_pdf, transition
from shop.models import CoverStyle, GiftBox, PackageTier

from .decorators import staff_required
from .forms import CoverStyleForm, DeliverPdfForm, PackageTierForm, ShipForm, StockAdjustForm
    
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

@staff_required
def catalogue(request):
    return render(request, "staffpanel/catalogue.html", {
        "covers": CoverStyle.objects.select_related("occasion")
                  .annotate(order_count=Count("order")).order_by("name"),
        "tiers": PackageTier.objects.all(),
        "gift_boxes": GiftBox.objects.all(),
    })


@staff_required
def cover_form(request, pk=None):
    """Add a new cover style or edit an existing one."""
    cover = get_object_or_404(CoverStyle, pk=pk) if pk else None
    form = CoverStyleForm(request.POST or None, instance=cover)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"Cover style \"{saved.name}\" {'updated' if cover else 'added'}.")
        return redirect("staff_catalogue")
    return render(request, "staffpanel/cover_form.html", {"form": form, "cover": cover})


@staff_required
@require_POST
def cover_toggle(request, pk):
    cover = get_object_or_404(CoverStyle, pk=pk)
    cover.is_active = not cover.is_active
    cover.save(update_fields=["is_active"])
    state = "is now shown in the shop" if cover.is_active else "is now hidden from the shop"
    messages.success(request, f"\"{cover.name}\" {state}.")
    return redirect("staff_catalogue")


@staff_required
def tier_form(request, pk):
    tier = get_object_or_404(PackageTier, pk=pk)
    form = PackageTierForm(request.POST or None, instance=tier)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Package \"{tier.name}\" updated. Existing orders keep the price they paid.")
        return redirect(reverse("staff_catalogue") + "#packages")
    return render(request, "staffpanel/tier_form.html", {"form": form, "tier": tier})


@staff_required
@require_POST
def giftbox_stock(request, pk):
    box = get_object_or_404(GiftBox, pk=pk)
    form = StockAdjustForm(request.POST)
    if not form.is_valid():
        messages.error(request, f"{box}: enter whole numbers (change between −500 and 500, reorder level 0–500).")
        return redirect(reverse("staff_catalogue") + "#gift-boxes")

    change = form.cleaned_data["change"]
    updated = GiftBox.objects.filter(pk=pk, stock__gte=-change).update(
        stock=F("stock") + change,
        reorder_level=form.cleaned_data["reorder_level"],
    )
    if updated:
        box.refresh_from_db()
        messages.success(request, f"{box}: stock is now {box.stock}.")
    else:
        messages.error(request, f"{box} only has {box.stock} in stock, so you can't remove {-change}.")
    return redirect(reverse("staff_catalogue") + "#gift-boxes")

@staff_required
def customer_list(request):
    customers = (
        User.objects.filter(is_staff=False)
        .select_related("profile")
        .annotate(
            order_count=Count("orders"),
            total_spent=Sum("orders__amount", filter=~Q(orders__status=Order.Status.CANCELLED)),
        )
        .order_by("-date_joined")
    )

    selected = request.GET.get("status", "")
    if selected == "active":
        customers = customers.filter(is_active=True)
    elif selected == "inactive":
        customers = customers.filter(is_active=False)

    query = request.GET.get("q", "").strip()
    if query:
        customers = customers.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
            | Q(profile__full_name__icontains=query) | Q(profile__phone__icontains=query)
        )

    page = Paginator(customers, 20).get_page(request.GET.get("page"))
    return render(request, "staffpanel/customer_list.html", {
        "page": page, "selected_status": selected, "query": query,
    })


@staff_required
def customer_detail(request, pk):
    customer = get_object_or_404(User.objects.select_related("profile"), pk=pk, is_staff=False)
    orders = customer.orders.select_related("cover", "tier").order_by("-created_at")
    total_spent = orders.exclude(status=Order.Status.CANCELLED).aggregate(total=Sum("amount"))["total"] or 0
    return render(request, "staffpanel/customer_detail.html", {
        "customer": customer,
        "profile": getattr(customer, "profile", None),
        "orders": orders,
        "total_spent": total_spent,
        "reviews": Review.objects.filter(order__customer=customer).select_related("order", "order__cover"),
    })


@staff_required
@require_POST
def customer_toggle_active(request, pk):
    customer = get_object_or_404(User, pk=pk, is_staff=False)
    customer.is_active = not customer.is_active
    customer.save(update_fields=["is_active"])
    if customer.is_active:
        messages.success(request, f"{customer.username}'s account has been reactivated.")
    else:
        messages.success(request, f"{customer.username}'s account has been deactivated. They can no longer log in; their orders are kept.")
    return redirect("staff_customer_detail", pk=pk)


@staff_required
def review_list(request):
    reviews = Review.objects.select_related("order", "order__cover", "order__customer")
    selected = request.GET.get("status", "")
    if selected == "visible":
        reviews = reviews.filter(is_hidden=False)
    elif selected == "hidden":
        reviews = reviews.filter(is_hidden=True)
    page = Paginator(reviews, 20).get_page(request.GET.get("page"))
    return render(request, "staffpanel/review_list.html", {"page": page, "selected_status": selected})


@staff_required
@require_POST
def review_toggle(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.is_hidden = not review.is_hidden
    review.save(update_fields=["is_hidden"])
    state = "hidden from the shop" if review.is_hidden else "visible in the shop again"
    messages.success(request, f"Review for {review.order.number} is now {state}.")
    return redirect("staff_reviews")