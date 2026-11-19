from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):

        extra_fields.setdefault("role", "admin")
        return super().create_superuser(username, email, password, **extra_fields)

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        SHOWROOM_USER = "showroom_user", "Showroom User"
        CUSTOMER = "customer", "Customer"
        MODERATOR = "moderator", "Moderator"
        ECOMMERCE_STAFF = "ecommerce_staff", "Ecommerce staff"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SHOWROOM_USER)
    phone_number = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)

    objects = CustomUserManager()

    showroom = models.ForeignKey(
        "showrooms.Showroom",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )

    def __str__(self):
        return f"{self.username} ({self.role})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.role == self.Role.SHOWROOM_USER and not self.showroom_id:
            raise ValidationError("A showroom user must be assigned to a showroom.")
        if self.role == self.Role.ADMIN and self.showroom_id:
            raise ValidationError("An admin user must not be assigned to a showroom.")


class EmailVerification(models.Model):
    email = models.EmailField(unique=True)
    purpose = models.CharField(max_length=10, choices=[("signup", "Signup"), ("verify", "Existing account")])
    nonce = models.CharField(max_length=64)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField()
    ready = models.BooleanField(default=False)
    consumed = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    window_started_at = models.DateTimeField()
    sent_count = models.PositiveSmallIntegerField(default=0)


class OtpSendBudget(models.Model):
    day = models.DateField(unique=True)
    reserved = models.PositiveIntegerField(default=0)
