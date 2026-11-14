from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator

from shop.models import FORMAT_CHOICES, FORMAT_PRINT, CoverStyle, GiftBox, PackageTier, Tag


class Order(models.Model):

    class Status(models.TextChoices):
        WAITING = "waiting", "Awaiting photos"
        SUBMITTED = "submitted", "Photos submitted"
        PRODUCING = "producing", "In production"
        DELIVERED = "delivered", "Awaiting your approval"
        REVISION = "revision", "Revision in progress"
        PRINTING = "printing", "Printing & packing"
        SHIPPED = "shipped", "Shipped"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")

    # What was bought
    cover = models.ForeignKey(CoverStyle, on_delete=models.PROTECT)
    tier = models.ForeignKey(PackageTier, on_delete=models.PROTECT)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    gift_box = models.ForeignKey(GiftBox, on_delete=models.PROTECT, null=True, blank=True)
    title = models.CharField(max_length=80)
    notes = models.TextField(blank=True)
    occasion_tags = models.ManyToManyField(Tag, related_name="orders_as_occasion")
    people_tags = models.ManyToManyField(Tag, related_name="orders_as_people")
    group_size = models.PositiveSmallIntegerField()
    event_days = models.PositiveSmallIntegerField()

    # What the ML model suggested for this story when the order was placed (shop/recommender.py)
    predicted_photos = models.PositiveSmallIntegerField(null=True, blank=True)
    recommended_tier = models.ForeignKey(
        PackageTier, on_delete=models.PROTECT, null=True, blank=True,
        related_name="recommended_orders",
    )

    # Payment and status info
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.WAITING)
    revision_used = models.BooleanField(default=False)
    revision_request = models.TextField(blank=True)
    paid_at = models.DateTimeField()

    # Contact and shipping info
    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    shipping_address = models.CharField(max_length=200, blank=True)
    shipping_postal_code = models.CharField(max_length=10, blank=True)
    courier = models.CharField(max_length=60, blank=True)
    tracking_number = models.CharField(max_length=60, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def number(self):
        return f"MEM-{self.pk:05d}"

    @property
    def is_print(self):
        return self.format == FORMAT_PRINT

    @property
    def followed_recommendation(self):
        """True if the customer bought the package the ML model recommended."""
        return self.recommended_tier_id == self.tier_id

    @property
    def can_cancel(self):
        """Customers can cancel for a full refund until they submit their photos."""
        return self.status == self.Status.WAITING

    @property
    def can_edit_photos(self):
        """Photos can be added, captioned and removed until the customer submits them."""
        return self.status == self.Status.WAITING

    @property
    def has_review(self):
        return hasattr(self, "review")

    @property
    def can_review(self):
        """Customers can review an order once it is completed, and only once."""
        return self.status == self.Status.COMPLETED and not self.has_review

    def add_event(self, message, actor=None):
        """Record a step in this order's timeline."""
        return self.events.create(message=message, actor=actor)

    def __str__(self):
        return f"{self.number} · {self.title}"


class OrderEvent(models.Model):
    """Status changes and who made them."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    message = models.CharField(max_length=200)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.order.number}: {self.message}"


class Review(models.Model):
    """A customer's rating of a completed order. Shown on the shop pages for that cover style."""

    RATING_CHOICES = [
        (5, "★★★★★ Loved it"),
        (4, "★★★★☆ Really good"),
        (3, "★★★☆☆ It was okay"),
        (2, "★★☆☆☆ Disappointing"),
        (1, "★☆☆☆☆ Poor"),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(max_length=500, blank=True)
    is_hidden = models.BooleanField(default=False)  # hide reviews
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def stars(self):
        """For example 4 becomes ★★★★☆."""
        return "★" * self.rating + "☆" * (5 - self.rating)

    @property
    def reviewer_name(self):
        """Only the first name is shown publicly."""
        names = self.order.contact_name.split()
        return names[0] if names else "A customer"

    def __str__(self):
        return f"{self.order.number}: {self.rating} stars"


def photo_upload_path(photo, filename):
    """Keep each order's photos in its own folder, e.g. media/orders/3/beach.jpg"""
    return f"orders/{photo.order_id}/{filename}"


class OrderPhoto(models.Model):
    """A photo the customer uploads for their memory book, with an optional caption."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=photo_upload_path)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at", "id"]

    def __str__(self):
        return f"{self.order.number}: photo {self.pk}"

def book_upload_path(version, filename):
    """Keep each order's PDFs together, e.g. media/books/3/v2-our-trip.pdf"""
    return f"books/{version.order_id}/v{version.number}-{filename}"


class BookVersion(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveSmallIntegerField()
    pdf = models.FileField(upload_to=book_upload_path, validators=[FileExtensionValidator(["pdf"])])
    note = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(fields=["order", "number"], name="unique_version_per_order"),
        ]

    @property
    def label(self):
        return "First version" if self.number == 1 else f"Revision {self.number - 1}"

    def __str__(self):
        return f"{self.order.number} v{self.number}"