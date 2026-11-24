import base64
import json
import tempfile
from pathlib import Path
from django.test import TestCase, Client, override_settings
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
        self.assertContains(response, "Verified")
        self.assertContains(response, "Dispatched")
        self.assertContains(response, "Critical")
        self.assertContains(response, "Resolved")
        self.assertContains(response, "Report hazard")
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
        # Citizens cannot toggle
        response = self.client.post(
            reverse("home:update_status"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        # Resolvers can toggle
        session = self.client.session
        user = dict(session["current_user"])
        user["role"] = "resolver"
        session["current_user"] = user
        session.save()
        response = self.client.post(
            reverse("home:update_status"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["newStatus"], "resolved")

    def test_citizen_and_resolver_home_screens_differ(self):
        # Default session has no role -> Citizen Watch view
        citizen_res = self.client.get(reverse("home:index"))
        self.assertEqual(citizen_res.status_code, 200)
        self.assertTemplateUsed(citizen_res, "home/_citizen_dashboard.html")
        self.assertContains(citizen_res, "Citizen Watch")
        self.assertContains(citizen_res, "Neighborhood Hazards")

        # Resolver role -> TIC & VECO Triage Console view
        session = self.client.session
        user = dict(session["current_user"])
        user["role"] = "resolver"
        session["current_user"] = user
        session.save()
        resolver_res = self.client.get(reverse("home:index"))
        self.assertEqual(resolver_res.status_code, 200)
        self.assertTemplateUsed(resolver_res, "home/_resolver_dashboard.html")
        self.assertContains(resolver_res, "TIC &amp; VECO Triage Queue")
        self.assertContains(resolver_res, "Triage Queue")

    def test_update_status_api_supports_three_stages_and_validates(self):
        session = self.client.session
        user = dict(session["current_user"])
        user["role"] = "resolver"
        session["current_user"] = user
        session.save()

        # Investigating stage
        res_inv = self.client.post(
            reverse("home:update_status"),
            data=json.dumps({"reportId": "rep-001", "newStatus": "investigating"}),
            content_type="application/json",
        )
        self.assertEqual(res_inv.status_code, 200)
        self.assertEqual(res_inv.json()["newStatus"], "investigating")

        # Invalid status rejected
        res_bad = self.client.post(
            reverse("home:update_status"),
            data=json.dumps({"reportId": "rep-001", "newStatus": "bogus"}),
            content_type="application/json",
        )
        self.assertEqual(res_bad.status_code, 400)

    def test_my_reports_and_dispatches_role_access(self):
        # Citizen can view My Reports
        my_res = self.client.get(reverse("home:my_reports"))
        self.assertEqual(my_res.status_code, 200)
        self.assertTemplateUsed(my_res, "home/my_reports.html")
        self.assertContains(my_res, "My Submitted Hazard Reports")

        # Citizen cannot view Dispatches console (redirects back to home)
        blocked_res = self.client.get(reverse("home:dispatches"))
        self.assertEqual(blocked_res.status_code, 302)
        self.assertRedirects(blocked_res, reverse("home:home"))

        # Resolver can view Dispatches console
        session = self.client.session
        user = dict(session["current_user"])
        user["role"] = "resolver"
        session["current_user"] = user
        session.save()
        ok_res = self.client.get(reverse("home:dispatches"))
        self.assertEqual(ok_res.status_code, 200)
        self.assertTemplateUsed(ok_res, "home/dispatches.html")
        self.assertContains(ok_res, "Agency Dispatches")

    def test_update_dispatch_api_role_guard_and_persistence(self):
        from apps.home.models import HazardCategory, HazardDispatch, HazardReport, UtilityAgency
        from apps.profile.models import CebuBarangay

        brgy = CebuBarangay.objects.create(
            name="Tisa", district="South District", zip_code="6000", center_lat=10.2982, center_lng=123.8741
        )
        cat = HazardCategory.objects.create(
            code="SAGGING_CABLE", category_name="Sagging Cable", min_clearance=4.5, default_severity="critical"
        )
        rep = HazardReport.objects.create(
            ticket_number="LW-TEST-0001", title="Test Wire", barangay=brgy, category=cat, address="Tisa Main"
        )
        agency = UtilityAgency.objects.create(
            agency_name="Visayan Electric (VECO)", department="Safety", contact_email="veco@test.ph", hotline_number="230", agency_type="Power"
        )
        disp = HazardDispatch.objects.create(report=rep, agency=agency, delivery_status="Delivered")

        # Citizen rejected with 403
        res_forbidden = self.client.post(
            reverse("home:update_dispatch"),
            data=json.dumps({"dispatchId": disp.id, "deliveryStatus": "Resolved"}),
            content_type="application/json",
        )
        self.assertEqual(res_forbidden.status_code, 403)

        # Resolver updates dispatch & report syncs to resolved
        session = self.client.session
        user = dict(session["current_user"])
        user["role"] = "resolver"
        session["current_user"] = user
        session.save()
        res_ok = self.client.post(
            reverse("home:update_dispatch"),
            data=json.dumps({
                "dispatchId": disp.id,
                "deliveryStatus": "Resolved",
                "resolutionNotes": "Line re-tensioned by VECO crew",
            }),
            content_type="application/json",
        )
        self.assertEqual(res_ok.status_code, 200)
        disp.refresh_from_db()
        rep.refresh_from_db()
        self.assertEqual(disp.delivery_status, "Resolved")
        self.assertEqual(disp.resolution_notes, "Line re-tensioned by VECO crew")
        self.assertEqual(rep.status, "resolved")

    def test_dispatches_active_hotspot_barangays_subquery(self):
        from django.db.models import Subquery
        from apps.home.models import HazardCategory, HazardReport
        from apps.profile.models import CebuBarangay

        brgy_active = CebuBarangay.objects.create(
            name="Tisa", district="South District", zip_code="6000", center_lat=10.2982, center_lng=123.8741, hotline_number="(032) 261-0412"
        )
        brgy_resolved = CebuBarangay.objects.create(
            name="Guadalupe", district="South District", zip_code="6000", center_lat=10.3223, center_lng=123.8812, hotline_number="(032) 254-4411"
        )
        CebuBarangay.objects.create(
            name="Apas", district="North District", zip_code="6000", center_lat=10.3341, center_lng=123.9085, hotline_number="(032) 231-5511"
        )
        cat = HazardCategory.objects.create(
            code="SAGGING_CABLE", category_name="Sagging Cable", min_clearance=4.5, default_severity="critical"
        )
        HazardReport.objects.create(
            ticket_number="LW-SUB-0001", title="Active Sag", barangay=brgy_active, category=cat, address="Tisa Rd", status="dispatched"
        )
        HazardReport.objects.create(
            ticket_number="LW-SUB-0002", title="Cleared Wire", barangay=brgy_resolved, category=cat, address="Guadalupe Rd", status="resolved"
        )

        # Verify Django ORM generates a genuine SQL Subquery
        inner_qs = HazardReport.objects.exclude(status="resolved").values("barangay_id")
        outer_qs = CebuBarangay.objects.filter(id__in=Subquery(inner_qs)).order_by("name")
        self.assertIn("IN (SELECT", str(outer_qs.query))
        self.assertEqual([b.name for b in outer_qs], ["Tisa"])

        # Verify resolver view renders only active hotspot barangays
        session = self.client.session
        user = dict(session["current_user"])
        user["role"] = "resolver"
        session["current_user"] = user
        session.save()

        res = self.client.get(reverse("home:dispatches"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual([b.name for b in res.context["active_hotspot_barangays"]], ["Tisa"])
        self.assertEqual(res.context["total_barangays_count"], 3)
        self.assertContains(res, "Active Hotspot Barangays")
        self.assertContains(res, "(032) 261-0412")
        self.assertNotContains(res, "(032) 254-4411")
        self.assertNotContains(res, "(032) 231-5511")

    def test_create_report_api_requires_authentication(self):
        unauthenticated_client = Client()
        response = unauthenticated_client.post(
            reverse("home:create_report"),
            data=json.dumps({"title": "Unauthorized wire report"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_create_report_api_persists_base64_photo_to_media_and_db(self):
        from apps.home.models import HazardReport

        tiny_png_b64 = base64.b64encode(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        ).decode("ascii")
        with tempfile.TemporaryDirectory() as tmp_dir:
            with override_settings(MEDIA_ROOT=tmp_dir, MEDIA_URL="/media/"):
                response = self.client.post(
                    reverse("home:create_report"),
                    data=json.dumps({
                        "title": "Base64 Wire Photo Test",
                        "barangay": "Tisa",
                        "address": "Katipunan St.",
                        "imageUrl": f"data:image/png;base64,{tiny_png_b64}",
                    }),
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(HazardReport.objects.count(), 1)
            report = HazardReport.objects.first()
            self.assertTrue(report.image_url.startswith("/media/hazards/"))
            self.assertLessEqual(len(report.image_url), 500)
            filename = report.image_url.replace("/media/hazards/", "", 1)
            self.assertTrue((Path(tmp_dir) / "hazards" / filename).is_file())

    def test_my_reports_tracks_user_by_reporter_fk_after_name_change(self):
        from django.contrib.auth.models import User
        from apps.home.models import HazardCategory, HazardReport
        from apps.profile.models import CebuBarangay, Profile

        user = User.objects.create_user(
            username="citizen@cebucity.ph",
            email="citizen@cebucity.ph",
            password="cebuwirehazard2026",
            first_name="Original Name",
        )
        brgy = CebuBarangay.objects.create(
            name="Lahug", district="North District", zip_code="6000", center_lat=10.3298, center_lng=123.9056
        )
        profile = Profile.objects.create(
            user=user, full_name="Original Name", phone="+63 917 111 2222", barangay=brgy, role="citizen"
        )
        cat = HazardCategory.objects.create(
            code="SAGGING_CABLE", category_name="Sagging Cable", min_clearance=4.5, default_severity="high"
        )
        HazardReport.objects.create(
            ticket_number="LW-FK-0001",
            title="FK Ownership Report",
            reporter=user,
            barangay=brgy,
            category=cat,
            address="Salinas Dr.",
        )

        # Simulate name change after report creation
        profile.full_name = "Updated Citizen Name"
        profile.save()
        user.first_name = "Updated Citizen Name"
        user.save()

        auth_client = Client()
        auth_client.force_login(user)
        res = auth_client.get(reverse("home:my_reports"))
        self.assertEqual(res.status_code, 200)
        tickets = [r["ticketNumber"] for r in res.context["my_reports"]]
        self.assertIn("LW-FK-0001", tickets)

    def test_logout_clears_session_and_redirects_to_login(self):
        response = self.client.get(reverse("home:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:index"))
        self.assertNotIn("current_user", self.client.session)
