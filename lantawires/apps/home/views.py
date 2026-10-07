import json
import time
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .data import CEBU_BARANGAYS, INITIAL_REPORTS, SAMPLE_HAZARD_PRESETS
from .models import HazardCategory, HazardReport

HAZARD_TYPE_TO_CATEGORY = {
    "sagging_cable": "SAGGING_CABLE",
    "low_clearance": "LOW_CLEARANCE",
    "spaghetti_cluster": "TANGLED_SPAGHETTI",
    "broken_pole": "FALLEN_POLE_LINE",
    "transformer_spark": "BURNING_SPARKING",
}

DEFAULT_GUEST = {
    "id": "usr-01",
    "name": "Gianne Cruz",
    "email": "gianne@cebucity.ph",
    "phone": "+63 917 554 8921",
    "barangay": "Tisa",
    "avatar": "GC",
}

def get_session_reports(request):
    custom_reports = request.session.get("custom_reports", [])
    
    # Also fetch database reports if any
    db_reports = []
    try:
        for r in HazardReport.objects.select_related("barangay", "reporter", "category").all():
            barangay_name = r.barangay.name if r.barangay_id else "Tisa"
            reporter_name = (
                r.reporter.get_full_name() or r.reporter.username
                if r.reporter_id
                else "Citizen Reporter"
            )
            db_reports.append({
                "id": f"rep-db-{r.id}",
                "ticketNumber": r.ticket_number,
                "title": r.title,
                "barangay": barangay_name,
                "address": r.address,
                "gpsCoordinates": {"lat": r.latitude, "lng": r.longitude},
                "severity": r.severity,
                "status": r.status,
                "reportedAt": r.created_at.strftime("%b %d, %Y"),
                "imageUrl": r.image_url or "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80",
                "reporterName": reporter_name,
                "clearanceHeightMeters": r.clearance_meters,
                "hazardType": r.hazard_type,
                "affectedAgencies": ["Cebu City TIC", "Visayan Electric (VECO)", "Telco Response Unit"],
                "aiAnalysis": {
                    "confidence": r.confidence_score,
                    "cableSagClearance": f"{r.clearance_meters}m clearance",
                    "wireDensityScore": "High (Overlapping bundles)",
                    "detectedComponents": ["Sagging drop wire", "Power bundle snag"],
                    "severityRating": r.severity,
                    "recommendedAction": "Field team dispatch for cable tensioning.",
                    "safetyWarning": "Immediate danger to tall motor vehicles and neighborhood safety.",
                    "isValidHazard": True,
                },
                "dispatchDetails": {
                    "dispatchTimestamp": r.created_at.strftime("%b %d, %Y %I:%M %p"),
                    "dispatchTurnaroundSeconds": 30,
                    "recipients": [
                        {"agency": "Cebu City Technical Infrastructure Committee (TIC)", "department": "Spaghetti Wire Eradication Task Force", "email": "tic-dispatch@cebucity.gov.ph", "status": "Delivered", "dispatchedAt": "Immediate"},
                        {"agency": "Visayan Electric (VECO)", "department": "Distribution Line Safety Dispatch", "email": "emergency.hotline@veco.com.ph", "status": "Delivered", "dispatchedAt": "Immediate"}
                    ]
                }
            })
    except Exception:
        pass

    # Combine custom reports, db reports, and initial reports (avoiding ticket duplicates)
    seen_tickets = set()
    combined = []
    for r in custom_reports + db_reports + INITIAL_REPORTS:
        ticket = r.get("ticketNumber") or r.get("id")
        if ticket not in seen_tickets:
            seen_tickets.add(ticket)
            combined.append(r)
    return combined

def home_view(request):
    current_user = request.session.get("current_user")
    if not current_user and request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        profile_barangay = (
            profile.barangay.name if profile and profile.barangay_id else "Tisa"
        )
        current_user = {
            "id": f"usr-{request.user.id:04d}",
            "name": profile.full_name if profile and profile.full_name else (request.user.get_full_name() or request.user.username),
            "email": request.user.email,
            "phone": profile.phone if profile else "+63 917 000 0000",
            "barangay": profile_barangay,
            "avatar": profile.avatar if profile and profile.avatar else (request.user.first_name[:2].upper() or "LW"),
            "role": getattr(profile, "role", "citizen") or "citizen",
        }
        request.session["current_user"] = current_user
        request.session.save()

    if not current_user and not request.user.is_authenticated:
        messages.warning(request, "Please log in to access the home screen.")
        return redirect("login:login")

    role = (current_user or {}).get("role", "citizen")
    if role not in ("citizen", "resolver") and request.user.is_authenticated:
        try:
            role = request.user.profile.role
            current_user["role"] = role
            request.session["current_user"] = current_user
        except Exception:
            role = "citizen"
    can_toggle = role == "resolver"

    reports = get_session_reports(request)

    total_verified = len(reports)
    critical_count = sum(1 for r in reports if r.get("severity") == "critical")
    dispatched_count = sum(1 for r in reports if r.get("status") == "dispatched")
    resolved_count = sum(1 for r in reports if r.get("status") == "resolved")

    stats = {
        "total": total_verified,
        "critical": critical_count,
        "dispatched": dispatched_count,
        "resolved": resolved_count,
    }

    context = {
        "current_user": current_user or DEFAULT_GUEST,
        "can_toggle": can_toggle,
        "reports": reports,
        "reports_json": json.dumps(reports),
        "barangays": CEBU_BARANGAYS,
        "presets": SAMPLE_HAZARD_PRESETS,
        "presets_json": json.dumps(SAMPLE_HAZARD_PRESETS),
        "stats": stats,
    }

    return render(request, "home/home.html", context)

def logout_view(request):
    logout(request)
    request.session.flush()
    messages.info(request, "You have been signed out successfully.")
    return redirect("login:login")

@require_POST
def create_report_api(request):
    try:
        data = json.loads(request.body)
        current_user = request.session.get("current_user", DEFAULT_GUEST)

        ticket_suffix = int(time.time()) % 10000
        ticket_number = f"LW-CEB-2026-{ticket_suffix:04d}"
        
        title = data.get("title", "Overhead Wire Hazard Incident")
        barangay = data.get("barangay", current_user.get("barangay", "Tisa"))
        address = data.get("address", "Cebu City Street Corridor")
        gps = data.get("gps", {"lat": 10.2982, "lng": 123.8741})
        severity = data.get("severity", "critical")
        status = "dispatched"
        image_url = data.get("imageUrl", "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80")
        reporter_name = current_user.get("name", "Citizen Reporter")
        clearance = float(data.get("clearanceHeightMeters", 3.0))
        confidence = float(data.get("confidence", 95.8))
        hazard_type = data.get("hazardType", "sagging_cable")

        # Persist directly into Supabase PostgreSQL (ERD: home_hazardreport
        # with FKs to auth_user, cebu_barangays, hazard_categories)
        try:
            from apps.profile.models import CebuBarangay

            barangay_obj, _ = CebuBarangay.objects.get_or_create(
                name=barangay,
                defaults={
                    "district": "South District",
                    "zip_code": "6000",
                    "center_lat": gps.get("lat", 10.2982),
                    "center_lng": gps.get("lng", 123.8741),
                },
            )
            category_code = HAZARD_TYPE_TO_CATEGORY.get(hazard_type, "SAGGING_CABLE")
            category_obj, _ = HazardCategory.objects.get_or_create(
                code=category_code,
                defaults={
                    "category_name": hazard_type.replace("_", " ").title(),
                    "min_clearance": 4.0,
                    "default_severity": severity,
                },
            )
            reporter_user = (
                request.user if request.user.is_authenticated else None
            )
            HazardReport.objects.create(
                ticket_number=ticket_number,
                title=title,
                reporter=reporter_user,
                barangay=barangay_obj,
                category=category_obj,
                address=address,
                latitude=gps.get("lat", 10.2982),
                longitude=gps.get("lng", 123.8741),
                severity=severity,
                status=status,
                hazard_type=hazard_type,
                clearance_meters=clearance,
                confidence_score=confidence,
                image_url=image_url,
            )
        except Exception as db_err:
            print("Database persistence warning:", db_err)

        new_report = {
            "id": f"rep-{int(time.time())}",
            "ticketNumber": ticket_number,
            "title": title,
            "barangay": barangay,
            "address": address,
            "gpsCoordinates": gps,
            "severity": severity,
            "status": status,
            "reportedAt": "Just now",
            "imageUrl": image_url,
            "reporterName": reporter_name,
            "clearanceHeightMeters": clearance,
            "hazardType": hazard_type,
            "affectedAgencies": ["Cebu City TIC", "Visayan Electric (VECO)", "Telco Response Unit"],
            "aiAnalysis": {
                "confidence": confidence,
                "cableSagClearance": data.get("sagClearance", f"{clearance}m clearance"),
                "wireDensityScore": data.get("wireDensity", "High (Overlapping bundles)"),
                "detectedComponents": data.get("components", ["Sagging drop wire", "Splice bundle snag"]),
                "severityRating": severity,
                "recommendedAction": "Emergency bucket truck dispatch for cable re-tensioning and bundle elevation.",
                "safetyWarning": "Immediate danger to tall motor vehicles and neighborhood safety.",
                "isValidHazard": True,
            },
            "dispatchDetails": {
                "dispatchTimestamp": "Just now (Automated Engine)",
                "dispatchTurnaroundSeconds": 32,
                "recipients": [
                    {
                        "agency": "Cebu City Technical Infrastructure Committee (TIC)",
                        "department": "Spaghetti Wire Eradication Task Force",
                        "email": "tic-dispatch@cebucity.gov.ph",
                        "status": "Delivered",
                        "dispatchedAt": "Immediate",
                    },
                    {
                        "agency": "Visayan Electric (VECO)",
                        "department": "Distribution Line Safety Dispatch",
                        "email": "emergency.hotline@veco.com.ph",
                        "status": "Delivered",
                        "dispatchedAt": "Immediate",
                    },
                ],
            },
        }

        custom_reports = request.session.get("custom_reports", [])
        custom_reports.insert(0, new_report)
        request.session["custom_reports"] = custom_reports
        request.session.modified = True

        return JsonResponse({"status": "ok", "report": new_report})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

@require_POST
def update_status_api(request):
    def _is_resolver():
        sess_role = (request.session.get("current_user") or {}).get("role")
        if sess_role == "resolver":
            return True
        if request.user.is_authenticated:
            try:
                return request.user.profile.role == "resolver"
            except Exception:
                return False
        return False

    if not _is_resolver():
        return JsonResponse({"status": "error", "message": "Resolver role required."}, status=403)

    try:
        data = json.loads(request.body)
        report_id = data.get("reportId")
        new_status = data.get("newStatus")

        # Update in database if exists
        try:
            HazardReport.objects.filter(ticket_number=report_id).update(status=new_status)
        except Exception:
            pass

        custom_reports = request.session.get("custom_reports", [])
        updated = False
        for rep in custom_reports:
            if rep["id"] == report_id or rep.get("ticketNumber") == report_id:
                rep["status"] = new_status
                updated = True
                break

        if not updated:
            for rep in INITIAL_REPORTS:
                if rep["id"] == report_id or rep.get("ticketNumber") == report_id:
                    rep_copy = dict(rep)
                    rep_copy["status"] = new_status
                    custom_reports.insert(0, rep_copy)
                    updated = True
                    break

        request.session["custom_reports"] = custom_reports
        request.session.modified = True
        return JsonResponse({"status": "ok", "reportId": report_id, "newStatus": new_status})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
