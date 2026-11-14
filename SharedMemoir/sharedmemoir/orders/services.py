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