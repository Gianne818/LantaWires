"""
ERD Entity mapping for profile app.
Entities:
  - cebu_barangays      -> CebuBarangay (db_table="cebu_barangays")
  - profile_profile     -> Profile (db_table="profile_profile")
Reference: CRUZ_ERD.pdf
"""

from django.conf import settings
from django.db import models


class CebuBarangay(models.Model):
    """ERD Entity: cebu_barangays — master list of Cebu City barangays."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    district = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10, default="6000")
    center_lat = models.FloatField()
    center_lng = models.FloatField()
    hotline_number = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        db_table = "cebu_barangays"
        verbose_name = "Cebu Barangay"
        verbose_name_plural = "Cebu Barangays"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.district})"


class Profile(models.Model):
    """
    ERD Entity: profile_profile
    Relationships:
      - 1:1 with auth_user (user_id)
      - M:1 with cebu_barangays (barangay_id)
    """

    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    barangay = models.ForeignKey(
        CebuBarangay, on_delete=models.PROTECT, related_name="profiles"
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    avatar = models.CharField(max_length=10, blank=True, null=True, default="GC")
    bio = models.TextField(
        blank=True, null=True, default="Cebu City civic safety contributor"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profile_profile"
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"
        ordering = ["-created_at"]

    def __str__(self):
        barangay_name = getattr(self.barangay, "name", "Unknown")
        return f"{self.full_name or self.user.username} ({barangay_name})"

    @property
    def barangay_name(self):
        """Backwards-compatible accessor for templates/views using string barangay."""
        return self.barangay.name if self.barangay_id else ""
