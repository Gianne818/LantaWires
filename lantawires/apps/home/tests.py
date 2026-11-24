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

    def test_edit_report_api_permissions_and_persistence(self):
        from django.contrib.auth.models import User
        from apps.home.models import AIHazardAnalysis, HazardCategory, HazardReport
        from apps.profile.models import CebuBarangay, Profile

        brgy_tisa = CebuBarangay.objects.create(
            name="Tisa", district="South District", zip_code="6000", center_lat=10.2982, center_lng=123.8741
        )
        CebuBarangay.objects.create(
            name="Lahug", district="North District", zip_code="6000", center_lat=10.3298, center_lng=123.9056
        )
        cat_sag = HazardCategory.objects.create(
            code="SAGGING_CABLE", category_name="Sagging Overhead Cable", min_clearance=4.5, default_severity="critical"
        )
        HazardCategory.objects.create(
            code="BURNING_SPARKING", category_name="Transformer Arcing / Fire Hazard", min_clearance=5.5, default_severity="critical"
        )

        owner = User.objects.create_user(username="owner@cebucity.ph", email="owner@cebucity.ph", password="pw")
        Profile.objects.create(user=owner, full_name="Owner Citizen", phone="+63 917", barangay=brgy_tisa, role="citizen")

        other = User.objects.create_user(username="other@cebucity.ph", email="other@cebucity.ph", password="pw")
        Profile.objects.create(user=other, full_name="Other Citizen", phone="+63 917", barangay=brgy_tisa, role="citizen")

        resolver = User.objects.create_user(username="res@cebucity.ph", email="res@cebucity.ph", password="pw")
        Profile.objects.create(user=resolver, full_name="TIC Resolver", phone="+63 917", barangay=brgy_tisa, role="resolver")

        report = HazardReport.objects.create(
            ticket_number="LW-EDIT-0001",
            title="Initial Sagging Wire",
            reporter=owner,
            barangay=brgy_tisa,
            category=cat_sag,
            address="Old St.",
            severity="high",
            clearance_meters=3.2,
            status="dispatched",
        )
        ai = AIHazardAnalysis.objects.create(
            report=report,
            confidence_score=95.0,
            detected_components="Drop wire",
            recommended_action="Check sag",
            safety_warning="Low wire",
            cable_sag_clearance="3.2m clearance",
            wire_density_score="High",
            severity_rating="high",
        )

        edit_url = reverse("home:edit_report", kwargs={"report_id": report.id})

        # Unauthenticated rejected with 401
        unauth_res = Client().post(edit_url, data=json.dumps({"title": "Hack"}), content_type="application/json")
        self.assertEqual(unauth_res.status_code, 401)

        # Other citizen rejected with 403
        other_client = Client()
        other_client.force_login(other)
        other_res = other_client.post(edit_url, data=json.dumps({"title": "Not Mine"}), content_type="application/json")
        self.assertEqual(other_res.status_code, 403)

        # Owner can edit unresolved report
        owner_client = Client()
        owner_client.force_login(owner)
        ok_res = owner_client.post(
            edit_url,
            data=json.dumps({
                "title": "Sparking Transformer Wire",
                "barangay": "Lahug",
                "address": "Salinas Dr., Lahug",
                "hazardType": "transformer_spark",
                "severity": "critical",
                "clearanceHeightMeters": 2.1,
            }),
            content_type="application/json",
        )
        self.assertEqual(ok_res.status_code, 200)
        report.refresh_from_db()
        ai.refresh_from_db()
        self.assertEqual(report.title, "Sparking Transformer Wire")
        self.assertEqual(report.barangay.name, "Lahug")
        self.assertEqual(report.category.code, "BURNING_SPARKING")
        self.assertEqual(report.severity, "critical")
        self.assertEqual(report.clearance_meters, 2.1)
        self.assertEqual(ai.severity_rating, "critical")
        self.assertEqual(ai.cable_sag_clearance, "2.1m clearance")

        # Resolved report cannot be edited by citizen owner, but can by resolver
        report.status = "resolved"
        report.save()
        locked_res = owner_client.post(edit_url, data=json.dumps({"title": "Too Late"}), content_type="application/json")
        self.assertEqual(locked_res.status_code, 403)

        resolver_client = Client()
        resolver_client.force_login(resolver)
        res_edit = resolver_client.post(edit_url, data=json.dumps({"title": "Resolver Corrected Title"}), content_type="application/json")
        self.assertEqual(res_edit.status_code, 200)
        report.refresh_from_db()
        self.assertEqual(report.title, "Resolver Corrected Title")

    def test_delete_report_api_permissions_and_cascade(self):
        from django.contrib.auth.models import User
        from apps.home.models import AIHazardAnalysis, HazardCategory, HazardDispatch, HazardReport, UtilityAgency
        from apps.profile.models import CebuBarangay, Profile

        brgy = CebuBarangay.objects.create(
            name="Tisa", district="South District", zip_code="6000", center_lat=10.2982, center_lng=123.8741
        )
        cat = HazardCategory.objects.create(
            code="SAGGING_CABLE", category_name="Sagging Overhead Cable", min_clearance=4.5, default_severity="critical"
        )
        agency = UtilityAgency.objects.create(
            agency_name="TIC", department="Task Force", contact_email="tic@test.ph", hotline_number="411", agency_type="LGU"
        )

        owner = User.objects.create_user(username="delowner@cebucity.ph", email="delowner@cebucity.ph", password="pw")
        Profile.objects.create(user=owner, full_name="Owner", phone="+63 917", barangay=brgy, role="citizen")

        other = User.objects.create_user(username="delother@cebucity.ph", email="delother@cebucity.ph", password="pw")
        Profile.objects.create(user=other, full_name="Other", phone="+63 917", barangay=brgy, role="citizen")

        resolver = User.objects.create_user(username="delres@cebucity.ph", email="delres@cebucity.ph", password="pw")
        Profile.objects.create(user=resolver, full_name="Resolver", phone="+63 917", barangay=brgy, role="resolver")

        report = HazardReport.objects.create(
            ticket_number="LW-DEL-0001", title="Delete Target", reporter=owner, barangay=brgy, category=cat, address="Tisa", status="resolved"
        )
        AIHazardAnalysis.objects.create(
            report=report, confidence_score=91.0, detected_components="Wire", recommended_action="Fix", safety_warning="Warn", cable_sag_clearance="3.0m", wire_density_score="High", severity_rating="high"
        )
        HazardDispatch.objects.create(report=report, agency=agency, delivery_status="Delivered")

        del_url = reverse("home:delete_report", kwargs={"report_id": report.id})

        self.assertEqual(Client().post(del_url).status_code, 401)

        other_client = Client()
        other_client.force_login(other)
        self.assertEqual(other_client.post(del_url).status_code, 403)

        owner_client = Client()
        owner_client.force_login(owner)
        # Resolved -> blocked for citizen
        self.assertEqual(owner_client.post(del_url).status_code, 403)

        # Unresolved -> owner can withdraw & cascades AI + Dispatches
        report.status = "dispatched"
        report.save()
        ok_del = owner_client.post(del_url)
        self.assertEqual(ok_del.status_code, 200)
        self.assertEqual(HazardReport.objects.count(), 0)
        self.assertEqual(AIHazardAnalysis.objects.count(), 0)
        self.assertEqual(HazardDispatch.objects.count(), 0)

        # Resolver can delete even resolved reports
        report2 = HazardReport.objects.create(
            ticket_number="LW-DEL-0002", title="Resolver Delete Target", reporter=owner, barangay=brgy, category=cat, address="Tisa", status="resolved"
        )
        resolver_client = Client()
        resolver_client.force_login(resolver)
        res_del = resolver_client.post(reverse("home:delete_report", kwargs={"report_id": report2.id}))
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(HazardReport.objects.count(), 0)

    def test_home_wizard_and_my_reports_render_crud_controls(self):
        from django.contrib.auth.models import User
        from apps.home.models import HazardCategory, HazardReport
        from apps.profile.models import CebuBarangay, Profile

        home_res = self.client.get(reverse("home:index"))
        self.assertEqual(home_res.status_code, 200)
        self.assertContains(home_res, "wizard-hazard-type-select")
        self.assertContains(home_res, "wizard-severity-select")
        self.assertContains(home_res, "wizard-clearance-input")
        self.assertContains(home_res, "wizard-geolocate-btn")
        self.assertContains(home_res, "detail-edit-form")
        self.assertContains(home_res, "edit-incident-btn")

        brgy = CebuBarangay.objects.create(
            name="Tisa", district="South District", zip_code="6000", center_lat=10.2982, center_lng=123.8741
        )
        cat = HazardCategory.objects.create(
            code="SAGGING_CABLE", category_name="Sagging Overhead Cable", min_clearance=4.5, default_severity="critical"
        )
        citizen = User.objects.create_user(username="crudcit@cebucity.ph", email="crudcit@cebucity.ph", password="pw", first_name="CRUD Citizen")
        Profile.objects.create(user=citizen, full_name="CRUD Citizen", phone="+63 917", barangay=brgy, role="citizen")
        HazardReport.objects.create(
            ticket_number="LW-CRUD-0001", title="Editable Citizen Wire", reporter=citizen, barangay=brgy, category=cat, address="Tisa St.", status="dispatched"
        )

        cit_client = Client()
        cit_client.force_login(citizen)
        my_res = cit_client.get(reverse("home:my_reports"))
        self.assertEqual(my_res.status_code, 200)
        self.assertContains(my_res, "my-report-inspect-btn")
        self.assertContains(my_res, "my-report-edit-btn")
        self.assertContains(my_res, "my-report-delete-btn")

    def test_create_dispatch_api_multi_agency_and_duplicate_guard(self):
        from apps.home.models import HazardCategory, HazardDispatch, HazardReport, UtilityAgency
        from apps.profile.models import CebuBarangay

        brgy = CebuBarangay.objects.create(
            name="Lahug", district="North District", zip_code="6000", center_lat=10.3298, center_lng=123.9056
        )
        cat = HazardCategory.objects.create(
            code="TANGLED_SPAGHETTI", category_name="Overcrowded Spaghetti Cluster", min_clearance=4.0, default_severity="high"
        )
        rep = HazardReport.objects.create(
            ticket_number="LW-DISP-0001", title="Spaghetti Cluster", barangay=brgy, category=cat, address="Salinas Dr."
        )
        pldt = UtilityAgency.objects.create(
            agency_name="PLDT-Smart Network Operations",
            department="Overhead Cable Maintenance",
            contact_email="fieldops@pldt.com.ph",
            hotline_number="171",
            agency_type="Telco",
        )

        create_url = reverse("home:create_dispatch")
        payload = json.dumps({"reportId": rep.id, "agencyId": pldt.id, "resolutionNotes": "Prune dead drop lines"})

        self.assertEqual(Client().post(create_url, data=payload, content_type="application/json").status_code, 401)
        self.assertEqual(self.client.post(create_url, data=payload, content_type="application/json").status_code, 403)

        session = self.client.session
        user = dict(session["current_user"])
        user["role"] = "resolver"
        session["current_user"] = user
        session.save()

        res_ok = self.client.post(create_url, data=payload, content_type="application/json")
        self.assertEqual(res_ok.status_code, 201)
        self.assertEqual(HazardDispatch.objects.count(), 1)
        self.assertEqual(res_ok.json()["dispatch"]["agencyName"], "PLDT-Smart Network Operations")

        # Duplicate dispatch for same report + agency rejected with 409
        res_dup = self.client.post(create_url, data=payload, content_type="application/json")
        self.assertEqual(res_dup.status_code, 409)

    def test_export_dispatches_csv_role_guard_and_filtering(self):
        from apps.home.models import HazardCategory, HazardDispatch, HazardReport, UtilityAgency
        from apps.profile.models import CebuBarangay

        brgy = CebuBarangay.objects.create(
            name="Tisa", district="South District", zip_code="6000", center_lat=10.2982, center_lng=123.8741
        )
        cat = HazardCategory.objects.create(
            code="SAGGING_CABLE", category_name="Sagging Overhead Cable", min_clearance=4.5, default_severity="critical"
        )
        rep1 = HazardReport.objects.create(
            ticket_number="LW-CSV-0001", title="Open Wire", barangay=brgy, category=cat, address="Tisa Rd", status="dispatched"
        )
        rep2 = HazardReport.objects.create(
            ticket_number="LW-CSV-0002", title="Cleared Wire", barangay=brgy, category=cat, address="Katipunan", status="resolved"
        )
        agency = UtilityAgency.objects.create(
            agency_name="Globe Telecom Quick Response",
            department="Wire Elevation",
            contact_email="wireclearance@globe.com.ph",
            hotline_number="211",
            agency_type="Telco",
        )
        HazardDispatch.objects.create(report=rep1, agency=agency, delivery_status="Delivered")
        HazardDispatch.objects.create(report=rep2, agency=agency, delivery_status="Resolved")

        export_url = reverse("home:export_dispatches_csv")
        blocked = self.client.get(export_url)
        self.assertEqual(blocked.status_code, 302)
        self.assertRedirects(blocked, reverse("home:home"))

        session = self.client.session
        user = dict(session["current_user"])
        user["role"] = "resolver"
        session["current_user"] = user
        session.save()

        csv_res = self.client.get(export_url)
        self.assertEqual(csv_res.status_code, 200)
        self.assertTrue(csv_res["Content-Type"].startswith("text/csv"))
        self.assertIn("lantawires_dispatches_report.csv", csv_res["Content-Disposition"])
        body = csv_res.content.decode("utf-8")
        self.assertIn("Dispatch ID,Ticket Number,Incident Title", body)
        self.assertIn("LW-CSV-0001", body)
        self.assertIn("LW-CSV-0002", body)

        filtered_res = self.client.get(f"{export_url}?status=Resolved")
        filtered_body = filtered_res.content.decode("utf-8")
        self.assertNotIn("LW-CSV-0001", filtered_body)
        self.assertIn("LW-CSV-0002", filtered_body)

    def test_dispatches_page_renders_multi_agency_form_filters_and_export(self):
        from apps.home.models import HazardCategory, HazardReport, UtilityAgency
        from apps.profile.models import CebuBarangay

        brgy = CebuBarangay.objects.create(
            name="Tisa", district="South District", zip_code="6000", center_lat=10.2982, center_lng=123.8741
        )
        cat = HazardCategory.objects.create(
            code="SAGGING_CABLE", category_name="Sagging Overhead Cable", min_clearance=4.5, default_severity="critical"
        )
        HazardReport.objects.create(
            ticket_number="LW-UI-0001", title="Open Wire", barangay=brgy, category=cat, address="Tisa St.", status="dispatched"
        )
        UtilityAgency.objects.create(
            agency_name="Cebu City TIC", department="Task Force", contact_email="tic@test.ph", hotline_number="411", agency_type="LGU"
        )
        UtilityAgency.objects.create(
            agency_name="Globe Telecom", department="Wire Retrieval", contact_email="globe@test.ph", hotline_number="211", agency_type="Telco"
        )

        session = self.client.session
        user = dict(session["current_user"])
        user["role"] = "resolver"
        session["current_user"] = user
        session.save()

        res = self.client.get(reverse("home:dispatches"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "export-dispatches-csv-btn")
        self.assertContains(res, "new-dispatch-report-select")
        self.assertContains(res, "new-dispatch-agency-select")
        self.assertContains(res, "Globe Telecom")

    def test_logout_clears_session_and_redirects_to_login(self):
        response = self.client.get(reverse("home:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:index"))
        self.assertNotIn("current_user", self.client.session)
