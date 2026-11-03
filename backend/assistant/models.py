from django.conf import settings
from django.db import models
from django.utils import timezone

from config.utils import EncryptedTextField


class ChatMessage(models.Model):
    ROLES = [("user", "Person"), ("assistant", "Ruvia")]
    KINDS = [("checkin", "Check-in"), ("ask", "History question"), ("followup", "Follow up"), ("safety", "Safety"),
             ("rough_day", "Rough day"), ("system", "System"), ("chat", "Chat")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLES)
    kind = models.CharField(max_length=10, choices=KINDS, default="checkin")
    text = EncryptedTextField(blank=True, default="")
    source = models.CharField(max_length=10, default="text")  # text or voice
    payload = models.JSONField(default=dict, blank=True)
    provider = models.CharField(max_length=20, blank=True)
    client_id = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]


class FollowUp(models.Model):
    STATUS = [("pending", "Pending"), ("answered", "Answered"), ("expired", "Expired")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followups")
    episode = models.ForeignKey("health.SymptomEpisode", on_delete=models.CASCADE, related_name="followups")
    due_at = models.DateTimeField()
    round = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    answer = models.CharField(max_length=10, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-due_at"]
