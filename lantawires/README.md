# LantaWires — Overhead Wire Hazard Detection & Auto-Dispatch Platform

An independent, mobile-responsive civic safety web application built with **Python Django**, **Supabase PostgreSQL**, and **Leaflet GIS** to report, verify, track, and dispatch hazardous overhead "spaghetti" utility wires across **23 Cebu City barangays**.

---

## System Architecture (Vertical Slicing)

The project uses a modular 5-app vertical slicing architecture backed by a normalized 9-table relational schema (`CRUZ_ERD.pdf`):

```text
lantawires/
├── config/                     # Project settings, context processors, root URLs & media serving
├── apps/
│   ├── login/                  # Authentication, role-aware session init, & `seed_demo` command
│   ├── register/               # Citizen & TIC/VECO resolver registration (invite code gated)
│   ├── home/                   # Citizen Watch, Resolver Triage Console, My Reports, Dispatches & APIs
│   ├── profile/                # CebuBarangay master directory, Profile management & role stats
│   └── user_settings/          # Persisted dark mode / alert preferences, global theme & password change
├── templates/                  # Claymorphism light/dark UI templates across all 5 apps
├── static/                     # Custom CSS, JS controllers, and Wiry mascot SVG assets
├── docs/                       # Part A/B/C SQL JOIN & SUBQUERY documentation + video demo guide
├── requirements.txt            # Django, psycopg2-binary, dj-database-url, python-dotenv
└── manage.py                   # Django CLI entrypoint
```

---

## Role-Based Workflows & Key Features

1. **Authentication & Registration (`/login/`, `/register/`)**
   - Role-based sign-in supporting **Citizen** accounts and **TIC / VECO Resolver** accounts (registrable via invite code `TIC-VECO-2026`).
   - One-click **Demo Citizen** (`morales.cebu@gmail.com`) and **Demo Resolver** (`gianne@cebucity.ph`) quick-fill buttons.
2. **Citizen Watch & Resolver Triage Console (`/`, `/home/`)**
   - **Interactive Leaflet Cebu City GIS Map** with severity-coded pins, bounding limits, and live coordinate tracking.
   - **Upgraded Report Hazard Wizard**: device photo upload (persisted under `/media/hazards/`), quick demo presets, live `HazardCategory` selector, severity & clearance estimation, and GPS / map-pin targeting.
   - **Full Hazard Report CRUD**: inspect telemetry & dispatch receipts, edit unresolved reports (`POST /home/api/report/<id>/edit/`), withdraw or delete reports (`POST /home/api/report/<id>/delete/`), and update 3-stage triage status (`Dispatched` → `Investigating` → `Resolved`) for resolvers.
3. **Personal Submission Tracker (`/home/my-reports/`)**
   - FK-linked report list for the signed-in user with **Inspect**, **Edit**, and **Withdraw** modals.
4. **Resolver Dispatches & Analytics Console (`/home/dispatches/`)**
   - **Live Utility Dispatch Queue (4-table SQL `INNER JOIN`)**: `HazardDispatch` joined with `HazardReport`, `CebuBarangay`, and `UtilityAgency`, with live search, agency filter, delivery-status filter, and crew resolution notes.
   - **Active Hotspot Barangays (SQL `SUBQUERY`)**: filters `cebu_barangays` with `id__in=Subquery(...)` to show only barangays with unresolved wire hazards and their Barangay Hall hotlines.
   - **Multi-Agency Dispatching (`POST /home/api/dispatch/create/`)**: manually route open tickets to partner agencies (`TIC`, `VECO`, `PLDT-Smart`, `Globe Telecom`, `CCDRRMO`).
   - **Filtered CSV Export (`/home/dispatches/export/`)**: download formula-safe operational CSV reports matching active queue filters.
5. **Profile & Global Settings (`/profile/`, `/settings/`)**
   - Edit avatar preset, full name, mobile number, home barangay, and bio with role-aware recent activity.
   - Global `UserSettings` context processor keeps dark/light clay mode synced across every page, plus an **Account Security — Change Password** form.

---

## Setup & Running Instructions

### 1. Create and Activate Virtual Environment
```bash
cd lantawires
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment & Database
Create `lantawires/.env` (see `.env.example`) with your Supabase PostgreSQL `DATABASE_URL` (falls back to local SQLite if omitted), then run migrations and seed demo data:
```bash
python manage.py migrate
python manage.py seed_demo
```

### 4. Start Server & Run Tests
```bash
python manage.py runserver
# In another terminal:
python manage.py test -v 2
```

Open `http://127.0.0.1:8000/`.

---

## Quick Demo Testing Credentials

- **Resolver Account:** `gianne@cebucity.ph` / `cebuwirehazard2026`
- **Citizen Account:** `morales.cebu@gmail.com` / `cebuwirehazard2026`
- Or click **Demo Citizen** / **Demo Resolver** on the Login screen.
