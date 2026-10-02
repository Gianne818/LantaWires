from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from apps.profile.models import CebuBarangay, Profile

class ProfileFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="gianne@cebucity.ph",
            email="gianne@cebucity.ph",
            password="cebuwirehazard2026",
            first_name="Gianne Cruz"
        )
        self.barangay = CebuBarangay.objects.get_or_create(
            name="Tisa",
            defaults={
                "district": "South District",
                "zip_code": "6000",
                "center_lat": 10.2982,
                "center_lng": 123.8741,
            },
        )[0]
        self.profile = Profile.objects.create(
            user=self.user,
            full_name="Gianne Cruz",
            phone="+63 917 554 8921",
            barangay=self.barangay,
            bio="Lead Civic Safety Responder",
            avatar="GC"
        )

    def test_unauthenticated_profile_access_redirects_to_login(self):
        response = self.client.get(reverse("profile:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:login"))

    def test_authenticated_profile_view_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile/profile.html")
        self.assertContains(response, "Gianne Cruz")
        self.assertContains(response, "Brgy. Tisa")
        self.assertContains(response, "Lead Civic Safety Responder")

    def test_profile_update_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile:profile"), {
            "full_name": "Gianne C. Cruz",
            "phone": "+63 917 999 8888",
            "barangay": "Lahug",
            "bio": "Senior Volunteer Coordinator",
            "avatar": "GC",
        })
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, "Gianne C. Cruz")
        self.assertEqual(self.profile.barangay.name, "Lahug")
        self.assertEqual(self.profile.phone, "+63 917 999 8888")
