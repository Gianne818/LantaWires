from django.contrib import messages
from django.shortcuts import redirect, render
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

    context = {
        "user": user,
        "settings": settings_obj or session_settings,
        "current_user": current_user_session,
    }
    return render(request, "user_settings/user_settings.html", context)
