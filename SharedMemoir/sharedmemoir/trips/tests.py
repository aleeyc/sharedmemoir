from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Trip


class TripCreationTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="trip_test_user",
            password="TestPassword123!"
        )

        self.valid_data = {
            "title": "Japan Graduation Trip",
            "destination_region": "Japan",
            "trip_type": "friends",
            "start_date": "2026-12-10",
            "end_date": "2026-12-16",
        }

    def test_login_required(self):
        response = self.client.get(
            reverse("trips:create")
        )

        expected_url = (
            reverse("login")
            + "?next="
            + reverse("trips:create")
        )

        self.assertRedirects(response, expected_url)

    def test_create_trip_successfully(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("trips:create"),
            self.valid_data
        )

        self.assertRedirects(response, reverse("home"))

        self.assertEqual(Trip.objects.count(), 1)

        trip = Trip.objects.first()

        self.assertEqual(trip.created_by, self.user)
        self.assertEqual(trip.trip_length_days, 7)

    def test_invalid_trip_dates(self):
        self.client.force_login(self.user)

        invalid_data = self.valid_data.copy()
        invalid_data["end_date"] = "2026-12-09"

        response = self.client.post(
            reverse("trips:create"),
            invalid_data
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "End date cannot be earlier than start date."
        )

        self.assertEqual(Trip.objects.count(), 0)
