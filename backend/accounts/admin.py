from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import EmailOTP, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "email_verified", "sex", "date_joined"]
    search_fields = ["email", "first_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "sex", "birth_year", "timezone", "water_goal_ml", "track_cycle",
                                "onboarded", "city", "latitude", "longitude", "theme")}),
        ("Reminders", {"fields": ("checkins_per_day", "first_checkin_time", "checkin_interval_hours",
                                  "water_reminders", "water_interval_hours", "quiet_start", "quiet_end",
                                  "followups_enabled", "cycle_notifications", "weekly_summary")}),
        ("Access", {"fields": ("is_active", "email_verified", "is_staff", "is_superuser", "groups")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ["email", "purpose", "created_at", "used", "attempts"]
    exclude = ["code_hash"]
