from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from apps.profile.models import Profile

DEFAULT_USERS = [
    {
        "id": "usr-01",
        "name": "Gianne Cruz",
        "email": "gianne@cebucity.ph",
        "phone": "+63 917 554 8921",
        "barangay": "Tisa",
        "avatar": "GC",
    },
    {
        "id": "usr-02",
        "name": "Eduardo Morales",
        "email": "morales.cebu@gmail.com",
        "phone": "+63 920 882 1042",
        "barangay": "Lahug",
        "avatar": "EM",
    },
    {
        "id": "usr-03",
        "name": "Lourdes Alcantara",
        "email": "lourdes.alcantara@yahoo.com",
        "phone": "+63 918 331 4455",
        "barangay": "Guadalupe",
        "avatar": "LA",
    },
]

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        remember_me = request.POST.get("remember_me") == "on"

        if not email or not password:
            messages.error(request, "Please enter both your email and password.")
            return render(
                request,
                "login/login.html",
                {"email": email, "remember_me": remember_me},
            )

        # 1. Authenticate against database User
        user = authenticate(request, username=email.lower(), password=password)
        if user is not None:
            login(request, user)
            profile = getattr(user, "profile", None)
            profile_barangay = (
                profile.barangay.name if profile and profile.barangay_id else "Tisa"
            )
            user_profile = {
                "id": f"usr-{user.id:04d}",
                "name": profile.full_name if profile and profile.full_name else (user.get_full_name() or user.username),
                "email": user.email,
                "phone": profile.phone if profile else "+63 917 000 0000",
                "barangay": profile_barangay,
                "avatar": profile.avatar if profile and profile.avatar else (user.first_name[:2].upper() or "LW"),
            }
            request.session["current_user"] = user_profile
            request.session.save()
            messages.success(request, f"Logged in successfully as {user_profile['name']}.")
            return redirect("home:home")

        # 2. Check demo users fallback
        demo_match = next((u for u in DEFAULT_USERS if u["email"].lower() == email.lower()), None)
        if demo_match and password == "cebuwirehazard2026":
            from apps.profile.models import CebuBarangay

            user, _ = User.objects.get_or_create(
                username=email.lower(),
                defaults={"email": email.lower(), "first_name": demo_match["name"]}
            )
            user.set_password(password)
            user.save()
            barangay_obj, _ = CebuBarangay.objects.get_or_create(
                name=demo_match["barangay"],
                defaults={
                    "district": "South District",
                    "zip_code": "6000",
                    "center_lat": 10.2982,
                    "center_lng": 123.8741,
                },
            )
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    "full_name": demo_match["name"],
                    "phone": demo_match["phone"],
                    "barangay": barangay_obj,
                    "avatar": demo_match["avatar"],
                }
            )
            login(request, user)
            request.session["current_user"] = demo_match
            request.session.save()
            messages.success(request, f"Logged in successfully as {demo_match['name']}.")
            return redirect("home:home")

        messages.error(request, "Invalid email or password.")
        return render(
            request,
            "login/login.html",
            {"email": email, "remember_me": remember_me},
        )

    # GET request: check if arriving from registration
    prefill_email = request.GET.get("registered_email") or request.session.pop("last_registered_email", "")
    registered_notice = None
    if prefill_email:
        registered_notice = "Account created successfully."

    return render(request, "login/login.html", {
        "email": prefill_email,
        "registered_notice": registered_notice,
    })
