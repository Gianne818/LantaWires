import json
from django.test import TestCase, Client
from django.urls import reverse

class HomeScreenTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Set authenticated session
        session = self.client.session
        session["current_user"] = {
            "id": "usr-01",
            "name": "Gianne Cruz",
            "email": "gianne@cebucity.ph",
            "phone": "+63 917 554 8921",
            "barangay": "Tisa",
            "avatar": "GC",
        }
        session.save()

    def test_unauthenticated_access_redirects_to_login(self):
        unauthenticated_client = Client()
        response = unauthenticated_client.get(reverse("home:index"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:index"))

    def test_home_screen_renders_with_user_and_metrics(self):
        response = self.client.get(reverse("home:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/home.html")
        self.assertContains(response, "Gianne Cruz")
        self.assertContains(response, "Brgy. Tisa")
        self.assertContains(response, "Total Verified")
        self.assertContains(response, "Active Dispatches")
        self.assertContains(response, "Critical Hazards")
        self.assertContains(response, "Resolved Bundles")
        self.assertContains(response, "Cebu Hotspot Map")
        self.assertContains(response, reverse("home:logout"))

    def test_create_report_api(self):
        payload = {
            "title": "Severe Low Hanging Power Cable",
            "barangay": "Tisa",
            "address": "Katipunan St., Brgy. Tisa",
            "severity": "critical",
            "hazardType": "sagging_cable",
            "confidence": 98.2,
            "sagClearance": "2.8m above roadway",
            "wireDensity": "Severe (40 cables)",
            "components": ["Power cable sag", "Telecom entanglement"],
        }
        response = self.client.post(
            reverse("home:create_report"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["report"]["barangay"], "Tisa")
        self.assertEqual(data["report"]["severity"], "critical")
        self.assertIn("LW-CEB-2026-", data["report"]["ticketNumber"])

    def test_update_status_api(self):
        payload = {
            "reportId": "rep-001",
            "newStatus": "resolved",
        }
        response = self.client.post(
            reverse("home:update_status"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["newStatus"], "resolved")

    def test_logout_clears_session_and_redirects_to_login(self):
        response = self.client.get(reverse("home:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:index"))
        self.assertNotIn("current_user", self.client.session)
