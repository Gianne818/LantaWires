from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from .models import UserSettings

def settings_view(request):
    current_user_session = request.session.get("current_user")
    if not request.user.is_authenticated and not current_user_session:
        messages.warning(request, "Please log in to access your settings.")
        return redirect("login:login")

    user = request.user if request.user.is_authenticated else None
    settings_obj = None
    if user:
        settings_obj, _ = UserSettings.objects.get_or_create(user=user)

    if request.method == "POST":
        dark_mode = request.POST.get("dark_mode") == "on"
        email_notifications = request.POST.get("email_notifications") == "on"
        hazard_alerts = request.POST.get("hazard_alerts") == "on"
        auto_dispatch_updates = request.POST.get("auto_dispatch_updates") == "on"
        sound_alerts = request.POST.get("sound_alerts") == "on"

        if settings_obj:
            settings_obj.dark_mode = dark_mode
            settings_obj.email_notifications = email_notifications
            settings_obj.hazard_alerts = hazard_alerts
            settings_obj.auto_dispatch_updates = auto_dispatch_updates
            settings_obj.sound_alerts = sound_alerts
            settings_obj.save()

        # Update session settings cache
        request.session["user_settings"] = {
            "dark_mode": dark_mode,
            "email_notifications": email_notifications,
            "hazard_alerts": hazard_alerts,
            "auto_dispatch_updates": auto_dispatch_updates,
            "sound_alerts": sound_alerts,
        }
        request.session.save()

        messages.success(request, "Settings updated successfully.")
        return redirect("user_settings:settings")

    session_settings = request.session.get("user_settings", {
        "dark_mode": True,
        "email_notifications": True,
        "hazard_alerts": True,
        "auto_dispatch_updates": True,
        "sound_alerts": False,
    })

    role = (current_user_session or {}).get("role")
    if role not in ("citizen", "resolver") and user is not None:
        try:
            role = user.profile.role
        except Exception:
            role = "citizen"
    is_resolver = role == "resolver"

    context = {
        "user": user,
        "settings": settings_obj or session_settings,
        "current_user": current_user_session,
        "is_resolver": is_resolver,
    }
    return render(request, "user_settings/user_settings.html", context)


@require_POST
def change_password_view(request):
    """Allow authenticated users to update their account password without losing their session."""
    if not request.user.is_authenticated:
        messages.warning(request, "Please log in to update your password.")
        return redirect("login:login")

    current_password = request.POST.get("current_password", "")
    new_password = request.POST.get("new_password", "")
    confirm_password = request.POST.get("confirm_password", "")

    if not current_password or not new_password or not confirm_password:
        messages.error(request, "Please fill out all password fields.")
        return redirect("user_settings:settings")

    if not request.user.check_password(current_password):
        messages.error(request, "Current password is incorrect.")
        return redirect("user_settings:settings")

    if len(new_password) < 6:
        messages.error(request, "New password must be at least 6 characters long.")
        return redirect("user_settings:settings")

    if new_password != confirm_password:
        messages.error(request, "New password confirmation does not match.")
        return redirect("user_settings:settings")

    if new_password == current_password:
        messages.error(request, "New password must be different from your current password.")
        return redirect("user_settings:settings")

    request.user.set_password(new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)
    messages.success(request, "Password updated successfully.")
    return redirect("user_settings:settings")
