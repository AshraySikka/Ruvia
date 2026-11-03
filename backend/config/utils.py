"""Small shared helpers: encrypted text field and per user time helpers."""
import base64
import hashlib
from datetime import datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models
from django.utils import timezone


@lru_cache(maxsize=1)
def _fernet():
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        # Development fallback only. Production refuses to start without a key.
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest()).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(text):
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token):
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError, AttributeError):
        return token


class EncryptedTextField(models.TextField):
    """Stores text encrypted at rest. Not searchable in SQL by design."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return encrypt(str(value))

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        return decrypt(value)


def user_tz(user):
    try:
        return ZoneInfo(user.timezone or "America/Toronto")
    except Exception:
        return ZoneInfo("America/Toronto")


def user_now(user):
    return timezone.now().astimezone(user_tz(user))


def user_today(user):
    return user_now(user).date()


def local_dt(user, day, at=time(9, 0)):
    return datetime.combine(day, at, tzinfo=user_tz(user))


def in_quiet_hours(user, moment=None):
    moment = (moment or timezone.now()).astimezone(user_tz(user))
    start, end, now_t = user.quiet_start, user.quiet_end, moment.time()
    if start is None or end is None:
        return False
    if start <= end:
        return start <= now_t < end
    return now_t >= start or now_t < end


def next_allowed_time(user, moment):
    """Move a moment out of quiet hours to the end of quiet time."""
    if not in_quiet_hours(user, moment):
        return moment
    local = moment.astimezone(user_tz(user))
    end_today = local.replace(hour=user.quiet_end.hour, minute=user.quiet_end.minute, second=0, microsecond=0)
    if end_today <= local:
        from datetime import timedelta
        end_today = end_today + timedelta(days=1)
    return end_today
