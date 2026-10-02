from django.contrib import admin
from .models import UserSettings

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "dark_mode", "email_notifications", "hazard_alerts", "auto_dispatch_updates")
