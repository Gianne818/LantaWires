import base64
import csv
import json
import re
import time
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Subquery
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .data import CEBU_BARANGAYS, INITIAL_REPORTS, SAMPLE_HAZARD_PRESETS
from .models import (
    AIHazardAnalysis,
    HazardCategory,
    HazardDispatch,
    HazardReport,
    UtilityAgency,
)
from apps.profile.models import CebuBarangay

HAZARD_TYPE_TO_CATEGORY = {
    "sagging_cable": "SAGGING_CABLE",
    "low_clearance": "LOW_CLEARANCE",
    "spaghetti_cluster": "TANGLED_SPAGHETTI",
    "broken_pole": "FALLEN_POLE_LINE",
    "transformer_spark": "BURNING_SPARKING",
}

CATEGORY_CODE_TO_TYPE = {v: k for k, v in HAZARD_TYPE_TO_CATEGORY.items()}

VALID_SEVERITIES = ("critical", "high", "medium", "low")

DEFAULT_HAZARD_CATEGORIES = [
    {"type": "sagging_cable", "code": "SAGGING_CABLE", "name": "Sagging Overhead Cable", "min_clearance": 4.5, "default_severity": "critical"},
    {"type": "low_clearance", "code": "LOW_CLEARANCE", "name": "Dangerous Low Clearance", "min_clearance": 4.5, "default_severity": "critical"},
    {"type": "spaghetti_cluster", "code": "TANGLED_SPAGHETTI", "name": "Overcrowded Spaghetti Cluster", "min_clearance": 4.0, "default_severity": "high"},
    {"type": "broken_pole", "code": "FALLEN_POLE_LINE", "name": "Deflected Pole / Downed Line", "min_clearance": 5.0, "default_severity": "high"},
    {"type": "transformer_spark", "code": "BURNING_SPARKING", "name": "Transformer Arcing / Fire Hazard", "min_clearance": 5.5, "default_severity": "critical"},
]


def _get_hazard_categories_context():
    """Return active HazardCategory options for report creation/editing forms."""
    try:
        rows = list(HazardCategory.objects.all())
    except Exception:
        rows = []
    if not rows:
        return DEFAULT_HAZARD_CATEGORIES
    return [
        {
            "type": CATEGORY_CODE_TO_TYPE.get(c.code, "sagging_cable"),
            "code": c.code,
            "name": c.category_name,
            "min_clearance": c.min_clearance,
            "default_severity": c.default_severity,
        }
        for c in rows
    ]

DEFAULT_GUEST = {
    "id": "usr-01",
    "name": "Gianne Cruz",
    "email": "gianne@cebucity.ph",
    "phone": "+63 917 554 8921",
    "barangay": "Tisa",
    "avatar": "GC",
}

DEFAULT_HAZARD_IMAGE_URL = "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80"

_IMAGE_EXT_MAP = {
    "jpeg": "jpg",
    "jpg": "jpg",
    "png": "png",
    "webp": "webp",
    "gif": "gif",
}


def _persist_hazard_image(raw_image_url, ticket_number):
    """Persist base64 data URLs under MEDIA_ROOT/hazards/ so image_url fits VARCHAR(500)."""
    if not raw_image_url or not isinstance(raw_image_url, str):
        return DEFAULT_HAZARD_IMAGE_URL

    raw_image_url = raw_image_url.strip()
    if raw_image_url.startswith("data:image/"):
        match = re.match(
            r"^data:image/([a-zA-Z0-9.+-]+);base64,(.+)$",
            raw_image_url,
            re.DOTALL,
        )
        if not match:
            return DEFAULT_HAZARD_IMAGE_URL
        subtype = match.group(1).lower()
        b64_payload = match.group(2).strip()
        ext = _IMAGE_EXT_MAP.get(subtype, "jpg")
        try:
            image_bytes = base64.b64decode(b64_payload, validate=True)
            if not image_bytes or len(image_bytes) > 10 * 1024 * 1024:
                return DEFAULT_HAZARD_IMAGE_URL
            safe_ticket = re.sub(r"[^A-Za-z0-9_-]", "", ticket_number) or "hazard"
            filename = f"{safe_ticket}-{uuid.uuid4().hex[:6]}.{ext}"
            hazards_dir = Path(settings.MEDIA_ROOT) / "hazards"
            hazards_dir.mkdir(parents=True, exist_ok=True)
            (hazards_dir / filename).write_bytes(image_bytes)
            media_prefix = (settings.MEDIA_URL or "/media/").rstrip("/")
            return f"{media_prefix}/hazards/{filename}"
        except (ValueError, OSError):
            return DEFAULT_HAZARD_IMAGE_URL

    if raw_image_url.startswith(("http://", "https://", "/media/", "/static/")) and len(raw_image_url) <= 500:
        return raw_image_url

    return DEFAULT_HAZARD_IMAGE_URL


def _report_belongs_to_user(report, request, user_obj):
    """Match report ownership by reporter FK ID, then email, then display name fallback."""
    if request.user.is_authenticated and report.get("reporterId") is not None:
        return report["reporterId"] == request.user.id

    user_email = ((user_obj or {}).get("email") or "").strip().lower()
    report_email = (report.get("reporterEmail") or "").strip().lower()
    if user_email and report_email:
        return report_email == user_email

    user_name = ((user_obj or {}).get("name") or "").strip().lower()
    return bool(user_name) and (report.get("reporterName") or "").strip().lower() == user_name


def _serialize_db_report(r):
    """Serialize a HazardReport ORM instance (with related AI & dispatches) to frontend JSON."""
    barangay_name = r.barangay.name if r.barangay_id else "Tisa"
    if r.reporter_id:
        reporter_profile = getattr(r.reporter, "profile", None)
        reporter_name = (
            (reporter_profile.full_name if reporter_profile and reporter_profile.full_name else "")
            or r.reporter.get_full_name()
            or r.reporter.username
        )
        reporter_email = (r.reporter.email or "").strip().lower()
    else:
        reporter_name = "Citizen Reporter"
        reporter_email = ""

    ai_obj = getattr(r, "ai_analysis", None)
    components = (
        [c.strip() for c in ai_obj.detected_components.split(",") if c.strip()]
        if ai_obj and ai_obj.detected_components
        else ["Sagging drop wire", "Power bundle snag"]
    )
    confidence = ai_obj.confidence_score if ai_obj else r.confidence_score
    cable_sag = ai_obj.cable_sag_clearance if ai_obj else f"{r.clearance_meters}m clearance"
    wire_density = ai_obj.wire_density_score if ai_obj else "High (Overlapping bundles)"
    safety_warning = ai_obj.safety_warning if ai_obj else "Immediate danger to tall motor vehicles and neighborhood safety."
    rec_action = ai_obj.recommended_action if ai_obj else "Field team dispatch for cable tensioning."

    recipients = []
    for d in r.dispatches.all():
        recipients.append({
            "agency": d.agency.agency_name,
            "department": d.agency.department,
            "email": d.agency.contact_email,
            "status": d.delivery_status,
            "resolutionNotes": d.resolution_notes or "",
            "dispatchedAt": d.dispatched_at.strftime("%I:%M %p") if d.dispatched_at else "Immediate",
        })
    if not recipients:
        recipients = [
            {"agency": "Cebu City Technical Infrastructure Committee (TIC)", "department": "Spaghetti Wire Eradication Task Force", "email": "tic-dispatch@cebucity.gov.ph", "status": "Delivered", "resolutionNotes": "", "dispatchedAt": "Immediate"},
            {"agency": "Visayan Electric (VECO)", "department": "Distribution Line Safety Dispatch", "email": "emergency.hotline@veco.com.ph", "status": "Delivered", "resolutionNotes": "", "dispatchedAt": "Immediate"},
        ]

    return {
        "id": f"rep-db-{r.id}",
        "dbId": r.id,
        "ticketNumber": r.ticket_number,
        "title": r.title,
        "barangay": barangay_name,
        "address": r.address,
        "gpsCoordinates": {"lat": r.latitude, "lng": r.longitude},
        "severity": r.severity,
        "status": r.status,
        "reportedAt": r.created_at.strftime("%b %d, %Y"),
        "imageUrl": r.image_url or DEFAULT_HAZARD_IMAGE_URL,
        "reporterName": reporter_name,
        "reporterId": r.reporter_id,
        "reporterEmail": reporter_email,
        "clearanceHeightMeters": r.clearance_meters,
        "hazardType": r.hazard_type,
        "categoryName": r.category.category_name if r.category_id else "",
        "affectedAgencies": ["Cebu City TIC", "Visayan Electric (VECO)", "Telco Response Unit"],
        "aiAnalysis": {
            "confidence": confidence,
            "cableSagClearance": cable_sag,
            "wireDensityScore": wire_density,
            "detectedComponents": components,
            "severityRating": r.severity,
            "recommendedAction": rec_action,
            "safetyWarning": safety_warning,
            "isValidHazard": True,
        },
        "dispatchDetails": {
            "dispatchTimestamp": r.created_at.strftime("%b %d, %Y %I:%M %p"),
            "dispatchTurnaroundSeconds": 30,
            "recipients": recipients,
        },
    }


def _can_manage_report(report_obj, request, user_obj, role):
    """Return (allowed, error_message) for editing or deleting a HazardReport."""
    if role == "resolver":
        return True, ""

    user_email = ((user_obj or {}).get("email") or "").strip().lower()
    report_email = (
        (report_obj.reporter.email or "").strip().lower()
        if report_obj.reporter_id
        else ""
    )
    owns_by_id = request.user.is_authenticated and report_obj.reporter_id == request.user.id
    owns_by_email = bool(user_email and report_email and user_email == report_email)
    if not (owns_by_id or owns_by_email):
        return False, "You can only modify reports you submitted."

    if report_obj.status == "resolved":
        return False, "Resolved reports can no longer be edited or withdrawn."

    return True, ""


def get_session_reports(request):
    custom_reports = request.session.get("custom_reports", [])
    
    # Also fetch database reports from Supabase PostgreSQL (CRUZ_ERD: home_hazardreport, ai_hazard_analyses, hazard_dispatches)
    db_reports = []
    try:
        for r in HazardReport.objects.select_related("barangay", "reporter", "reporter__profile", "category").prefetch_related("dispatches__agency").all():
            db_reports.append(_serialize_db_report(r))
    except Exception as e:
        print("Error fetching database reports:", e)

    # Combine db reports first so live DB state takes precedence over stale session entries
    seen_tickets = set()
    combined = []
    for r in db_reports + custom_reports + INITIAL_REPORTS:
        ticket = r.get("ticketNumber") or r.get("id")
        if ticket not in seen_tickets:
            seen_tickets.add(ticket)
            combined.append(r)
    return combined

def _resolve_session_user(request):
    """Return (current_user_dict, role) from session or authenticated User, or (None, None)."""
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
        return None, None

    role = (current_user or {}).get("role")
    if role not in ("citizen", "resolver"):
        if request.user.is_authenticated:
            try:
                role = request.user.profile.role
                current_user["role"] = role
                request.session["current_user"] = current_user
            except Exception:
                role = "citizen"
        else:
            role = "citizen"

    return current_user or DEFAULT_GUEST, role


def home_view(request):
    user_obj, role = _resolve_session_user(request)
    if user_obj is None:
        messages.warning(request, "Please log in to access the home screen.")
        return redirect("login:login")

    is_resolver = role == "resolver"
    can_toggle = is_resolver

    reports = get_session_reports(request)
    user_name = (user_obj.get("name") or "").strip().lower()
    user_barangay = (user_obj.get("barangay") or "Tisa").strip().lower()

    total_verified = len(reports)
    critical_count = sum(1 for r in reports if r.get("severity") == "critical")
    dispatched_count = sum(1 for r in reports if r.get("status") == "dispatched")
    investigating_count = sum(1 for r in reports if r.get("status") == "investigating")
    resolved_count = sum(1 for r in reports if r.get("status") == "resolved")

    stats = {
        "total": total_verified,
        "critical": critical_count,
        "dispatched": dispatched_count,
        "investigating": investigating_count,
        "resolved": resolved_count,
    }

    citizen_stats = {
        "my_reports": sum(
            1 for r in reports if _report_belongs_to_user(r, request, user_obj)
        ),
        "barangay_active": sum(
            1
            for r in reports
            if (r.get("barangay") or "").strip().lower() == user_barangay
            and r.get("status") != "resolved"
        ),
        "barangay_critical": sum(
            1
            for r in reports
            if (r.get("barangay") or "").strip().lower() == user_barangay
            and r.get("severity") == "critical"
            and r.get("status") != "resolved"
        ),
        "city_resolved": resolved_count,
    }

    hazard_categories = _get_hazard_categories_context()
    context = {
        "current_user": user_obj,
        "current_user_id": request.user.id if request.user.is_authenticated else "",
        "is_resolver": is_resolver,
        "can_toggle": can_toggle,
        "reports": reports,
        "reports_json": json.dumps(reports),
        "barangays": list(CebuBarangay.objects.values_list("name", flat=True)) or CEBU_BARANGAYS,
        "hazard_categories": hazard_categories,
        "hazard_categories_json": json.dumps(hazard_categories),
        "presets": SAMPLE_HAZARD_PRESETS,
        "presets_json": json.dumps(SAMPLE_HAZARD_PRESETS),
        "stats": stats,
        "citizen_stats": citizen_stats,
    }

    return render(request, "home/home.html", context)


def my_reports_view(request):
    """Citizen-focused view showing reports submitted by the logged-in user."""
    user_obj, role = _resolve_session_user(request)
    if user_obj is None:
        messages.warning(request, "Please log in to view your reports.")
        return redirect("login:login")

    is_resolver = role == "resolver"
    reports = get_session_reports(request)
    my_reports = [
        r for r in reports if _report_belongs_to_user(r, request, user_obj)
    ]

    my_stats = {
        "total": len(my_reports),
        "dispatched": sum(1 for r in my_reports if r.get("status") == "dispatched"),
        "investigating": sum(1 for r in my_reports if r.get("status") == "investigating"),
        "resolved": sum(1 for r in my_reports if r.get("status") == "resolved"),
    }

    return render(
        request,
        "home/my_reports.html",
        {
            "current_user": user_obj,
            "is_resolver": is_resolver,
            "my_reports": my_reports,
            "my_reports_json": json.dumps(my_reports),
            "my_stats": my_stats,
            "barangays": list(CebuBarangay.objects.values_list("name", flat=True)) or CEBU_BARANGAYS,
            "hazard_categories": _get_hazard_categories_context(),
        },
    )


def dispatches_view(request):
    """Resolver-only console for utility agency dispatches and barangay hazard analytics."""
    user_obj, role = _resolve_session_user(request)
    if user_obj is None:
        messages.warning(request, "Please log in to access the dispatches console.")
        return redirect("login:login")

    if role != "resolver":
        messages.warning(request, "Dispatches console is restricted to resolver accounts.")
        return redirect("home:home")

    reports = get_session_reports(request)

    agencies = list(UtilityAgency.objects.all())
    if not agencies:
        agencies = [
            {
                "agency_name": "Cebu City Technical Infrastructure Committee (TIC)",
                "department": "Spaghetti Wire Eradication Task Force",
                "contact_email": "tic-dispatch@cebucity.gov.ph",
                "hotline_number": "(032) 411-0115",
                "agency_type": "LGU",
            },
            {
                "agency_name": "Visayan Electric (VECO)",
                "department": "Distribution Line Safety Dispatch",
                "contact_email": "emergency.hotline@veco.com.ph",
                "hotline_number": "(032) 230-8326",
                "agency_type": "Power",
            },
        ]

    dispatches = list(
        HazardDispatch.objects.select_related("report", "report__barangay", "agency")
        .order_by("-dispatched_at")[:50]
    )
    db_agencies = list(UtilityAgency.objects.all())
    open_db_reports = list(
        HazardReport.objects.select_related("barangay")
        .exclude(status="resolved")
        .order_by("-created_at")
    )
    
    active_hazard_barangay_ids = (
        HazardReport.objects.exclude(status="resolved").values("barangay_id")
    )
    active_hotspot_barangays = list(
        CebuBarangay.objects.filter(
            id__in=Subquery(active_hazard_barangay_ids)
        ).order_by("name")
    )
    total_barangays_count = CebuBarangay.objects.count()

    # Barangay breakdown computed from live reports list
    barangay_map = {}
    for r in reports:
        brgy = r.get("barangay") or "Tisa"
        entry = barangay_map.setdefault(
            brgy, {"name": brgy, "total": 0, "critical": 0, "active": 0, "resolved": 0}
        )
        entry["total"] += 1
        if r.get("severity") == "critical":
            entry["critical"] += 1
        if r.get("status") == "resolved":
            entry["resolved"] += 1
        else:
            entry["active"] += 1

    barangay_breakdown = sorted(
        barangay_map.values(), key=lambda item: (item["active"], item["total"]), reverse=True
    )
    max_brgy_total = max((item["total"] for item in barangay_breakdown), default=1) or 1
    for item in barangay_breakdown:
        item["width_pct"] = max(12, round((item["total"] / max_brgy_total) * 100))

    dispatch_stats = {
        "total_dispatches": len(dispatches) or sum(
            len(r.get("dispatchDetails", {}).get("recipients", [])) for r in reports
        ),
        "agencies_count": len(agencies),
        "open_incidents": sum(1 for r in reports if r.get("status") != "resolved"),
        "resolved_incidents": sum(1 for r in reports if r.get("status") == "resolved"),
    }

    return render(
        request,
        "home/dispatches.html",
        {
            "current_user": user_obj,
            "is_resolver": True,
            "agencies": agencies,
            "db_agencies": db_agencies,
            "open_db_reports": open_db_reports,
            "delivery_statuses": ["Delivered", "Acknowledged", "En Route", "Resolved", "Failed"],
            "dispatches": dispatches,
            "active_hotspot_barangays": active_hotspot_barangays,
            "total_barangays_count": total_barangays_count,
            "fallback_reports": reports[:10],
            "barangay_breakdown": barangay_breakdown,
            "dispatch_stats": dispatch_stats,
        },
    )

def logout_view(request):
    logout(request)
    request.session.flush()
    messages.info(request, "You have been signed out successfully.")
    return redirect("login:login")

@require_POST
def create_report_api(request):
    current_user, _ = _resolve_session_user(request)
    if current_user is None:
        return JsonResponse(
            {"status": "error", "message": "Authentication required."},
            status=401,
        )

    try:
        data = json.loads(request.body)

        ticket_suffix = int(time.time()) % 10000
        ticket_number = f"LW-CEB-2026-{ticket_suffix:04d}"
        if HazardReport.objects.filter(ticket_number=ticket_number).exists():
            ticket_number = f"LW-CEB-2026-{uuid.uuid4().hex[:4].upper()}"
        
        title = (data.get("title") or "Overhead Wire Hazard Incident").strip()[:200] or "Overhead Wire Hazard Incident"
        barangay = (data.get("barangay") or current_user.get("barangay", "Tisa")).strip() or "Tisa"
        address = (data.get("address") or "Cebu City Street Corridor").strip()[:255] or "Cebu City Street Corridor"
        gps = data.get("gps") or {"lat": 10.2982, "lng": 123.8741}
        severity = data.get("severity", "critical")
        if severity not in VALID_SEVERITIES:
            severity = "critical"
        status = "dispatched"
        image_url = _persist_hazard_image(data.get("imageUrl"), ticket_number)
        reporter_name = current_user.get("name", "Citizen Reporter")
        try:
            clearance = max(0.5, min(15.0, float(data.get("clearanceHeightMeters", 3.0))))
        except (TypeError, ValueError):
            clearance = 3.0
        try:
            confidence = max(0.0, min(100.0, float(data.get("confidence", 95.8))))
        except (TypeError, ValueError):
            confidence = 95.8
        hazard_type = data.get("hazardType", "sagging_cable")
        if hazard_type not in HAZARD_TYPE_TO_CATEGORY:
            hazard_type = "sagging_cable"
        safety_warning = (data.get("safetyWarning") or "Immediate danger to tall motor vehicles and neighborhood safety.").strip()
        rec_action = (data.get("recommendedAction") or "Emergency bucket truck dispatch for cable re-tensioning and bundle elevation.").strip()

        # Persist directly into Supabase PostgreSQL (CRUZ_ERD: home_hazardreport, ai_hazard_analyses, hazard_dispatches)
        db_report_id = None
        try:
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

            # 1. Create HazardReport
            report_obj = HazardReport.objects.create(
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
            db_report_id = report_obj.id

            # 2. Create AIHazardAnalysis (CRUZ_ERD: ai_hazard_analyses)
            components_list = data.get("components") or ["Sagging drop wire", "Power bundle snag"]
            components_str = ", ".join(components_list) if isinstance(components_list, list) else str(components_list)
            sag_clearance = data.get("sagClearance") or f"{clearance}m clearance"
            wire_density = data.get("wireDensity") or "High (Overlapping bundles)"

            AIHazardAnalysis.objects.create(
                report=report_obj,
                confidence_score=confidence,
                detected_components=components_str,
                recommended_action=rec_action,
                safety_warning=safety_warning,
                is_valid_hazard=True,
                cable_sag_clearance=str(sag_clearance)[:100],
                wire_density_score=str(wire_density)[:50],
                severity_rating=str(severity)[:20],
            )

            # 3. Create HazardDispatch entries (CRUZ_ERD: hazard_dispatches & utility_agencies)
            tic_agency, _ = UtilityAgency.objects.get_or_create(
                agency_name="Cebu City Technical Infrastructure Committee (TIC)",
                defaults={
                    "department": "Spaghetti Wire Eradication Task Force",
                    "contact_email": "tic-dispatch@cebucity.gov.ph",
                    "hotline_number": "(032) 411-0115",
                    "agency_type": "LGU",
                },
            )
            veco_agency, _ = UtilityAgency.objects.get_or_create(
                agency_name="Visayan Electric (VECO)",
                defaults={
                    "department": "Distribution Line Safety Dispatch",
                    "contact_email": "emergency.hotline@veco.com.ph",
                    "hotline_number": "(032) 230-8326",
                    "agency_type": "Power",
                },
            )

            HazardDispatch.objects.create(
                report=report_obj,
                agency=tic_agency,
                turnaround_seconds=30,
                delivery_status="Delivered",
                resolution_notes="Automated dispatch sent to LGU Spaghetti Wire Task Force",
            )
            HazardDispatch.objects.create(
                report=report_obj,
                agency=veco_agency,
                turnaround_seconds=32,
                delivery_status="Delivered",
                resolution_notes="Automated emergency dispatch sent to VECO distribution safety crew",
            )
        except Exception as db_err:
            print("Database persistence warning:", db_err)

        new_report = {
            "id": f"rep-db-{db_report_id}" if db_report_id else f"rep-{int(time.time())}",
            "dbId": db_report_id,
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
            "reporterId": request.user.id if request.user.is_authenticated else None,
            "reporterEmail": (current_user.get("email") or "").strip().lower(),
            "clearanceHeightMeters": clearance,
            "hazardType": hazard_type,
            "affectedAgencies": ["Cebu City TIC", "Visayan Electric (VECO)", "Telco Response Unit"],
            "aiAnalysis": {
                "confidence": confidence,
                "cableSagClearance": data.get("sagClearance", f"{clearance}m clearance"),
                "wireDensityScore": data.get("wireDensity", "High (Overlapping bundles)"),
                "detectedComponents": data.get("components", ["Sagging drop wire", "Splice bundle snag"]),
                "severityRating": severity,
                "recommendedAction": rec_action,
                "safetyWarning": safety_warning,
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

        if db_report_id is None:
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

        valid_statuses = ("dispatched", "investigating", "resolved")
        if new_status not in valid_statuses:
            return JsonResponse(
                {"status": "error", "message": "Invalid status value."}, status=400
            )

        dispatch_status_map = {
            "dispatched": "Delivered",
            "investigating": "En Route",
            "resolved": "Resolved",
        }

        # Update in database if exists (CRUZ_ERD: home_hazardreport & hazard_dispatches)
        try:
            report_qs = HazardReport.objects.filter(ticket_number=report_id)
            if not report_qs.exists() and str(report_id).startswith("rep-db-"):
                try:
                    db_id = int(str(report_id).replace("rep-db-", ""))
                    report_qs = HazardReport.objects.filter(id=db_id)
                except ValueError:
                    pass
            report_qs.update(status=new_status)
            for rep in report_qs:
                HazardDispatch.objects.filter(report=rep).update(
                    delivery_status=dispatch_status_map[new_status]
                )
        except Exception as e:
            print("Database status update warning:", e)

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


@require_POST
def update_dispatch_api(request):
    """Resolver-only API to update a HazardDispatch delivery status and resolution notes."""
    _, role = _resolve_session_user(request)
    if role != "resolver":
        return JsonResponse({"status": "error", "message": "Resolver role required."}, status=403)

    try:
        data = json.loads(request.body)
        dispatch_id = data.get("dispatchId")
        delivery_status = data.get("deliveryStatus")
        resolution_notes = (data.get("resolutionNotes") or "").strip()

        valid_delivery = ("Delivered", "Acknowledged", "En Route", "Resolved", "Failed")
        if delivery_status not in valid_delivery:
            return JsonResponse({"status": "error", "message": "Invalid delivery status."}, status=400)

        dispatch_obj = HazardDispatch.objects.select_related("report").filter(id=dispatch_id).first()
        if not dispatch_obj:
            return JsonResponse({"status": "error", "message": "Dispatch record not found."}, status=404)

        dispatch_obj.delivery_status = delivery_status
        if resolution_notes:
            dispatch_obj.resolution_notes = resolution_notes
        if delivery_status in ("Acknowledged", "En Route", "Resolved") and not dispatch_obj.acknowledged_at:
            dispatch_obj.acknowledged_at = timezone.now()
        dispatch_obj.save()

        # Sync parent HazardReport status cleanly
        report = dispatch_obj.report
        if delivery_status == "En Route" and report.status == "dispatched":
            report.status = "investigating"
            report.save(update_fields=["status", "updated_at"])
        elif delivery_status == "Resolved":
            remaining_open = HazardDispatch.objects.filter(report=report).exclude(delivery_status="Resolved").exists()
            if not remaining_open:
                report.status = "resolved"
                report.save(update_fields=["status", "updated_at"])

        open_incidents = HazardReport.objects.exclude(status="resolved").count()
        resolved_incidents = HazardReport.objects.filter(status="resolved").count()
        active_hotspot_count = CebuBarangay.objects.filter(
            id__in=Subquery(
                HazardReport.objects.exclude(status="resolved").values("barangay_id")
            )
        ).count()

        return JsonResponse(
            {
                "status": "ok",
                "dispatchId": dispatch_obj.id,
                "deliveryStatus": dispatch_obj.delivery_status,
                "reportStatus": report.status,
                "resolutionNotes": dispatch_obj.resolution_notes or "",
                "openIncidents": open_incidents,
                "resolvedIncidents": resolved_incidents,
                "activeHotspotCount": active_hotspot_count,
            }
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


def _csv_safe(value):
    """Sanitize cell text against CSV formula injection and embedded newlines."""
    text = "" if value is None else str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    if text.startswith(("=", "+", "-", "@", "\t")):
        return "'" + text
    return text


@require_POST
def create_dispatch_api(request):
    """Resolver-only API to dispatch an open HazardReport to any UtilityAgency."""
    user_obj, role = _resolve_session_user(request)
    if user_obj is None:
        return JsonResponse({"status": "error", "message": "Authentication required."}, status=401)
    if role != "resolver":
        return JsonResponse({"status": "error", "message": "Resolver role required."}, status=403)

    try:
        data = json.loads(request.body)
        try:
            report_id = int(data.get("reportId"))
            agency_id = int(data.get("agencyId"))
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": "Valid report and agency IDs are required."}, status=400)

        resolution_notes = (data.get("resolutionNotes") or "").strip()

        report_obj = HazardReport.objects.select_related("barangay").filter(id=report_id).first()
        if not report_obj:
            return JsonResponse({"status": "error", "message": "Hazard report not found."}, status=404)

        agency_obj = UtilityAgency.objects.filter(id=agency_id).first()
        if not agency_obj:
            return JsonResponse({"status": "error", "message": "Utility agency not found."}, status=404)

        if HazardDispatch.objects.filter(report=report_obj, agency=agency_obj).exists():
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"{agency_obj.agency_name} is already dispatched to {report_obj.ticket_number}.",
                },
                status=409,
            )

        disp = HazardDispatch.objects.create(
            report=report_obj,
            agency=agency_obj,
            turnaround_seconds=28,
            delivery_status="Delivered",
            resolution_notes=resolution_notes or f"Manual resolver dispatch to {agency_obj.agency_name}",
        )

        return JsonResponse(
            {
                "status": "ok",
                "dispatch": {
                    "id": disp.id,
                    "ticketNumber": report_obj.ticket_number,
                    "reportTitle": report_obj.title,
                    "barangayName": report_obj.barangay.name,
                    "agencyId": agency_obj.id,
                    "agencyName": agency_obj.agency_name,
                    "turnaroundSeconds": disp.turnaround_seconds,
                    "deliveryStatus": disp.delivery_status,
                    "resolutionNotes": disp.resolution_notes or "",
                },
                "totalDispatches": HazardDispatch.objects.count(),
            },
            status=201,
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


def export_dispatches_csv(request):
    """Resolver-only CSV export of utility dispatch records joined across ERD tables."""
    user_obj, role = _resolve_session_user(request)
    if user_obj is None:
        messages.warning(request, "Please log in to export dispatch reports.")
        return redirect("login:login")
    if role != "resolver":
        messages.warning(request, "CSV export is restricted to resolver accounts.")
        return redirect("home:home")

    qs = HazardDispatch.objects.select_related(
        "report", "report__barangay", "report__category", "agency"
    ).order_by("-dispatched_at")

    agency_filter = (request.GET.get("agency") or "").strip()
    if agency_filter.isdigit():
        qs = qs.filter(agency_id=int(agency_filter))

    status_filter = (request.GET.get("status") or "").strip()
    valid_delivery = ("Delivered", "Acknowledged", "En Route", "Resolved", "Failed")
    if status_filter in valid_delivery:
        qs = qs.filter(delivery_status=status_filter)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="lantawires_dispatches_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Dispatch ID",
        "Ticket Number",
        "Incident Title",
        "Barangay",
        "District",
        "Category",
        "Severity",
        "Report Status",
        "Utility Agency",
        "Agency Type",
        "Delivery Status",
        "Turnaround (s)",
        "Dispatched At",
        "Resolution Notes",
    ])

    for d in qs:
        writer.writerow([
            d.id,
            _csv_safe(d.report.ticket_number),
            _csv_safe(d.report.title),
            _csv_safe(d.report.barangay.name if d.report.barangay_id else ""),
            _csv_safe(d.report.barangay.district if d.report.barangay_id else ""),
            _csv_safe(d.report.category.category_name if d.report.category_id else ""),
            _csv_safe(d.report.severity),
            _csv_safe(d.report.status),
            _csv_safe(d.agency.agency_name),
            _csv_safe(d.agency.agency_type),
            _csv_safe(d.delivery_status),
            d.turnaround_seconds,
            d.dispatched_at.strftime("%Y-%m-%d %H:%M:%S") if d.dispatched_at else "",
            _csv_safe(d.resolution_notes or ""),
        ])

    return response


@require_POST
def edit_report_api(request, report_id):
    """Allow report owner (while unresolved) or resolver to update a HazardReport."""
    current_user, role = _resolve_session_user(request)
    if current_user is None:
        return JsonResponse({"status": "error", "message": "Authentication required."}, status=401)

    report_obj = (
        HazardReport.objects.select_related("barangay", "reporter", "reporter__profile", "category")
        .prefetch_related("dispatches__agency")
        .filter(id=report_id)
        .first()
    )
    if not report_obj:
        return JsonResponse({"status": "error", "message": "Hazard report not found."}, status=404)

    allowed, reason = _can_manage_report(report_obj, request, current_user, role)
    if not allowed:
        return JsonResponse({"status": "error", "message": reason}, status=403)

    try:
        data = json.loads(request.body)

        if "title" in data:
            title = (data.get("title") or "").strip()
            if not title:
                return JsonResponse({"status": "error", "message": "Incident title cannot be empty."}, status=400)
            report_obj.title = title[:200]

        if "address" in data:
            address = (data.get("address") or "").strip()
            if not address:
                return JsonResponse({"status": "error", "message": "Street / landmark cannot be empty."}, status=400)
            report_obj.address = address[:255]

        if data.get("barangay"):
            barangay_name = str(data.get("barangay")).strip()
            if barangay_name:
                barangay_obj, _ = CebuBarangay.objects.get_or_create(
                    name=barangay_name,
                    defaults={
                        "district": "South District",
                        "zip_code": "6000",
                        "center_lat": report_obj.latitude,
                        "center_lng": report_obj.longitude,
                    },
                )
                report_obj.barangay = barangay_obj

        if data.get("hazardType"):
            hazard_type = str(data.get("hazardType")).strip()
            if hazard_type not in HAZARD_TYPE_TO_CATEGORY:
                return JsonResponse({"status": "error", "message": "Invalid hazard category."}, status=400)
            category_code = HAZARD_TYPE_TO_CATEGORY[hazard_type]
            category_obj, _ = HazardCategory.objects.get_or_create(
                code=category_code,
                defaults={
                    "category_name": hazard_type.replace("_", " ").title(),
                    "min_clearance": 4.0,
                    "default_severity": report_obj.severity,
                },
            )
            report_obj.hazard_type = hazard_type
            report_obj.category = category_obj

        if data.get("severity"):
            severity = str(data.get("severity")).strip()
            if severity not in VALID_SEVERITIES:
                return JsonResponse({"status": "error", "message": "Invalid severity value."}, status=400)
            report_obj.severity = severity

        if "clearanceHeightMeters" in data and data.get("clearanceHeightMeters") not in (None, ""):
            try:
                clearance = float(data.get("clearanceHeightMeters"))
            except (TypeError, ValueError):
                return JsonResponse({"status": "error", "message": "Clearance must be a valid number."}, status=400)
            if not (0.5 <= clearance <= 15.0):
                return JsonResponse({"status": "error", "message": "Clearance must be between 0.5m and 15.0m."}, status=400)
            report_obj.clearance_meters = round(clearance, 2)

        report_obj.save()

        ai_obj = getattr(report_obj, "ai_analysis", None)
        if ai_obj:
            ai_obj.severity_rating = report_obj.severity
            ai_obj.cable_sag_clearance = f"{report_obj.clearance_meters:.1f}m clearance"
            ai_obj.save(update_fields=["severity_rating", "cable_sag_clearance"])

        refreshed = (
            HazardReport.objects.select_related("barangay", "reporter", "reporter__profile", "category")
            .prefetch_related("dispatches__agency")
            .get(id=report_obj.id)
        )
        return JsonResponse({"status": "ok", "report": _serialize_db_report(refreshed)})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@require_POST
def delete_report_api(request, report_id):
    """Allow report owner (while unresolved) or resolver to delete/withdraw a HazardReport."""
    current_user, role = _resolve_session_user(request)
    if current_user is None:
        return JsonResponse({"status": "error", "message": "Authentication required."}, status=401)

    report_obj = HazardReport.objects.select_related("reporter").filter(id=report_id).first()
    if not report_obj:
        return JsonResponse({"status": "error", "message": "Hazard report not found."}, status=404)

    allowed, reason = _can_manage_report(report_obj, request, current_user, role)
    if not allowed:
        return JsonResponse({"status": "error", "message": reason}, status=403)

    ticket_number = report_obj.ticket_number
    deleted_id = report_obj.id
    report_obj.delete()

    custom_reports = request.session.get("custom_reports", [])
    if custom_reports:
        request.session["custom_reports"] = [
            r for r in custom_reports
            if r.get("ticketNumber") != ticket_number and r.get("dbId") != deleted_id
        ]
        request.session.modified = True

    return JsonResponse({"status": "ok", "deletedId": deleted_id, "ticketNumber": ticket_number})
