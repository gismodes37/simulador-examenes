from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for the User model."""

    list_display = [
        "username",
        "email",
        "callsign",
        "is_radio_amateur",
        "is_staff",
        "date_joined",
    ]
    list_filter = [
        "is_radio_amateur",
        "is_staff",
        "is_superuser",
        "is_active",
    ]
    search_fields = [
        "username",
        "email",
        "callsign",
        "first_name",
        "last_name",
    ]
    ordering = ["-date_joined"]

    # Add callsign and is_radio_amateur to the default fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Radio Amateur Info",
            {"fields": ("callsign", "is_radio_amateur")},
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Radio Amateur Info",
            {"fields": ("callsign", "is_radio_amateur")},
        ),
    )
