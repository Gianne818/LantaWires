"""
ERD Entity mapping for user_settings app.
Entity: user_settings_usersettings -> UserSettings
Reference: CRUZ_ERD.pdf
"""

from django.conf import settings
from django.db import models


class UserSettings(models.Model):
    """ERD Entity: user_settings_usersettings (1:1 with auth_user)."""

    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settings"
    )
    dark_mode = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    hazard_alerts = models.BooleanField(default=True)
    auto_dispatch_updates = models.BooleanField(default=True)
    sound_alerts = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_settings_usersettings"
        verbose_name = "User Settings"
        verbose_name_plural = "User Settings"

    def __str__(self):
        return f"Settings for {self.user.username}"
