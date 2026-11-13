from django.conf import settings
from django.db import models

class CustomerProfile(models.Model):

    AGE_GROUPS = [
        ("18-24", "18–24"),
        ("25-34", "25–34"),
        ("35-44", "35–44"),
        ("45-54", "45–54"),
        ("55+", "55 and above"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    age_group = models.CharField(max_length=10, choices=AGE_GROUPS)
    address_line = models.CharField("Shipping address", max_length=200, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.user.username})"