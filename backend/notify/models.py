from django.conf import settings
from django.db import models
from django.utils import timezone


class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=600, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    """Every reminder lives here. It is pushed when due and also shows in the in-app inbox."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20)  # checkin, water, followup, cycle, care, nudge, weekly, goal, date
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=300, blank=True)
    url = models.CharField(max_length=200, default="/")
    payload = models.JSONField(default=dict, blank=True)
    send_at = models.DateTimeField(default=timezone.now, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    cancelled = models.BooleanField(default=False)
    respect_quiet = models.BooleanField(default=True)
    dedupe_key = models.CharField(max_length=120, null=True, blank=True, unique=True)

    class Meta:
        ordering = ["-send_at"]
