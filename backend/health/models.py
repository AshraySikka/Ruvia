from django.conf import settings
from django.db import models
from django.utils import timezone

from config.utils import EncryptedTextField

User = settings.AUTH_USER_MODEL

SEVERITY_CHOICES = [("mild", "Mild"), ("moderate", "Moderate"), ("severe", "Severe"), ("extreme", "Extreme")]
OUTCOME_CHOICES = [("unknown", "Not answered"), ("better", "Better"), ("same", "Same"), ("worse", "Worse")]


class DailyLog(models.Model):
    """One row per person per day. Ratings are self-rated on a 0 to 10 scale."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="days")
    date = models.DateField()
    physical_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    mental_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    physical_estimate = models.PositiveSmallIntegerField(null=True, blank=True)
    mental_estimate = models.PositiveSmallIntegerField(null=True, blank=True)
    sleep_hours = models.FloatField(null=True, blank=True)
    moods = models.JSONField(default=list, blank=True)
    rough_day = models.BooleanField(default=False)
    note = EncryptedTextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]

    def scores(self):
        from .services.scoring import day_scores
        return day_scores(self)


class WaterLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="water_logs")
    date = models.DateField(db_index=True)
    amount_ml = models.PositiveIntegerField()
    logged_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-logged_at"]


class DayTag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tags")
    date = models.DateField(db_index=True)
    label = models.CharField(max_length=40)
    kind = models.CharField(max_length=12, default="symptom")  # symptom, mood, trigger, note
    source = models.CharField(max_length=10, default="auto")  # auto or manual
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "date", "label")
        ordering = ["created_at"]


class SymptomEpisode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="episodes")
    key = models.CharField(max_length=40, db_index=True)
    label = models.CharField(max_length=60)
    date = models.DateField(db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="moderate")
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    triggers = models.JSONField(default=list, blank=True)
    tried = models.JSONField(default=list, blank=True)
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES, default="unknown")
    resolved = models.BooleanField(default=False)
    note = EncryptedTextField(blank=True, default="")
    message = models.ForeignKey("assistant.ChatMessage", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]


class Medication(models.Model):
    KINDS = [("prescribed", "Prescribed"), ("otc", "Over the counter"), ("supplement", "Supplement")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medications")
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, choices=KINDS, default="prescribed")
    dose_text = models.CharField(max_length=120, blank=True)
    frequency = models.CharField(max_length=120, blank=True)
    start_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-active", "name"]


class MedLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="med_logs")
    medication = models.ForeignKey(Medication, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    taken_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-taken_at"]


class Allergy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="allergies")
    substance = models.CharField(max_length=120)
    reaction = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["substance"]


class CabinetItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cabinet")
    name = models.CharField(max_length=120)
    note = models.CharField(max_length=200, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    running_low = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]


class CycleEntry(models.Model):
    FLOW = [("light", "Light"), ("medium", "Medium"), ("heavy", "Heavy")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cycles")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    flow = models.CharField(max_length=10, choices=FLOW, default="medium")
    pain = models.PositiveSmallIntegerField(null=True, blank=True)
    on_time = models.BooleanField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-start_date"]


class CyclePrompt(models.Model):
    """Tracks 'did your period start today?' questions so we do not repeat them."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cycle_prompts")
    predicted_date = models.DateField()
    asked_on = models.DateField()
    answer = models.CharField(max_length=10, blank=True)  # yes, not_yet

    class Meta:
        unique_together = ("user", "asked_on")


class HealthDate(models.Model):
    KINDS = [("appointment", "Appointment"), ("test", "Test"), ("renewal", "Prescription renewal"),
             ("vaccine", "Vaccine"), ("checkup", "Checkup"), ("other", "Other")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="health_dates")
    title = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, choices=KINDS, default="appointment")
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=160, blank=True)
    notes = models.CharField(max_length=300, blank=True)
    shared = models.BooleanField(default=True)

    class Meta:
        ordering = ["date", "time"]


class EmergencyCard(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="emergency_card")
    full_name = models.CharField(max_length=120, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    blood_type = models.CharField(max_length=6, blank=True)
    conditions = models.TextField(blank=True)
    contacts = models.JSONField(default=list, blank=True)
    doctor = models.CharField(max_length=160, blank=True)
    health_card_note = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class WeatherDay(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="weather")
    date = models.DateField()
    temp_max = models.FloatField(null=True)
    temp_min = models.FloatField(null=True)
    pressure_mean = models.FloatField(null=True)
    pressure_change = models.FloatField(null=True)
    humidity_mean = models.FloatField(null=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]


class Goal(models.Model):
    title = models.CharField(max_length=80)
    emoji = models.CharField(max_length=8, default="")
    unit = models.CharField(max_length=20, default="times")
    target = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="goals_created")
    members = models.ManyToManyField(User, related_name="goals")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class GoalCheck(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="checks")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    value = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("goal", "user", "date")


class MoodFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mood_feedback")
    mood_key = models.CharField(max_length=40)
    activity = models.CharField(max_length=120)
    helped = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
