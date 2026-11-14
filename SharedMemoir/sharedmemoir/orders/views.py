from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from shop.bag import clear_bag, get_bag

from .forms import CheckoutForm
from .models import Order
from .services import OutOfStock, place_order


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