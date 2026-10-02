from django.contrib import admin
from .models import (
    AIHazardAnalysis,
    HazardCategory,
    HazardDispatch,
    HazardReport,
    UtilityAgency,
)


@admin.register(HazardReport)
class HazardReportAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "title",
        "barangay",
        "category",
        "severity",
        "status",
        "created_at",
    )
    list_filter = ("severity", "status", "category")
    search_fields = ("ticket_number", "title", "address")


@admin.register(HazardCategory)
class HazardCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "category_name", "min_clearance", "default_severity")


@admin.register(UtilityAgency)
class UtilityAgencyAdmin(admin.ModelAdmin):
    list_display = ("agency_name", "department", "agency_type")


@admin.register(AIHazardAnalysis)
class AIHazardAnalysisAdmin(admin.ModelAdmin):
    list_display = ("report", "confidence_score", "severity_rating", "analyzed_at")


@admin.register(HazardDispatch)
class HazardDispatchAdmin(admin.ModelAdmin):
    list_display = ("report", "agency", "delivery_status", "dispatched_at")
