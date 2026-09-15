from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "phone", "barangay", "created_at")
    search_fields = ("full_name", "user__email", "phone", "barangay")
    list_filter = ("barangay", "created_at")
