from .models import UserSettings


def user_settings_context(request):
    """Inject persisted UserSettings into all templates so base.html theme stays synced."""
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        try:
            settings_obj = UserSettings.objects.filter(user=user).first()
            if settings_obj is not None:
                return {"settings": settings_obj}
        except Exception:
            pass

    session_settings = request.session.get("user_settings")
    if isinstance(session_settings, dict):
        return {"settings": session_settings}

    return {"settings": {"dark_mode": False}}
