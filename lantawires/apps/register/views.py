from django.contrib import messages
from django.shortcuts import redirect, render

CEBU_BARANGAYS = [
    "Tisa",
    "Buhisan",
    "Lahug",
    "Guadalupe",
    "Mabolo",
    "Kasambagan",
    "Banilad",
    "Punta Princesa",
    "Labangon",
    "Sambag I",
    "Sambag II",
    "Talamban",
    "Tejero",
    "Pari-an",
    "Carreta",
    "San Nicolas Proper",
    "Mambaling",
    "Basak San Nicolas",
    "Basak Pardo",
    "Cogon Ramos",
    "Capitol Site",
    "Kamputhaw",
    "Apas",
]

def register_view(request):
    context = {
        "barangays": CEBU_BARANGAYS,
    }

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        barangay = request.POST.get("barangay", "Tisa").strip()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()
        agree_terms = request.POST.get("agree_terms") == "on"

        context.update({
            "name": name,
            "email": email,
            "phone": phone,
            "selected_barangay": barangay,
        })

        if not name:
            messages.error(request, "Please provide your full name.")
            return render(request, "register/register.html", context)

        if not email or "@" not in email:
            messages.error(request, "Please provide a valid email address.")
            return render(request, "register/register.html", context)

        if not phone:
            messages.error(request, "Please provide your contact number.")
            return render(request, "register/register.html", context)

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return render(request, "register/register.html", context)

        if password != confirm_password:
            messages.error(request, "Password confirmation does not match.")
            return render(request, "register/register.html", context)

        if not agree_terms:
            messages.error(request, "Please acknowledge the hazard reporting guidelines.")
            return render(request, "register/register.html", context)

        from django.contrib.auth.models import User
        from .models import UserProfile

        # Check if email is already registered
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with this email address already exists. Please log in.")
            return render(request, "register/register.html", context)

        # Create Django User and Profile in database
        user = User.objects.create_user(
            username=email.lower(),
            email=email.lower(),
            password=password,
            first_name=name,
        )

        avatar = "".join(part[0] for part in name.split()[:2]).upper() or "LW"
        UserProfile.objects.create(
            user=user,
            full_name=name,
            phone=phone,
            barangay=barangay,
            avatar=avatar,
        )

        request.session["last_registered_email"] = email
        request.session.save()

        messages.success(
            request,
            "Account created successfully.",
        )
        return redirect(f"/login/?registered_email={email}")

    return render(request, "register/register.html", context)
