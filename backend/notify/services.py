import json
import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from config.utils import in_quiet_hours, next_allowed_time

from .models import Notification, PushSubscription

log = logging.getLogger(__name__)


def queue(user, kind, title, body="", url="/", send_at=None, payload=None, dedupe=None, respect_quiet=True):
    try:
        n, _ = Notification.objects.get_or_create(
            dedupe_key=dedupe, defaults={
                "user": user, "kind": kind, "title": title[:120], "body": body[:300], "url": url,
                "send_at": send_at or timezone.now(), "payload": payload or {}, "respect_quiet": respect_quiet,
            },
        ) if dedupe else (Notification.objects.create(
            user=user, kind=kind, title=title[:120], body=body[:300], url=url,
            send_at=send_at or timezone.now(), payload=payload or {}, respect_quiet=respect_quiet), True)
        return n
    except IntegrityError:
        return None


def push(user, title, body, url="/", tag=None, actions=None):
    if not (settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY):
        return 0
    from pywebpush import WebPushException, webpush
    data = json.dumps({"title": title, "body": body, "url": url, "tag": tag or url, "actions": actions or []})
    sent = 0
    for sub in user.push_subscriptions.all():
        try:
            webpush(
                subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                data=data, vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT}, ttl=60 * 60 * 6,
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                sub.delete()
            else:
                log.warning("Push failed for %s: %s", user.pk, exc)
        except Exception as exc:  # network trouble should never break the scheduler
            log.warning("Push error for %s: %s", user.pk, exc)
    return sent


ACTIONS = {
    "followup": [{"action": "better", "title": "Better"}, {"action": "same", "title": "Same"}, {"action": "worse", "title": "Worse"}],
    "cycle_confirm": [{"action": "yes", "title": "Yes, it started"}, {"action": "not_yet", "title": "Not yet"}],
    "water": [{"action": "water250", "title": "+250 ml"}],
}


def deliver_due(now=None, limit=500):
    now = now or timezone.now()
    due = Notification.objects.filter(sent_at__isnull=True, cancelled=False, send_at__lte=now).select_related("user")[:limit]
    delivered = 0
    for n in due:
        if n.respect_quiet and in_quiet_hours(n.user, now):
            n.send_at = next_allowed_time(n.user, now)
            n.save(update_fields=["send_at"])
            continue
        if n.kind == "water" and n.send_at < now - timedelta(hours=2):
            n.cancelled = True  # stale water nudges are noise
            n.save(update_fields=["cancelled"])
            continue
        push(n.user, n.title, n.body, n.url, tag=f"{n.kind}-{n.id}", actions=ACTIONS.get(n.payload.get("actions_key", n.kind)))
        n.sent_at = now
        n.save(update_fields=["sent_at"])
        delivered += 1
    return delivered
