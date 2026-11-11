from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegisterTests(TestCase):

    def setUp(self):
        self.valid_data = {
            "username": "new_user",
            "email": "new_user@example.com",
            "password1": "TestPassword123!",
            "password2": "TestPassword123!",
        }

    def test_register_page_loads(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")

    def test_register_successfully(self):
        response = self.client.post(
            reverse("register"),
            self.valid_data
        )

        # After registering, the user goes back to the home page
        self.assertRedirects(response, reverse("home"))

        # One user is saved in the database
        self.assertEqual(User.objects.count(), 1)

        # The new user is already logged in
        home_page = self.client.get(reverse("home"))
        self.assertContains(home_page, "Hi, new_user")

    def test_passwords_do_not_match(self):
        invalid_data = self.valid_data.copy()
        invalid_data["password2"] = "DifferentPassword456!"

        response = self.client.post(
            reverse("register"),
            invalid_data
        )

        # The form is shown again and no user is saved
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)


class LogoutTests(TestCase):

    def test_logout(self):
        user = User.objects.create_user(
            username="logout_user",
            password="TestPassword123!"
        )
        self.client.force_login(user)

        # Logout must be a POST request
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("home"))

        # The navbar shows "Log in" again
        home_page = self.client.get(reverse("home"))
        self.assertContains(home_page, "Log in")
