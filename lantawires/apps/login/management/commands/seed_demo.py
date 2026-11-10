import time
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.home.models import (
    AIHazardAnalysis,
    HazardCategory,
    HazardDispatch,
    HazardReport,
    UtilityAgency,
)
from apps.profile.models import CebuBarangay, Profile
from apps.user_settings.models import UserSettings

BARANGAYS_DATA = [
    {"name": "Tisa", "district": "South District", "lat": 10.2982, "lng": 123.8741, "hotline": "(032) 261-0412"},
    {"name": "Buhisan", "district": "South District", "lat": 10.2891, "lng": 123.8633, "hotline": "(032) 261-8891"},
    {"name": "Lahug", "district": "North District", "lat": 10.3298, "lng": 123.9056, "hotline": "(032) 231-1205"},
    {"name": "Guadalupe", "district": "South District", "lat": 10.3223, "lng": 123.8812, "hotline": "(032) 254-4411"},
    {"name": "Mabolo", "district": "North District", "lat": 10.3189, "lng": 123.9145, "hotline": "(032) 232-1980"},
    {"name": "Kasambagan", "district": "North District", "lat": 10.3242, "lng": 123.9118, "hotline": "(032) 233-0145"},
    {"name": "Banilad", "district": "North District", "lat": 10.3394, "lng": 123.9115, "hotline": "(032) 344-0981"},
    {"name": "Punta Princesa", "district": "South District", "lat": 10.2931, "lng": 123.8715, "hotline": "(032) 261-3312"},
    {"name": "Labangon", "district": "South District", "lat": 10.3015, "lng": 123.8802, "hotline": "(032) 261-7788"},
    {"name": "Sambag I", "district": "North District", "lat": 10.3105, "lng": 123.8901, "hotline": "(032) 253-1120"},
    {"name": "Sambag II", "district": "North District", "lat": 10.3135, "lng": 123.8925, "hotline": "(032) 253-1125"},
    {"name": "Talamban", "district": "North District", "lat": 10.3644, "lng": 123.9172, "hotline": "(032) 344-5501"},
    {"name": "Tejero", "district": "North District", "lat": 10.3038, "lng": 123.9082, "hotline": "(032) 232-4410"},
    {"name": "Pari-an", "district": "North District", "lat": 10.2995, "lng": 123.9038, "hotline": "(032) 255-0814"},
    {"name": "Carreta", "district": "North District", "lat": 10.3081, "lng": 123.9103, "hotline": "(032) 231-6022"},
    {"name": "San Nicolas Proper", "district": "South District", "lat": 10.2965, "lng": 123.8942, "hotline": "(032) 261-5509"},
    {"name": "Mambaling", "district": "South District", "lat": 10.2912, "lng": 123.8804, "hotline": "(032) 261-4401"},
    {"name": "Basak San Nicolas", "district": "South District", "lat": 10.2882, "lng": 123.8752, "hotline": "(032) 261-9988"},
    {"name": "Basak Pardo", "district": "South District", "lat": 10.2825, "lng": 123.8682, "hotline": "(032) 272-1100"},
    {"name": "Cogon Ramos", "district": "North District", "lat": 10.3115, "lng": 123.8975, "hotline": "(032) 254-8802"},
    {"name": "Capitol Site", "district": "North District", "lat": 10.3175, "lng": 123.8912, "hotline": "(032) 253-7744"},
    {"name": "Kamputhaw", "district": "North District", "lat": 10.3205, "lng": 123.8982, "hotline": "(032) 231-9905"},
    {"name": "Apas", "district": "North District", "lat": 10.3341, "lng": 123.9085, "hotline": "(032) 231-5511"},
]

AGENCIES_DATA = [
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
    {
        "agency_name": "PLDT-Smart Network Operations",
        "department": "Overhead Cable Maintenance & Bundling",
        "contact_email": "fieldops.cebu@pldt.com.ph",
        "hotline_number": "171",
        "agency_type": "Telco",
    },
    {
        "agency_name": "Globe Telecom Quick Response",
        "department": "Wire Elevation and Retrieval Unit",
        "contact_email": "wireclearance@globe.com.ph",
        "hotline_number": "211",
        "agency_type": "Telco",
    },
    {
        "agency_name": "Cebu City Disaster Risk Reduction Office (CCDRRMO)",
        "department": "Public Transit Corridor Safety",
        "contact_email": "ccdrmo@cebucity.gov.ph",
        "hotline_number": "(032) 262-1424",
        "agency_type": "LGU Emergency",
    },
]

CATEGORIES_DATA = [
    {"code": "SAGGING_CABLE", "name": "Sagging Overhead Cable", "min_clearance": 4.5, "severity": "critical"},
    {"code": "LOW_CLEARANCE", "name": "Dangerous Low Clearance", "min_clearance": 4.5, "severity": "critical"},
    {"code": "TANGLED_SPAGHETTI", "name": "Overcrowded Spaghetti Cluster", "min_clearance": 4.0, "severity": "high"},
    {"code": "FALLEN_POLE_LINE", "name": "Deflected Pole / Downed Line", "min_clearance": 5.0, "severity": "high"},
    {"code": "BURNING_SPARKING", "name": "Transformer Arcing / Fire Hazard", "min_clearance": 5.5, "severity": "critical"},
]

DEMO_USERS = [
    {
        "name": "Gianne Cruz",
        "email": "gianne@cebucity.ph",
        "phone": "+63 917 554 8921",
        "barangay": "Tisa",
        "avatar": "GC",
        "role": "resolver",
        "password": "cebuwirehazard2026",
    },
    {
        "name": "Eduardo Morales",
        "email": "morales.cebu@gmail.com",
        "phone": "+63 920 882 1042",
        "barangay": "Lahug",
        "avatar": "EM",
        "role": "citizen",
        "password": "cebuwirehazard2026",
    },
    {
        "name": "Lourdes Alcantara",
        "email": "lourdes.alcantara@yahoo.com",
        "phone": "+63 918 331 4455",
        "barangay": "Guadalupe",
        "avatar": "LA",
        "role": "citizen",
        "password": "cebuwirehazard2026",
    },
]

INITIAL_REPORTS_DATA = [
    {
        "ticket_number": "LW-CEB-2026-0841",
        "title": "Severe Tangled Cable Sagging into Jeepney Transit Lane",
        "barangay": "Tisa",
        "address": "F. Pacaña St. cor. Katipunan Extension, Brgy. Tisa",
        "lat": 10.2982,
        "lng": 123.8741,
        "severity": "critical",
        "status": "dispatched",
        "image_url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80",
        "clearance": 3.1,
        "category_code": "LOW_CLEARANCE",
        "hazard_type": "low_clearance",
        "confidence": 96.4,
        "components": "Heavy primary feeder cable sag, Dead telecom bundle loop, Vehicle catch hazard, High tension proximity",
        "wire_density": "Severe (42 overlapping active & dead cables)",
        "sag_clearance": "3.1m above asphalt (legal min: 4.5m for primary transit)",
        "warning": "Direct danger to heavy delivery trucks and public transit jeepneys.",
        "action": "Immediate utility bucket truck dispatch. Priority street cordon required.",
    },
    {
        "ticket_number": "LW-CEB-2026-0839",
        "title": "Dangling Spaghetti Bundle near Creek Residential Walkway",
        "barangay": "Buhisan",
        "address": "Sitio Lower Riverside, Brgy. Buhisan",
        "lat": 10.2891,
        "lng": 123.8633,
        "severity": "high",
        "status": "dispatched",
        "image_url": "https://images.unsplash.com/photo-1517420704952-d9f39e95b43e?auto=format&fit=crop&w=800&q=80",
        "clearance": 2.4,
        "category_code": "TANGLED_SPAGHETTI",
        "hazard_type": "spaghetti_cluster",
        "confidence": 93.8,
        "components": "Exposed splice box with wire exposure, Proximity to corrugated metal roofing, Pedestrian reach zone",
        "wire_density": "High (31 tangled telephone/cable loops)",
        "sag_clearance": "2.4m above concrete path",
        "warning": "Electrocution risk during monsoon rain runoff.",
        "action": "Cut and bundle operation by maintenance response crew.",
    },
    {
        "ticket_number": "LW-CEB-2026-0835",
        "title": "Cracked Wooden Pole with Overburdened Telecom Spool",
        "barangay": "Lahug",
        "address": "Salinas Drive near IT Park Access, Brgy. Lahug",
        "lat": 10.3298,
        "lng": 123.9056,
        "severity": "high",
        "status": "dispatched",
        "image_url": "https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?auto=format&fit=crop&w=800&q=80",
        "clearance": 3.8,
        "category_code": "FALLEN_POLE_LINE",
        "hazard_type": "broken_pole",
        "confidence": 91.2,
        "components": "Pole structural deflection > 12 degrees, Overweight bundle pulling anchor line, Secondary drop wire abrasion",
        "wire_density": "Severe (50+ fiber optic & coaxial lines)",
        "sag_clearance": "3.8m above curb",
        "warning": "Structural collapse risk under high wind pressure.",
        "action": "Emergency pole reinforcement and fiber rerouting.",
    },
    {
        "ticket_number": "LW-CEB-2026-0820",
        "title": "Low-Hanging Fiber Cable Crossing Pedestrian Overpass",
        "barangay": "Guadalupe",
        "address": "V. Rama Ave cor. Happy Valley Rd, Brgy. Guadalupe",
        "lat": 10.3152,
        "lng": 123.8821,
        "severity": "medium",
        "status": "resolved",
        "image_url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80",
        "clearance": 2.7,
        "category_code": "SAGGING_CABLE",
        "hazard_type": "sagging_cable",
        "confidence": 94.7,
        "components": "Dead drop wire, Detached J-hook fixture",
        "wire_density": "Moderate (12 lines)",
        "sag_clearance": "2.7m clearance restored to 5.2m",
        "warning": "Pedestrian collision hazard now mitigated.",
        "action": "Tensioned and bundled to standard messenger wire.",
    },
    {
        "ticket_number": "LW-CEB-2026-0818",
        "title": "Transformer Sparking and Burned Spaghetti Insulation",
        "barangay": "Tisa",
        "address": "South Hills Road, Sitio Mangga, Brgy. Tisa",
        "lat": 10.2945,
        "lng": 123.8712,
        "severity": "critical",
        "status": "dispatched",
        "image_url": "https://images.unsplash.com/photo-1498084393753-b411b2d26b34?auto=format&fit=crop&w=800&q=80",
        "clearance": 4.0,
        "category_code": "BURNING_SPARKING",
        "hazard_type": "transformer_spark",
        "confidence": 97.8,
        "components": "Charred cable jackets, Thermal hotspot signature, Unauthorized tie-ins",
        "wire_density": "Severe (Telecom tangled directly onto secondary bus)",
        "sag_clearance": "Active arcing zone on transformer secondary lead",
        "warning": "Imminent electrical fire hazard adjacent to residential structures.",
        "action": "Immediate de-energization by emergency crew and standby.",
    },
]


class Command(BaseCommand):
    help = "Seeds all Cebu barangays, utility agencies, categories, demo users, and initial hazard reports into Supabase PostgreSQL."

    def handle(self, *args, **options):
        self.stdout.write("Starting database synchronization with Supabase...")

        # 1. Seed Cebu Barangays
        barangay_map = {}
        for b in BARANGAYS_DATA:
            obj, _ = CebuBarangay.objects.update_or_create(
                name=b["name"],
                defaults={
                    "district": b["district"],
                    "zip_code": "6000",
                    "center_lat": b["lat"],
                    "center_lng": b["lng"],
                    "hotline_number": b["hotline"],
                },
            )
            barangay_map[b["name"]] = obj
        self.stdout.write(self.style.SUCCESS(f"Synced {len(barangay_map)} Cebu Barangays."))

        # 2. Seed Utility Agencies
        agency_map = {}
        for a in AGENCIES_DATA:
            obj, _ = UtilityAgency.objects.update_or_create(
                agency_name=a["agency_name"],
                defaults={
                    "department": a["department"],
                    "contact_email": a["contact_email"],
                    "hotline_number": a["hotline_number"],
                    "agency_type": a["agency_type"],
                },
            )
            agency_map[a["agency_name"]] = obj
        self.stdout.write(self.style.SUCCESS(f"Synced {len(agency_map)} Utility Agencies."))

        # 3. Seed Hazard Categories
        category_map = {}
        for c in CATEGORIES_DATA:
            obj, _ = HazardCategory.objects.update_or_create(
                code=c["code"],
                defaults={
                    "category_name": c["name"],
                    "min_clearance": c["min_clearance"],
                    "default_severity": c["severity"],
                },
            )
            category_map[c["code"]] = obj
        self.stdout.write(self.style.SUCCESS(f"Synced {len(category_map)} Hazard Categories."))

        # 4. Seed Demo Users & Profiles
        user_map = {}
        for u in DEMO_USERS:
            email = u["email"].lower()
            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    "email": email,
                    "first_name": u["name"],
                },
            )
            user.set_password(u["password"])
            user.first_name = u["name"]
            user.email = email
            user.save()

            brgy_obj = barangay_map.get(u["barangay"])
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    "full_name": u["name"],
                    "phone": u["phone"],
                    "barangay": brgy_obj,
                    "avatar": u["avatar"],
                    "role": u.get("role", "citizen"),
                },
            )
            UserSettings.objects.get_or_create(user=user)
            user_map[email] = user
        self.stdout.write(self.style.SUCCESS(f"Synced {len(user_map)} Demo Users & Profiles."))

        # 5. Seed Initial Hazard Reports & AI Analyses & Dispatches
        tic_agency = agency_map.get("Cebu City Technical Infrastructure Committee (TIC)")
        veco_agency = agency_map.get("Visayan Electric (VECO)")
        primary_user = user_map.get("gianne@cebucity.ph")

        reports_synced = 0
        for r_data in INITIAL_REPORTS_DATA:
            brgy = barangay_map.get(r_data["barangay"])
            cat = category_map.get(r_data["category_code"])

            report, _ = HazardReport.objects.update_or_create(
                ticket_number=r_data["ticket_number"],
                defaults={
                    "title": r_data["title"],
                    "reporter": primary_user,
                    "barangay": brgy,
                    "category": cat,
                    "latitude": r_data["lat"],
                    "longitude": r_data["lng"],
                    "clearance_meters": r_data["clearance"],
                    "confidence_score": r_data["confidence"],
                    "severity": r_data["severity"],
                    "status": r_data["status"],
                    "hazard_type": r_data["hazard_type"],
                    "address": r_data["address"],
                    "image_url": r_data["image_url"],
                },
            )

            # AI Analysis (1:1 with HazardReport)
            AIHazardAnalysis.objects.update_or_create(
                report=report,
                defaults={
                    "confidence_score": r_data["confidence"],
                    "detected_components": r_data["components"],
                    "recommended_action": r_data["action"],
                    "safety_warning": r_data["warning"],
                    "is_valid_hazard": True,
                    "cable_sag_clearance": str(r_data["sag_clearance"])[:100],
                    "wire_density_score": str(r_data["wire_density"])[:50],
                    "severity_rating": str(r_data["severity"])[:20],
                },
            )

            # Hazard Dispatches (M:1 with HazardReport and UtilityAgency)
            if tic_agency:
                HazardDispatch.objects.update_or_create(
                    report=report,
                    agency=tic_agency,
                    defaults={
                        "turnaround_seconds": 32,
                        "delivery_status": "Delivered" if r_data["status"] != "resolved" else "Resolved",
                        "resolution_notes": "Dispatched to LGU Spaghetti Wire Eradication Task Force",
                    },
                )
            if veco_agency:
                HazardDispatch.objects.update_or_create(
                    report=report,
                    agency=veco_agency,
                    defaults={
                        "turnaround_seconds": 30,
                        "delivery_status": "Delivered" if r_data["status"] != "resolved" else "Resolved",
                        "resolution_notes": "Dispatched to Visayan Electric Line Safety Team",
                    },
                )
            reports_synced += 1

        self.stdout.write(self.style.SUCCESS(f"Synced {reports_synced} Hazard Reports, AI Analyses, and Dispatches."))
        self.stdout.write(self.style.SUCCESS("All CRUZ_ERD entities successfully synchronized to Supabase!"))
