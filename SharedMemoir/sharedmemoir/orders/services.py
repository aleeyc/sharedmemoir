from django.db import transaction
from django.db.models import F
from django.utils import timezone

from shop.models import GiftBox

from .models import Order


class OutOfStock(Exception):
    """Error raised when the chosen gift box sold out between adding to bag and paying."""

@transaction.atomic
def place_order(user, bag, data):
    gift_box = bag["gift_box"]
    if bag["is_print"]:
        updated = 0
        if gift_box is not None:
            updated = GiftBox.objects.filter(pk=gift_box.pk, stock__gt=0).update(stock=F("stock") - 1)
        if updated == 0:
            raise OutOfStock()

    order = Order.objects.create(
        customer=user,
        cover=bag["cover"],
        tier=bag["tier"],
        format=bag["format"],
        gift_box=gift_box,
        title=bag["title"],
        notes=bag["notes"],
        group_size=bag["group_size"],
        event_days=bag["event_days"],
        predicted_photos=bag.get("predicted_photos"),
        recommended_tier=bag.get("recommended_tier"),
        amount=bag["price"],
        paid_at=timezone.now(),
        contact_name=data["contact_name"],
        contact_email=data["contact_email"],
        contact_phone=data["contact_phone"],
        shipping_address=data.get("shipping_address", ""),
        shipping_postal_code=data.get("shipping_postal_code", ""),
    )
    order.occasion_tags.set(bag["occasion_tags"])
    order.people_tags.set(bag["people_tags"])
    order.add_event("Order placed and demo payment completed.", actor=user)
    return order


@transaction.atomic
def cancel_and_refund(order, user):
    """Cancel an order that is still waiting for photos and put its gift box back in stock.
    Returns False if the order has moved on and can no longer be cancelled."""
    # Only change the status if it is still "waiting". This also stops a double click
    # from cancelling twice and returning two gift boxes to stock.
    updated = Order.objects.filter(pk=order.pk, status=Order.Status.WAITING).update(
        status=Order.Status.CANCELLED, updated_at=timezone.now(),
    )
    if updated == 0:
        return False

    if order.gift_box_id:
        GiftBox.objects.filter(pk=order.gift_box_id).update(stock=F("stock") + 1)
    order.add_event("Order cancelled by the customer. Full refund issued (demo).", actor=user)
    return True

class TransitionError(Exception):
    """Raised when someone tries an action the order's current status doesn't allow."""


S = Order.Status

# The production workflow after photos are submitted
TRANSITIONS = {
    "start":   ({S.SUBMITTED}, "staff", S.PRODUCING),
    "deliver": ({S.PRODUCING, S.REVISION}, "staff", S.DELIVERED),
    "revise":  ({S.DELIVERED}, "customer", S.REVISION),
    "accept":  ({S.DELIVERED}, "customer", None),
    "ship":    ({S.PRINTING}, "staff", S.SHIPPED),
    "receive": ({S.SHIPPED}, "customer", S.COMPLETED),
}


def can_transition(order, event, user):
    """True if this user may perform this event on this order right now."""
    allowed_statuses, role, _next_status = TRANSITIONS[event]
    if order.status not in allowed_statuses:
        return False
    if event == "revise" and order.revision_used:
        return False  # only one free revision
    if role == "customer":
        return order.customer_id == user.id
    return user.is_staff


@transaction.atomic
def transition(order, event, user, message, **changes):
    """Check the rules, move the order to its next status, save any extra field changes
    (e.g. courier and tracking number) and record the step in the timeline."""
    if not can_transition(order, event, user):
        raise TransitionError("That action isn't available for this order right now.")

    next_status = TRANSITIONS[event][2]
    if event == "accept":
        next_status = S.PRINTING if order.is_print else S.COMPLETED
    if event == "revise":
        order.revision_used = True

    for field, value in changes.items():
        setattr(order, field, value)
    order.status = next_status
    order.save()
    order.add_event(message, actor=user)
    return order


@transaction.atomic
def deliver_pdf(order, user, pdf, note=""):
    if not can_transition(order, "deliver", user):
        raise TransitionError("A PDF can only be delivered while the order is in production or revision.")
    number = order.versions.count() + 1
    order.versions.create(number=number, pdf=pdf, note=note, uploaded_by=user)
    label = "first version" if number == 1 else f"revised version (v{number})"
    return transition(order, "deliver", user, f"Studio delivered the {label} of the PDF.")