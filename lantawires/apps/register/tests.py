from django.test import TestCase, Client
from django.urls import reverse

class RegisterScreenTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_screen_renders_successfully(self):
        response = self.client.get(reverse("register:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "register/register.html")
        self.assertContains(response, "Create Account")
        self.assertContains(response, "Cebu City Barangay")
        self.assertContains(response, "Brgy. Tisa")
        self.assertContains(response, "Brgy. Lahug")
        self.assertContains(response, reverse("login:index"))

    def test_register_post_missing_fields_shows_error(self):
        response = self.client.post(reverse("register:index"), {
            "name": "",
            "email": "",
            "phone": "",
            "password": "",
            "confirm_password": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please provide your full name.")

    def test_register_post_password_mismatch_shows_error(self):
        response = self.client.post(reverse("register:index"), {
            "name": "Maria Santos",
            "email": "maria@cebu.ph",
            "phone": "+63 917 111 2222",
            "barangay": "Lahug",
            "password": "password123",
            "confirm_password": "password456",
            "agree_terms": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password confirmation does not match.")

    def test_register_post_valid_transitions_to_login_then_user_can_login_to_home(self):
        # 1. Register account
        response = self.client.post(reverse("register:index"), {
            "name": "Eduardo Morales",
            "email": "morales.cebu@gmail.com",
            "phone": "+63 920 882 1042",
            "barangay": "Lahug",
            "password": "cebuwirehazard2026",
            "confirm_password": "cebuwirehazard2026",
            "agree_terms": "on",
        })
        # Verifies transition back to Login screen
        self.assertEqual(response.status_code, 302)
        from django.contrib.auth.models import User
        from apps.profile.models import Profile
        self.assertTrue(User.objects.filter(email="morales.cebu@gmail.com").exists())
        self.assertTrue(Profile.objects.filter(user__email="morales.cebu@gmail.com").exists())

        # 2. Login screen shows the created account notice & prefilled email
        login_page = self.client.get(reverse("login:index") + "?registered_email=morales.cebu@gmail.com")
        self.assertEqual(login_page.status_code, 200)
        self.assertContains(login_page, "morales.cebu@gmail.com")
        self.assertContains(login_page, "Account created successfully.")

        # 3. Now user logs in using the registered credentials -> transitions to Home screen
        login_response = self.client.post(reverse("login:index"), {
            "email": "morales.cebu@gmail.com",
            "password": "cebuwirehazard2026",
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertRedirects(login_response, reverse("home:index"))
        self.assertEqual(self.client.session["current_user"]["name"], "Eduardo Morales")
        self.assertEqual(self.client.session["current_user"]["barangay"], "Lahug")
