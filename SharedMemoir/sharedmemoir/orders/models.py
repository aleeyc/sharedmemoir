from django.conf import settings
from django.db import models

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

    # Payment and status info
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.WAITING)
    revision_used = models.BooleanField(default=False)
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