import hashlib
import secrets
from datetime import time, timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("email_verified", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    SEX_CHOICES = [("female", "Female"), ("male", "Male"), ("other", "Other"), ("na", "Prefer not to say")]
    THEME_CHOICES = [("auto", "Match my device"), ("light", "Light"), ("dark", "Dark")]

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    email_verified = models.BooleanField(default=False)

    # Profile
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, default="na")
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="America/Toronto")
    water_goal_ml = models.PositiveIntegerField(default=2000)
    track_cycle = models.BooleanField(default=False)
    onboarded = models.BooleanField(default=False)
    city = models.CharField(max_length=120, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="auto")
    avatar_hue = models.PositiveIntegerField(default=28)

    # Reminders, each person sets their own
    checkins_per_day = models.PositiveSmallIntegerField(default=2)
    first_checkin_time = models.TimeField(default=time(10, 0))
    checkin_interval_hours = models.PositiveSmallIntegerField(default=8)
    water_reminders = models.BooleanField(default=True)
    water_interval_hours = models.PositiveSmallIntegerField(default=2)
    quiet_start = models.TimeField(default=time(22, 0))
    quiet_end = models.TimeField(default=time(7, 30))
    followups_enabled = models.BooleanField(default=True)
    cycle_notifications = models.BooleanField(default=True)
    weekly_summary = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.first_name or self.email.split("@")[0].title()

    @property
    def cycle_enabled(self):
        return self.track_cycle


class EmailOTP(models.Model):
    PURPOSES = [("signup", "Sign up"), ("login", "Log in"), ("reset", "Reset password")]

    email = models.EmailField(db_index=True)
    purpose = models.CharField(max_length=10, choices=PURPOSES)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)

    MAX_ATTEMPTS = 5
    TTL_MINUTES = 10

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def hash_code(email, code):
        raw = f"{settings.SECRET_KEY}:{email.lower()}:{code}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def issue(cls, email, purpose):
        code = f"{secrets.randbelow(1_000_000):06d}"
        cls.objects.filter(email=email, purpose=purpose, used=False).update(used=True)
        cls.objects.create(
            email=email,
            purpose=purpose,
            code_hash=cls.hash_code(email, code),
            expires_at=timezone.now() + timedelta(minutes=cls.TTL_MINUTES),
        )
        return code

    @classmethod
    def recent_count(cls, email, minutes=60):
        return cls.objects.filter(email=email, created_at__gte=timezone.now() - timedelta(minutes=minutes)).count()

    @classmethod
    def verify(cls, email, purpose, code):
        otp = cls.objects.filter(email=email, purpose=purpose, used=False).first()
        if not otp or otp.expires_at < timezone.now():
            return False, "That code has expired. Ask for a new one."
        if otp.attempts >= cls.MAX_ATTEMPTS:
            return False, "Too many tries. Ask for a new code."
        if not secrets.compare_digest(otp.code_hash, cls.hash_code(email, (code or "").strip())):
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            return False, "That code does not match. Check the email and try again."
        otp.used = True
        otp.save(update_fields=["used"])
        return True, ""
