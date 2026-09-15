import json
import time
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .data import CEBU_BARANGAYS, INITIAL_REPORTS, SAMPLE_HAZARD_PRESETS

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
    # Combine custom reports first (newest) followed by initial reports
    return custom_reports + INITIAL_REPORTS

def home_view(request):
    current_user = request.session.get("current_user")
    if not current_user:
        messages.warning(request, "Please log in to access the home screen.")
        return redirect("login:index")

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
        "current_user": current_user,
        "reports": reports,
        "reports_json": json.dumps(reports),
        "barangays": CEBU_BARANGAYS,
        "presets": SAMPLE_HAZARD_PRESETS,
        "presets_json": json.dumps(SAMPLE_HAZARD_PRESETS),
        "stats": stats,
    }

    return render(request, "home/home.html", context)

def logout_view(request):
    request.session.flush()
    messages.info(request, "You have been signed out successfully.")
    return redirect("login:index")

@require_POST
def create_report_api(request):
    try:
        data = json.loads(request.body)
        current_user = request.session.get("current_user", DEFAULT_GUEST)

        ticket_suffix = int(time.time()) % 10000
        new_report = {
            "id": f"rep-{int(time.time())}",
            "ticketNumber": f"LW-CEB-2026-{ticket_suffix:04d}",
            "title": data.get("title", "Overhead Wire Hazard Incident"),
            "barangay": data.get("barangay", current_user.get("barangay", "Tisa")),
            "address": data.get("address", "Cebu City Street Corridor"),
            "gpsCoordinates": data.get("gps", {"lat": 10.2982, "lng": 123.8741}),
            "severity": data.get("severity", "critical"),
            "status": "dispatched",
            "reportedAt": "Just now",
            "imageUrl": data.get("imageUrl", "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80"),
            "reporterName": current_user.get("name", "Citizen Reporter"),
            "clearanceHeightMeters": data.get("clearanceHeightMeters", 3.0),
            "hazardType": data.get("hazardType", "sagging_cable"),
            "affectedAgencies": ["Cebu City TIC", "Visayan Electric (VECO)", "Telco Response Unit"],
            "aiAnalysis": {
                "confidence": float(data.get("confidence", 95.8)),
                "cableSagClearance": data.get("sagClearance", "3.0m clearance (Non-compliant transit threshold)"),
                "wireDensityScore": data.get("wireDensity", "High (Overlapping bundles)"),
                "detectedComponents": data.get("components", ["Sagging drop wire", "Splice bundle snag"]),
                "severityRating": data.get("severity", "critical"),
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
    try:
        data = json.loads(request.body)
        report_id = data.get("reportId")
        new_status = data.get("newStatus")

        custom_reports = request.session.get("custom_reports", [])
        updated = False
        for rep in custom_reports:
            if rep["id"] == report_id:
                rep["status"] = new_status
                updated = True
                break

        if not updated:
            # Check in initial reports
            for rep in INITIAL_REPORTS:
                if rep["id"] == report_id:
                    # Clone to custom reports with new status
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
