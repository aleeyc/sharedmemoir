from .models import FORMAT_PRINT, CoverStyle, GiftBox, PackageTier, Tag

BAG_SESSION_KEY = "bag"

def save_bag(request, cleaned, recommended_tier=None, predicted_photos=None):
    """Store the customised book in the session. Only IDs and plain values go in,
    because the session is saved as JSON.
    recommended_tier and predicted_photos are the ML model's output (shop/recommender.py)."""
    request.session[BAG_SESSION_KEY] = {
        "cover_id": cleaned["cover"].id,
        "format": cleaned["format"],
        "tier_id": cleaned["tier"].id,
        "occasion_ids": [tag.id for tag in cleaned["occasion_tags"]],
        "people_ids": [tag.id for tag in cleaned["people_tags"]],
        "group_size": cleaned["group_size"],
        "event_days": cleaned["event_days"],
        "title": cleaned["title"],
        "gift_box_id": cleaned["gift_box"].id if cleaned["gift_box"] else None,
        "notes": cleaned["notes"],
        "recommended_tier_id": recommended_tier.id if recommended_tier else None,
        "predicted_photos": predicted_photos,
    }


def clear_bag(request):
    request.session.pop(BAG_SESSION_KEY, None)


def bag_initial(data):
    """Turn the stored bag back into form initial values, for 'Edit customisation'."""
    return {
        "cover": data["cover_id"],
        "format": data["format"],
        "tier": data["tier_id"],
        "occasion_tags": data["occasion_ids"],
        "people_tags": data["people_ids"],
        "group_size": data["group_size"],
        "event_days": data["event_days"],
        "title": data["title"],
        "gift_box": data["gift_box_id"],
        "notes": data["notes"],
    }


def get_bag(request):
    """Return the bag with real objects and the price, or None if it is empty or out of date."""
    data = request.session.get(BAG_SESSION_KEY)
    if not data:
        return None
    try:
        cover = CoverStyle.objects.get(pk=data["cover_id"], is_active=True)
        tier = PackageTier.objects.get(pk=data["tier_id"], is_active=True)
    except (CoverStyle.DoesNotExist, PackageTier.DoesNotExist):
        clear_bag(request)  # staff deactivated the cover or package since it was added
        return None

    is_print = data["format"] == FORMAT_PRINT
    return {
        **data,
        "cover": cover,
        "tier": tier,
        "is_print": is_print,
        "gift_box": GiftBox.objects.filter(pk=data["gift_box_id"]).first() if is_print else None,
        "occasion_tags": Tag.objects.filter(pk__in=data["occasion_ids"]),
        "people_tags": Tag.objects.filter(pk__in=data["people_ids"]),
        "price": tier.print_price if is_print else tier.digital_price,
        # The package the ML model recommended (None if there is no recommendation).
        "recommended_tier": PackageTier.objects.filter(pk=data.get("recommended_tier_id")).first(),
    }