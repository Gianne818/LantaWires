from django.test import TestCase, Client
from django.urls import reverse

class LoginScreenTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_root_redirects_to_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:index"))

    def test_login_screen_renders_successfully(self):
        response = self.client.get(reverse("login:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login/login.html")
        self.assertContains(response, "LantaWires")
        self.assertContains(response, "Login")
        self.assertContains(response, "Email Address")
        self.assertContains(response, reverse("register:index"))

    def test_login_post_missing_fields_shows_error(self):
        response = self.client.post(reverse("login:index"), {"email": "", "password": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter both your email and password.")

    def test_login_post_valid_credentials_transitions_to_home(self):
        response = self.client.post(reverse("login:index"), {
            "email": "gianne@cebucity.ph",
            "password": "cebuwirehazard2026",
            "remember_me": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home:index"))
        self.assertEqual(self.client.session["current_user"]["name"], "Gianne Cruz")
        self.assertEqual(self.client.session["current_user"]["barangay"], "Tisa")
