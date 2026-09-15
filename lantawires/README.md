# LantaWires — AI-Powered Wire Hazard Detection & Dispatch Platform

An independent, mobile-responsive civic safety web application built with **Python Django** designed to identify, analyze, and catalog hazardous overhead "spaghetti" utility wires across Cebu City.

---

## System Architecture (Vertical Slicing)

The project follows a clean vertical slicing architecture where the three core domains operate as distinct Django applications:

```text
lantawires/
├── config/                  # Project configuration & top-level routing
│   ├── settings.py          # App registration, session, templates & static setup
│   ├── urls.py              # Root router mapping /, /login/, /register/, /home/
│   ├── wsgi.py
│   └── asgi.py
├── login/                   # App 1: Authentication & Demo Credential Access
│   ├── apps.py
│   ├── urls.py
│   └── views.py             # Login verification, session init, flash messages
├── register/                # App 2: Citizen & Barangay Account Registration
│   ├── apps.py
│   ├── urls.py
│   └── views.py             # Validation, Cebu City barangay assignment
├── home/                    # App 3: Central Operations Dashboard & Telemetry
│   ├── apps.py
│   ├── data.py              # Cebu City barangay zones, mock incidents & presets
│   ├── urls.py
│   └── views.py             # Metrics aggregation, dispatch engine & REST APIs
├── templates/               # Reusable UI templates
│   ├── base.html            # Dark-mode design system & Lucide Icons integration
│   ├── login/
│   │   └── login.html       # Split-column civic overview & sign-in card
│   ├── register/
│   │   └── register.html    # Split-column registration & barangay selector
│   └── home/
│       └── home.html        # Hotspot vector map, metrics, feed & telemetry modals
├── static/
│   ├── css/
│   │   └── lantawires.css   # Tailored dark slate, amber hazard & cyber glow styling
│   └── js/
│       ├── login.js         # Autofill sample credentials & password toggle
│       ├── register.js      # Password confirmation validation & autofill
│       └── home.js          # SVG map pin projector, filter engine & report wizard
├── requirements.txt         # Dependencies (Django 5.x)
└── manage.py                # Django CLI entrypoint
```

---

## Screen Navigation Flow

```text
               ┌───────────────────────────────┐
               │         Login Screen          │◄────────────┐
               │   (http://127.0.0.1:8000/)    │             │
               └──────────────┬────────────────┘             │
                              │                              │
               ┌──────────────┴──────────────┐               │
               │                             │               │
    [Create an account]              [Sign In / Autofill]    │
               │                             │               │
               ▼                             ▼               │
 ┌───────────────────────────┐ ┌───────────────────────────┐ │
 │      Register Screen      │ │        Home Screen        │ │
 │ (http://127.0.0.1:8000/   │ │ (http://127.0.0.1:8000/   │ │
 │        register/)         │ │          home/)           │ │
 └─────────────┬─────────────┘ └─────────────┬─────────────┘ │
               │                             │               │
      [Register Account /                    │               │
       Sign in here link]                [Sign Out]          │
               │                             │               │
               └─────────────────────────────┴───────────────┘
```

1. **Login Screen (`/login/` or `/`)**:
   - Split layout with Cebu City safety platform overview, problem statement, and 3 feature highlight cards.
   - Fast **"Autofill Sample"** button to prefill verified demo credentials.
   - Smooth link to Register Screen.
2. **Register Screen (`/register/`)**:
   - Citizen registration with full name, contact number, email, and selection of 23+ Cebu City barangays (Tisa, Buhisan, Lahug, Guadalupe, Mabolo, etc.).
   - Fast **"Autofill Sample"** button.
   - **Post-Registration Transition**: Submitting the registration form redirects back to the **Login Screen** with a success notice (`Account created! Please sign in with <email> to access the home screen`) and prefilled email, ensuring users authenticate before reaching the dashboard.
3. **Home Screen (`/home/`)**:
   - Protected: Direct unauthenticated access redirects to the Login screen.
   - Header with active user profile badge and **Sign Out** button (transitions back to Login).
   - Real-time triage metrics: Total Verified, Active Dispatches, Critical Hazards, Resolved Bundles.
   - Interactive stylized **Cebu City Hotspot Map** with animated pulsing pins and interactive inspection.
   - Live Incident Cards Feed with search by street, barangay, and severity filters.
   - **Report Overhead Hazard Modal**: Interactive simulation of computer vision analysis.
   - **Incident Detail Modal**: Telemetry inspection with detected bounding boxes, safety warnings, and dispatch receipts.

---

## Setup & Running Instructions

### 1. Create and Activate Virtual Environment

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Migrations (Optional)

```bash
python manage.py migrate
```

### 4. Start the Django Server

```bash
python manage.py runserver
```

Open your browser at:
```text
http://127.0.0.1:8000/
```

---

## Quick Demo Testing Credentials

- **Email**: `gianne@cebucity.ph`
- **Password**: `cebuwirehazard2026`
- Or simply click the **"Autofill Sample"** button present on both Login and Register screens.
