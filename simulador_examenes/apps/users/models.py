from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model for radio amateur exam simulator."""

    callsign = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Amateur radio callsign (e.g., XQ1AA)",
    )
    is_radio_amateur = models.BooleanField(
        default=False,
        help_text="Indicates if the user holds a radio amateur license",
    )

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self):
        if self.callsign:
            return f"{self.callsign} ({self.username})"
        return self.username
