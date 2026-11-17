"""
Runs every few minutes from a cron job. Safe to run as often as you like: every reminder has a dedupe key.
"""
import logging
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone

from config.utils import user_tz

from .services import deliver_due, queue

log = logging.getLogger(__name__)
WINDOW = timedelta(minutes=45)


def _slot_now(local_now, slot_time):
    slot = local_now.replace(hour=slot_time.hour, minute=slot_time.minute, second=0, microsecond=0)
    return slot <= local_now < slot + WINDOW, slot


def _checkin_slots(user):
    base = datetime.combine(datetime.today(), user.first_checkin_time)
    return [(base + timedelta(hours=user.checkin_interval_hours * i)).time() for i in range(user.checkins_per_day)
            if (base + timedelta(hours=user.checkin_interval_hours * i)).date() == base.date()]


def plan_user(user, now):
    from assistant.models import ChatMessage
    from health.models import HealthDate, WaterLog
    from health.services.cycle import summary as cycle_summary

    local = now.astimezone(user_tz(user))
    today = local.date()
    created = 0

    # Daily check-ins
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    checked_in = ChatMessage.objects.filter(user=user, role="user", created_at__gte=midnight).exists()
    for i, t in enumerate(_checkin_slots(user)):
        hit, slot = _slot_now(local, t)
        if hit:
            title = "How are you today?" if not checked_in else "Quick check-in"
            body = ("Tell me in a sentence or a voice note. It takes ten seconds." if not checked_in
                    else "How is the rest of your day going?")
            if queue(user, "checkin", title, body, "/chat", now, dedupe=f"checkin:{user.id}:{today}:{i}"):
                created += 1

    # Water, only when behind the pace for the day
    if user.water_reminders and user.water_interval_hours:
        start = datetime.combine(today, user.quiet_end, tzinfo=local.tzinfo)
        end = datetime.combine(today, user.quiet_start, tzinfo=local.tzinfo)
        if end <= start:
            end += timedelta(days=1)
        slot = start + timedelta(hours=user.water_interval_hours)
        n = 0
        while slot < end:
            if slot <= local < slot + WINDOW:
                drank = WaterLog.objects.filter(user=user, date=today).aggregate(t=Sum("amount_ml"))["t"] or 0
                pace = user.water_goal_ml * (slot - start).total_seconds() / (end - start).total_seconds()
                if drank < pace - 200:
                    queue(user, "water", f"{drank} ml so far today",
                          f"A glass now keeps you on track for {user.water_goal_ml} ml.", "/?water=1", now,
                          dedupe=f"water:{user.id}:{today}:{n}")
                    created += 1
            slot += timedelta(hours=user.water_interval_hours)
            n += 1

    # Cycle heads up and the 'did it start?' question
    if user.track_cycle and user.cycle_notifications:
        c = cycle_summary(user, today)
        if c.get("has_data"):
            if c["days_until"] == 2:
                if queue(user, "cycle", "Period likely in 2 days", "Walk today and eat protein with breakfast. It may help with cramps.",
                         "/cycle", now, dedupe=f"cycle_soon:{user.id}:{c['next_start']}"):
                    created += 1
                    notify_circle_cycle(user, c)
            hit, _ = _slot_now(local, datetime.strptime("09:00", "%H:%M").time())
            if hit and c["days_until"] <= 0 and not c["on_period"] and c["late_by"] <= 10:
                if queue(user, "cycle", "Did your period start today?", "Tap to let me know. It keeps the predictions honest.",
                         "/cycle?confirm=1", now, payload={"actions_key": "cycle_confirm"}, dedupe=f"cycle_confirm:{user.id}:{today}"):
                    created += 1

    # Health dates, the evening before
    hit, _ = _slot_now(local, datetime.strptime("18:00", "%H:%M").time())
    if hit:
        for d in HealthDate.objects.filter(user=user, date=today + timedelta(days=1)):
            when = f" at {d.time.strftime('%-I:%M %p')}" if d.time else ""
            queue(user, "date", f"Tomorrow: {d.title}", f"{d.get_kind_display()}{when}. Your doctor summary is in Me if you need it.",
                  "/care?tab=dates", now, dedupe=f"date:{d.id}")
        if local.weekday() == 6 and user.weekly_summary:
            queue(user, "weekly", "Your week in Ruvia", "See what changed this week.", "/insights", now,
                  dedupe=f"weekly:{user.id}:{today}")

    # Weather once a day
    hit, _ = _slot_now(local, datetime.strptime("07:00", "%H:%M").time())
    if hit and user.latitude is not None:
        from health.services.weather import sync_weather
        sync_weather(user, past_days=3)
    return created


def notify_circle_cycle(user, c):
    from care.models import ShareGrant
    for grant in ShareGrant.objects.filter(owner=user, cycle=True, cycle_alerts=True).select_related("viewer"):
        queue(grant.viewer, "care", f"{user.display_name}'s period is likely in 2 days",
              "A heating pad, snacks and patience go a long way.", f"/care/person/{user.id}", timezone.now(),
              dedupe=f"cycle_soon_circle:{grant.viewer_id}:{user.id}:{c['next_start']}")


def expire_followups(now):
    from assistant.models import FollowUp
    return FollowUp.objects.filter(status="pending", due_at__lt=now - timedelta(hours=24)).update(status="expired")


def run_tick(now=None):
    now = now or timezone.now()
    User = get_user_model()
    planned = 0
    for user in User.objects.filter(is_active=True, email_verified=True, onboarded=True):
        try:
            planned += plan_user(user, now)
        except Exception as exc:
            log.exception("Planning failed for user %s: %s", user.pk, exc)
    delivered = deliver_due(now)
    expired = expire_followups(now)
    return {"planned": planned, "delivered": delivered, "expired_followups": expired, "at": now.isoformat()}
