from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class CebuBarangay(models.Model):
    id = models.AutoField(
        primary_key=True,
        help_text="Primary Key: Integer M PI",
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Barangay name: Varchar(100) M",
    )
    district = models.CharField(
        max_length=50,
        help_text="Administrative district (North/South): Varchar(50) M",
    )
    zip_code = models.CharField(
        max_length=10,
        default="6000",
        help_text="Postal zip code: Varchar(10) M",
    )
    center_lat = models.FloatField(
        help_text="Centroid GPS latitude: Double Precision M",
    )
    center_lng = models.FloatField(
        help_text="Centroid GPS longitude: Double Precision M",
    )
    hotline_number = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Barangay Hall Emergency Hotline: Varchar(30)",
    )

    class Meta:
        db_table = "cebu_barangays"
        verbose_name = "Cebu Barangay"
        verbose_name_plural = "Cebu Barangays"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.district})"


class UtilityAgency(models.Model):
    id = models.AutoField(
        primary_key=True,
        help_text="Primary Key: Integer M PI",
    )
    agency_name = models.CharField(
        max_length=150,
        help_text="Agency / Corporate entity name: Varchar(150) M",
    )
    department = models.CharField(
        max_length=150,
        help_text="Specialized operations division: Varchar(150) M",
    )
    contact_email = models.CharField(
        max_length=254,
        help_text="Dispatch notification email: Varchar(254) M",
    )
    hotline_number = models.CharField(
        max_length=50,
        help_text="Direct emergency dispatch telephone hotline: Varchar(50) M",
    )
    agency_type = models.CharField(
        max_length=50,
        help_text="Sector classification (Power, Telco, LGU): Varchar(50) M",
    )

    class Meta:
        db_table = "utility_agencies"
        verbose_name = "Utility Agency"
        verbose_name_plural = "Utility Agencies"
        ordering = ["agency_name"]

    def __str__(self):
        return f"{self.agency_name} - {self.department}"


class HazardCategory(models.Model):
    id = models.AutoField(
        primary_key=True,
        help_text="Primary Key: Integer M PI",
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique category identifier token: Varchar(50) M",
    )
    category_name = models.CharField(
        max_length=100,
        help_text="Full descriptive category name: Varchar(100) M",
    )
    min_clearance = models.FloatField(
        help_text="Minimum legal clearance height in meters: Double Precision M",
    )
    default_severity = models.CharField(
        max_length=20,
        choices=[
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ],
        default="high",
        help_text="Default hazard severity level: Varchar(20) M",
    )

    class Meta:
        db_table = "hazard_categories"
        verbose_name = "Hazard Category"
        verbose_name_plural = "Hazard Categories"
        ordering = ["category_name"]

    def __str__(self):
        return f"{self.category_name} [{self.code}]"


class Profile(models.Model):
    id = models.BigAutoField(
        primary_key=True,
        help_text="Primary Key: BigInt M PI",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Foreign Key to auth_user: BigInt M FK",
    )
    barangay = models.ForeignKey(
        CebuBarangay,
        on_delete=models.PROTECT,
        related_name="profiles",
        help_text="Foreign Key to cebu_barangays: Integer M FK",
    )
    full_name = models.CharField(
        max_length=150,
        help_text="Citizen full legal name: Varchar(150) M",
    )
    phone = models.CharField(
        max_length=30,
        help_text="Mobile or contact phone number: Varchar(30) M",
    )
    avatar = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        default="GC",
        help_text="Initials or profile avatar preset: Varchar(10)",
    )
    bio = models.TextField(
        blank=True,
        null=True,
        default="Cebu City civic safety contributor",
        help_text="Short citizen biography: Text",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Account creation timestamp: Timestamptz M",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last profile update timestamp: Timestamptz M",
    )

    class Meta:
        db_table = "profile_profile"
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.barangay.name if self.barangay else 'Unknown'})"


class UserSettings(models.Model):
    id = models.BigAutoField(
        primary_key=True,
        help_text="Primary Key: BigInt M PI",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings",
        help_text="Foreign Key to auth_user: BigInt M FK",
    )
    dark_mode = models.BooleanField(
        default=True,
        help_text="Dark mode UI theme preference: Boolean M",
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text="Email alert preference: Boolean M",
    )
    hazard_alerts = models.BooleanField(
        default=True,
        help_text="Emergency wire alert push notifications: Boolean M",
    )
    auto_dispatch_updates = models.BooleanField(
        default=True,
        help_text="Real-time dispatch telemetry updates: Boolean M",
    )
    sound_alerts = models.BooleanField(
        default=False,
        help_text="Sound alert notifications toggle: Boolean M",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp of last preference change: Timestamptz M",
    )

    class Meta:
        db_table = "user_settings_usersettings"
        verbose_name = "User Settings"
        verbose_name_plural = "User Settings"

    def __str__(self):
        return f"Settings for {self.user.username}"


class HazardReport(models.Model):
    id = models.BigAutoField(
        primary_key=True,
        help_text="Primary Key: BigInt M PI",
    )
    ticket_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Tracking ticket code (e.g., LW-CEB-2026-0811): Varchar(50) M",
    )
    title = models.CharField(
        max_length=200,
        help_text="Incident headline summary: Varchar(200) M",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazard_reports",
        help_text="Foreign Key to auth_user (optional/anonymous): BigInt FK",
    )
    barangay = models.ForeignKey(
        CebuBarangay,
        on_delete=models.PROTECT,
        related_name="hazard_reports",
        help_text="Foreign Key to cebu_barangays: Integer M FK",
    )
    category = models.ForeignKey(
        HazardCategory,
        on_delete=models.PROTECT,
        related_name="hazard_reports",
        help_text="Foreign Key to hazard_categories: Integer M FK",
    )
    latitude = models.FloatField(
        default=10.2982,
        help_text="Incident GPS latitude: Double Precision M",
    )
    longitude = models.FloatField(
        default=123.8741,
        help_text="Incident GPS longitude: Double Precision M",
    )
    clearance_meters = models.FloatField(
        default=3.0,
        help_text="Overhead clearance from asphalt in meters: Double Precision M",
    )
    confidence_score = models.FloatField(
        default=95.8,
        help_text="Computer vision confidence score (0-100): Double Precision M",
    )
    severity = models.CharField(
        max_length=20,
        choices=[
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ],
        default="critical",
        help_text="Assigned hazard severity: Varchar(20) M",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("dispatched", "Dispatched"),
            ("investigating", "Investigating"),
            ("resolved", "Resolved"),
        ],
        default="dispatched",
        help_text="Current triage status: Varchar(20) M",
    )
    hazard_type = models.CharField(
        max_length=50,
        default="sagging_cable",
        help_text="Wire hazard type code: Varchar(50) M",
    )
    address = models.CharField(
        max_length=255,
        help_text="Street address / landmark: Varchar(255) M",
    )
    image_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Hosted photographic inspection evidence URL: Varchar(500)",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Submission timestamp: Timestamptz M",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last triage update timestamp: Timestamptz M",
    )

    class Meta:
        db_table = "home_hazardreport"
        verbose_name = "Hazard Report"
        verbose_name_plural = "Hazard Reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket_number} - {self.title} ({self.barangay.name if self.barangay else 'Unknown'})"


class AIHazardAnalysis(models.Model):
    id = models.BigAutoField(
        primary_key=True,
        help_text="Primary Key: BigInt M PI",
    )
    report = models.OneToOneField(
        HazardReport,
        on_delete=models.CASCADE,
        related_name="ai_analysis",
        help_text="Foreign Key to home_hazardreport: BigInt M FK",
    )
    confidence_score = models.FloatField(
        help_text="AI model confidence percentage: Double Precision M",
    )
    detected_components = models.TextField(
        help_text="Identified wire objects / bounding boxes: Text M",
    )
    recommended_action = models.TextField(
        help_text="Actionable mitigation instructions: Text M",
    )
    safety_warning = models.TextField(
        help_text="Public safety threat advisory: Text M",
    )
    is_valid_hazard = models.BooleanField(
        default=True,
        help_text="Verification flag for actionable hazard: Boolean M",
    )
    analyzed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Inference execution timestamp: Timestamptz M",
    )
    cable_sag_clearance = models.CharField(
        max_length=100,
        help_text="Clearance estimation against legal standards: Varchar(100) M",
    )
    wire_density_score = models.CharField(
        max_length=50,
        help_text="Bundle density classification: Varchar(50) M",
    )
    severity_rating = models.CharField(
        max_length=20,
        help_text="Risk rating classification: Varchar(20) M",
    )

    class Meta:
        db_table = "ai_hazard_analyses"
        verbose_name = "AI Hazard Analysis"
        verbose_name_plural = "AI Hazard Analyses"
        ordering = ["-analyzed_at"]

    def __str__(self):
        return f"AI Analysis for {self.report.ticket_number} ({self.confidence_score}%)"


class HazardDispatch(models.Model):
    id = models.BigAutoField(
        primary_key=True,
        help_text="Primary Key: BigInt M PI",
    )
    report = models.ForeignKey(
        HazardReport,
        on_delete=models.CASCADE,
        related_name="dispatches",
        help_text="Foreign Key to home_hazardreport: BigInt M FK",
    )
    agency = models.ForeignKey(
        UtilityAgency,
        on_delete=models.CASCADE,
        related_name="dispatches",
        help_text="Foreign Key to utility_agencies: Integer M FK",
    )
    dispatched_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Transmission timestamp: Timestamptz M",
    )
    turnaround_seconds = models.IntegerField(
        default=30,
        help_text="Dispatch system turnaround duration in seconds: Integer M",
    )
    acknowledged_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Crew acknowledgment timestamp: Timestamptz",
    )
    resolution_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Remediation / clearing operational notes: Text",
    )
    delivery_status = models.CharField(
        max_length=30,
        default="Delivered",
        choices=[
            ("Delivered", "Delivered"),
            ("Acknowledged", "Acknowledged"),
            ("En Route", "En Route"),
            ("Resolved", "Resolved"),
            ("Failed", "Failed"),
        ],
        help_text="Transmission state: Varchar(30) M",
    )

    class Meta:
        db_table = "hazard_dispatches"
        verbose_name = "Hazard Dispatch"
        verbose_name_plural = "Hazard Dispatches"
        ordering = ["-dispatched_at"]

    def __str__(self):
        return f"Dispatch #{self.id} -> {self.agency.agency_name} ({self.delivery_status})"
