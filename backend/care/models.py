from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL

SHARE_FIELDS = ["scores", "tags", "symptoms", "water", "cycle", "cycle_alerts", "rough_day", "dates", "emergency_card", "medications"]


class Invite(models.Model):
    STATUS = [("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")]
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invites_sent")
    email = models.EmailField()
    invitee = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="invites_received")
    relation = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)


class CircleMember(models.Model):
    """One row per direction. If A and B are connected there are two rows."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="circle")
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="in_circles")
    relation = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("owner", "member")


class ShareGrant(models.Model):
    """What owner shares with viewer. Everything starts off except the rough day signal."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="grants_given")
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="grants_received")
    scores = models.BooleanField(default=False)
    tags = models.BooleanField(default=False)
    symptoms = models.BooleanField(default=False)
    water = models.BooleanField(default=False)
    cycle = models.BooleanField(default=False)
    cycle_alerts = models.BooleanField(default=False)
    rough_day = models.BooleanField(default=True)
    dates = models.BooleanField(default=False)
    emergency_card = models.BooleanField(default=False)
    medications = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("owner", "viewer")

    def flags(self):
        return {f: getattr(self, f) for f in SHARE_FIELDS}


class Nudge(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="nudges_sent")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="nudges_received")
    kind = models.CharField(max_length=20, default="thinking")  # thinking, water, hug, checkin
    message = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
