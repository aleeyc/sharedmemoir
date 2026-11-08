from django.conf import settings
from django.db import models


class Trip(models.Model):
    class TripType(models.TextChoices):
        FAMILY = "family", "Family"
        FRIENDS = "friends", "Friends"
        COUPLE = "couple", "Couple"
        SCHOOL = "school", "School"

    title = models.CharField(max_length=120)
    destination_region = models.CharField(max_length=80)

    trip_type = models.CharField(
        max_length=20,
        choices=TripType.choices
    )

    start_date = models.DateField()
    end_date = models.DateField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_trips"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def trip_length_days(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return self.title
