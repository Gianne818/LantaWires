"""
ERD Entity mapping for home app (operations domain).
Entities:
  - utility_agencies   -> UtilityAgency (db_table="utility_agencies")
  - hazard_categories  -> HazardCategory (db_table="hazard_categories")
  - home_hazardreport  -> HazardReport (db_table="home_hazardreport")
  - ai_hazard_analyses -> AIHazardAnalysis (db_table="ai_hazard_analyses")
  - hazard_dispatches  -> HazardDispatch (db_table="hazard_dispatches")
Reference: CRUZ_ERD.pdf
"""

from django.conf import settings
from django.db import models

SEVERITY_CHOICES = [
    ("critical", "Critical"),
    ("high", "High"),
    ("medium", "Medium"),
    ("low", "Low"),
]

STATUS_CHOICES = [
    ("dispatched", "Dispatched"),
    ("investigating", "Investigating"),
    ("resolved", "Resolved"),
]


class UtilityAgency(models.Model):
    """ERD Entity: utility_agencies."""

    id = models.AutoField(primary_key=True)
    agency_name = models.CharField(max_length=150)
    department = models.CharField(max_length=150)
    contact_email = models.CharField(max_length=254)
    hotline_number = models.CharField(max_length=50)
    agency_type = models.CharField(max_length=50)

    class Meta:
        db_table = "utility_agencies"
        verbose_name = "Utility Agency"
        verbose_name_plural = "Utility Agencies"
        ordering = ["agency_name"]

    def __str__(self):
        return f"{self.agency_name} - {self.department}"


class HazardCategory(models.Model):
    """ERD Entity: hazard_categories."""

    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    category_name = models.CharField(max_length=100)
    min_clearance = models.FloatField()
    default_severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default="high"
    )

    class Meta:
        db_table = "hazard_categories"
        verbose_name = "Hazard Category"
        verbose_name_plural = "Hazard Categories"
        ordering = ["category_name"]

    def __str__(self):
        return f"{self.category_name} [{self.code}]"


class HazardReport(models.Model):
    """
    ERD Entity: home_hazardreport
    Relationships:
      - M:1 with auth_user (reporter_id, nullable for anonymous)
      - M:1 with cebu_barangays (barangay_id)
      - M:1 with hazard_categories (category_id)
    """

    id = models.BigAutoField(primary_key=True)
    ticket_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazard_reports",
    )
    barangay = models.ForeignKey(
        "profile.CebuBarangay", on_delete=models.PROTECT, related_name="hazard_reports"
    )
    category = models.ForeignKey(
        HazardCategory, on_delete=models.PROTECT, related_name="hazard_reports"
    )
    latitude = models.FloatField(default=10.2982)
    longitude = models.FloatField(default=123.8741)
    clearance_meters = models.FloatField(default=3.0)
    confidence_score = models.FloatField(default=95.8)
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default="critical"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="dispatched")
    hazard_type = models.CharField(max_length=50, default="sagging_cable")
    address = models.CharField(max_length=255)
    image_url = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "home_hazardreport"
        verbose_name = "Hazard Report"
        verbose_name_plural = "Hazard Reports"
        ordering = ["-created_at"]

    def __str__(self):
        barangay_name = getattr(self.barangay, "name", "Unknown")
        return f"{self.ticket_number} - {self.title} ({barangay_name})"


class AIHazardAnalysis(models.Model):
    """
    ERD Entity: ai_hazard_analyses
    Relationship: 1:1 with home_hazardreport (report_id)
    """

    id = models.BigAutoField(primary_key=True)
    report = models.OneToOneField(
        HazardReport, on_delete=models.CASCADE, related_name="ai_analysis"
    )
    confidence_score = models.FloatField()
    detected_components = models.TextField()
    recommended_action = models.TextField()
    safety_warning = models.TextField()
    is_valid_hazard = models.BooleanField(default=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)
    cable_sag_clearance = models.CharField(max_length=100)
    wire_density_score = models.CharField(max_length=50)
    severity_rating = models.CharField(max_length=20)

    class Meta:
        db_table = "ai_hazard_analyses"
        verbose_name = "AI Hazard Analysis"
        verbose_name_plural = "AI Hazard Analyses"
        ordering = ["-analyzed_at"]

    def __str__(self):
        return f"AI Analysis for {self.report.ticket_number} ({self.confidence_score}%)"


class HazardDispatch(models.Model):
    """
    ERD Entity: hazard_dispatches
    Relationships:
      - M:1 with home_hazardreport (report_id)
      - M:1 with utility_agencies (agency_id)
    """

    DELIVERY_CHOICES = [
        ("Delivered", "Delivered"),
        ("Acknowledged", "Acknowledged"),
        ("En Route", "En Route"),
        ("Resolved", "Resolved"),
        ("Failed", "Failed"),
    ]

    id = models.BigAutoField(primary_key=True)
    report = models.ForeignKey(
        HazardReport, on_delete=models.CASCADE, related_name="dispatches"
    )
    agency = models.ForeignKey(
        UtilityAgency, on_delete=models.CASCADE, related_name="dispatches"
    )
    dispatched_at = models.DateTimeField(auto_now_add=True)
    turnaround_seconds = models.IntegerField(default=30)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)
    delivery_status = models.CharField(
        max_length=30, choices=DELIVERY_CHOICES, default="Delivered"
    )

    class Meta:
        db_table = "hazard_dispatches"
        verbose_name = "Hazard Dispatch"
        verbose_name_plural = "Hazard Dispatches"
        ordering = ["-dispatched_at"]

    def __str__(self):
        return f"Dispatch #{self.id} -> {self.agency.agency_name} ({self.delivery_status})"
