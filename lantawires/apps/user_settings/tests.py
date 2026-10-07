from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from apps.user_settings.models import UserSettings

class SettingsFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="gianne@cebucity.ph",
            email="gianne@cebucity.ph",
            password="cebuwirehazard2026",
            first_name="Gianne Cruz"
        )
        self.settings = UserSettings.objects.create(
            user=self.user,
            dark_mode=True,
            email_notifications=True,
            hazard_alerts=True,
            auto_dispatch_updates=True,
            sound_alerts=False,
        )

    def test_unauthenticated_settings_access_redirects_to_login(self):
        response = self.client.get(reverse("user_settings:settings"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:login"))

    def test_authenticated_settings_view_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("user_settings:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user_settings/user_settings.html")
        self.assertContains(response, "Preferences")
        self.assertContains(response, "Dark clay mode")
        self.assertContains(response, "Barangay alerts")

    def test_settings_update_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("user_settings:settings"), {
            "dark_mode": "on",
            "email_notifications": "on",
            "hazard_alerts": "on",
            "sound_alerts": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.settings.refresh_from_db()
        self.assertTrue(self.settings.sound_alerts)
        self.assertFalse(self.settings.auto_dispatch_updates)
