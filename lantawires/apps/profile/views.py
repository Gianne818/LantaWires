from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .models import CebuBarangay, Profile

CEBU_BARANGAYS = [
    "Tisa", "Buhisan", "Lahug", "Guadalupe", "Mabolo",
    "Kasambagan", "Banilad", "Punta Princesa", "Labangon",
    "Sambag I", "Sambag II", "Talamban", "Tejero", "Pari-an",
    "Carreta", "San Nicolas Proper", "Mambaling", "Basak San Nicolas",
    "Basak Pardo", "Cogon Ramos", "Capitol Site", "Kamputhaw", "Apas",
]

AVATAR_PRESETS = ["GC", "EM", "LA", "LW", "CB", "TI", "VE"]

def profile_view(request):
    current_user_session = request.session.get("current_user")
    if not request.user.is_authenticated and not current_user_session:
        messages.warning(request, "Please log in to view your profile.")
        return redirect("login:login")

    user = request.user if request.user.is_authenticated else None
    profile = None
    if user:
        default_barangay, _ = CebuBarangay.objects.get_or_create(
            name="Tisa",
            defaults={
                "district": "South District",
                "zip_code": "6000",
                "center_lat": 10.2982,
                "center_lng": 123.8741,
            },
        )
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                "full_name": user.get_full_name() or user.username,
                "phone": "+63 917 554 8921",
                "barangay": default_barangay,
                "bio": "Civic responder helping clear hazardous cables across Cebu City.",
                "avatar": user.first_name[:2].upper() if user.first_name else "GC",
            }
        )

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        barangay_name = request.POST.get("barangay", "Tisa").strip()
        bio = request.POST.get("bio", "").strip()
        avatar = request.POST.get("avatar", "GC").strip()

        if profile:
            barangay_obj, _ = CebuBarangay.objects.get_or_create(
                name=barangay_name,
                defaults={
                    "district": "South District",
                    "zip_code": "6000",
                    "center_lat": 10.2982,
                    "center_lng": 123.8741,
                },
            )
            profile.full_name = full_name or profile.full_name
            profile.phone = phone or profile.phone
            profile.barangay = barangay_obj
            profile.bio = bio
            profile.avatar = avatar
            profile.save()

            if user:
                user.first_name = full_name
                user.save()

        # Update session copy as well
        if current_user_session:
            current_user_session.update({
                "name": full_name or current_user_session.get("name"),
                "phone": phone or current_user_session.get("phone"),
                "barangay": barangay_name,
                "avatar": avatar,
                "role": profile.role if profile else current_user_session.get("role", "citizen"),
            })
            request.session["current_user"] = current_user_session
            request.session.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("profile:profile")

    profile_barangay = profile.barangay.name if profile and profile.barangay_id else "Tisa"
    context = {
        "user": user,
        "profile": profile,
        "current_user": current_user_session or {
            "name": profile.full_name if profile else "Gianne Cruz",
            "phone": profile.phone if profile else "+63 917 554 8921",
            "barangay": profile_barangay if profile else "Tisa",
            "avatar": profile.avatar if profile else "GC",
            "email": user.email if user else "gianne@cebucity.ph",
        },
        "barangays": list(CebuBarangay.objects.values_list("name", flat=True)) or CEBU_BARANGAYS,
        "avatar_presets": AVATAR_PRESETS,
    }
    return render(request, "profile/profile.html", context)
