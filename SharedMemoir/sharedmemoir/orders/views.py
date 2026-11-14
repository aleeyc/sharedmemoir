from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from shop.bag import clear_bag, get_bag

from .forms import CheckoutForm, PhotoUploadForm, RevisionRequestForm, ReviewForm
from .models import Order, OrderPhoto
from .services import (OutOfStock, TransitionError, can_transition, cancel_and_refund, place_order, transition)


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
    orders = (
        request.user.orders.select_related("cover", "tier", "review")
        .annotate(photo_count=Count("photos"))
        .order_by("-created_at")  # Django ignores the model's default ordering once we annotate
    )
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


@login_required
def order_photos(request, pk):
    """Upload photos (while the order is waiting for them) or view the submitted photos."""
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    if order.status == Order.Status.CANCELLED:
        messages.info(request, f"{order.number} was cancelled.")
        return redirect("my_orders")

    form = PhotoUploadForm(order=order)
    if request.method == "POST":
        if not order.can_edit_photos:
            messages.error(request, "Your photos have already been submitted.")
            return redirect("order_photos", pk=order.pk)

        form = PhotoUploadForm(request.POST, request.FILES, order=order)
        if form.is_valid():
            images = form.cleaned_data["images"]
            for image in images:
                order.photos.create(image=image)
            messages.success(request, f"{len(images)} photo{'s' if len(images) > 1 else ''} uploaded.")
            return redirect("order_photos", pk=order.pk)

    photos = list(order.photos.all())
    tier = order.tier
    return render(request, "orders/photos.html", {
        "order": order,
        "form": form,
        "photos": photos,
        "count": len(photos),
        "photos_needed": max(0, tier.min_photos - len(photos)),
        "ready": tier.min_photos <= len(photos) <= tier.max_photos,
    })


@login_required
@require_POST
def save_caption(request, pk, photo_id):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    photo = get_object_or_404(OrderPhoto, pk=photo_id, order=order)
    if order.can_edit_photos:
        photo.caption = request.POST.get("caption", "").strip()[:200]  # same limit as the model field
        photo.save(update_fields=["caption"])
        messages.success(request, "Caption saved.")
    else:
        messages.error(request, "Your photos have already been submitted.")
    return redirect("order_photos", pk=order.pk)


@login_required
@require_POST
def delete_photo(request, pk, photo_id):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    photo = get_object_or_404(OrderPhoto, pk=photo_id, order=order)
    if order.can_edit_photos:
        photo.image.delete(save=False)  # remove the file from the media folder too
        photo.delete()
        messages.info(request, "Photo removed.")
    else:
        messages.error(request, "Your photos have already been submitted.")
    return redirect("order_photos", pk=order.pk)


@login_required
@require_POST
def submit_photos(request, pk):
    """Send the photos to the studio. After this the customer can no longer change them or cancel."""
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    if not order.can_edit_photos:
        messages.error(request, "Your photos have already been submitted.")
        return redirect("order_photos", pk=order.pk)

    count = order.photos.count()
    tier = order.tier
    if not (tier.min_photos <= count <= tier.max_photos):
        messages.error(request, f"Your {tier.name} package needs {tier.min_photos}–{tier.max_photos} photos. "
                                f"You have uploaded {count}.")
        return redirect("order_photos", pk=order.pk)

    order.status = Order.Status.SUBMITTED
    order.save(update_fields=["status", "updated_at"])
    order.add_event(f"Customer submitted {count} photos. Production can begin.", actor=request.user)
    messages.success(request, "Your photos have been sent to our studio. We'll start designing your book.")
    return redirect("order_photos", pk=order.pk)


# What the customer should do or expect next, for each status
NEXT_STEPS = {
    Order.Status.WAITING: "Upload your photos and submit them so our studio can begin.",
    Order.Status.SUBMITTED: "Your photos are with our studio. Production starts soon.",
    Order.Status.PRODUCING: "Our studio is designing your memory book.",
    Order.Status.DELIVERED: "Your PDF is ready. Approve it, or request your one free revision.",
    Order.Status.REVISION: "Our studio is working on the changes you asked for.",
    Order.Status.PRINTING: "Your book is being printed and packed in its gift box.",
    Order.Status.SHIPPED: "Your book is on its way. Let us know once it arrives.",
    Order.Status.COMPLETED: "This order is complete. Thank you for choosing MEMORA.",
    Order.Status.CANCELLED: "This order was cancelled and your demo payment refunded.",
}


def _order_page_context(order, user, revision_form=None):
    versions = list(order.versions.all())  # newest first
    return {
        "order": order,
        "latest": versions[0] if versions else None,
        "earlier_versions": versions[1:],
        "events": order.events.select_related("actor"),
        "photo_count": order.photos.count(),
        "next_step": NEXT_STEPS.get(order.status, ""),
        "can_accept": can_transition(order, "accept", user),
        "can_revise": can_transition(order, "revise", user),
        "can_receive": can_transition(order, "receive", user),
        "revision_form": revision_form or RevisionRequestForm(),
    }


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("cover", "tier", "gift_box"),
                              pk=pk, customer=request.user)
    return render(request, "orders/order_detail.html", _order_page_context(order, request.user))


@login_required
@require_POST
def request_revision(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    form = RevisionRequestForm(request.POST)
    if not form.is_valid():
        return render(request, "orders/order_detail.html",
                      _order_page_context(order, request.user, revision_form=form))
    try:
        transition(order, "revise", request.user, "Customer requested their free revision.",
                   revision_request=form.cleaned_data["details"])
    except TransitionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Revision requested. Our studio will send you an updated PDF.")
    return redirect("order_detail", pk=pk)


@login_required
@require_POST
def approve_design(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    try:
        transition(order, "accept", request.user, "Customer approved the final design.")
    except TransitionError as error:
        messages.error(request, str(error))
    else:
        if order.is_print:
            messages.success(request, "Design approved! We're now printing your book.")
        else:
            messages.success(request, "Design approved! Your memory book is complete.")
    return redirect("order_detail", pk=pk)


@login_required
@require_POST
def confirm_receipt(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    try:
        transition(order, "receive", request.user, "Customer confirmed the book arrived.")
    except TransitionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Thanks for confirming! We hope you love your book.")
    return redirect("order_detail", pk=pk)