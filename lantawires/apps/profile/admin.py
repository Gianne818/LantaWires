from django.contrib import admin
from .models import CebuBarangay, Profile


@admin.register(CebuBarangay)
class CebuBarangayAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "zip_code")
    search_fields = ("name", "district")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "phone", "barangay", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__username", "full_name", "phone")
