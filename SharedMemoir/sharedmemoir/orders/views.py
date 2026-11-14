from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from shop.bag import clear_bag, get_bag

from .forms import CheckoutForm, ReviewForm
from .models import Order
from .services import OutOfStock, cancel_and_refund, place_order


@login_required
def checkout(request):
    bag = get_bag(request)
    if bag is None:
        messages.info(request, "Your bag is empty. Choose a memory book first.")
        return redirect("shop")

    profile = getattr(request.user, "profile", None)
    initial = {
        "contact_name": profile.full_name if profile else request.user.username,
        "contact_email": request.user.email,
        "contact_phone": profile.phone if profile else "",
        "shipping_address": profile.address_line if profile else "",
        "shipping_postal_code": profile.postal_code if profile else "",
    }
    form = CheckoutForm(request.POST or None, initial=initial, is_print=bag["is_print"])

    if request.method == "POST" and form.is_valid():
        try:
            order = place_order(request.user, bag, form.cleaned_data)
        except OutOfStock:
            messages.error(request, "Sorry, that gift box has just sold out. Please choose another.")
            return redirect(reverse("configure", args=[bag["cover"].slug]) + "?edit=1")
        clear_bag(request)
        return redirect("order_success", pk=order.pk)

    return render(request, "orders/checkout.html", {"form": form, "bag": bag})


@login_required
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    return render(request, "orders/success.html", {"order": order})


@login_required
def my_orders(request):
    orders = request.user.orders.select_related("cover", "tier", "review")
    return render(request, "orders/my_orders.html", {"orders": orders})


@login_required
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    if not order.can_cancel:
        messages.error(request, f"{order.number} can no longer be cancelled.")
        return redirect("my_orders")

    if request.method == "POST":
        if cancel_and_refund(order, request.user):
            messages.success(request, f"{order.number} has been cancelled. "
                                      f"A full refund of S${order.amount:.2f} has been issued (demo).")
        else:
            messages.error(request, f"{order.number} can no longer be cancelled.")
        return redirect("my_orders")

    # GET: ask the customer to confirm first.
    return render(request, "orders/cancel_confirm.html", {"order": order})


@login_required
def review_order(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    if not order.can_review:
        messages.info(request, "You can review an order once it is completed, and only once.")
        return redirect("my_orders")

    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.order = order
        review.save()
        order.add_event(f"Customer left a {review.rating}-star review.", actor=request.user)
        messages.success(request, "Thank you for your review!")
        return redirect("my_orders")

    return render(request, "orders/review_form.html", {"form": form, "order": order})
