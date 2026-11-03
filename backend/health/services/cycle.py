"""Cycle predictions from logged period starts. Simple averages, shown as estimates."""
from datetime import date, timedelta
from statistics import mean

from .library import CYCLE_TIPS

DEFAULT_CYCLE = 28
DEFAULT_PERIOD = 5


def summary(user, today=None):
    from config.utils import user_today
    today = today or user_today(user)
    entries = list(user.cycles.order_by("start_date"))
    if not entries:
        return {"has_data": False, "enabled": user.track_cycle}

    starts = [e.start_date for e in entries]
    gaps = [(b - a).days for a, b in zip(starts, starts[1:]) if 15 <= (b - a).days <= 60]
    cycle_len = round(mean(gaps[-6:])) if gaps else DEFAULT_CYCLE
    lengths = [((e.end_date - e.start_date).days + 1) for e in entries if e.end_date and 1 <= (e.end_date - e.start_date).days + 1 <= 10]
    period_len = round(mean(lengths[-6:])) if lengths else DEFAULT_PERIOD
    variability = (max(gaps[-6:]) - min(gaps[-6:])) if len(gaps) >= 2 else None

    last = entries[-1]
    next_start = last.start_date + timedelta(days=cycle_len)
    while next_start + timedelta(days=3) < today:
        next_start += timedelta(days=cycle_len)
    day_in_cycle = (today - last.start_date).days + 1
    ovulation_day = max(cycle_len - 14, 8)

    on_period = last.end_date is None and day_in_cycle <= 8 or (last.end_date and last.start_date <= today <= last.end_date)
    if on_period:
        phase = "menstrual"
    elif day_in_cycle <= period_len:
        phase = "menstrual"
    elif day_in_cycle < ovulation_day - 1:
        phase = "follicular"
    elif day_in_cycle <= ovulation_day + 1:
        phase = "ovulation"
    else:
        phase = "luteal"
    days_until = (next_start - today).days
    tips_key = "pre_period" if phase == "luteal" and 0 <= days_until <= 4 else phase
    late = days_until < 0 and not on_period

    return {
        "has_data": True,
        "enabled": user.track_cycle,
        "cycle_length": cycle_len,
        "period_length": period_len,
        "variability_days": variability,
        "last_start": last.start_date.isoformat(),
        "on_period": bool(on_period),
        "day_in_cycle": day_in_cycle,
        "phase": phase,
        "phase_title": CYCLE_TIPS[tips_key]["title"],
        "tips": CYCLE_TIPS[tips_key]["tips"],
        "next_start": next_start.isoformat(),
        "window_start": (next_start - timedelta(days=2)).isoformat(),
        "window_end": (next_start + timedelta(days=2)).isoformat(),
        "days_until": days_until,
        "late_by": -days_until if late else 0,
        "ovulation_estimate": (last.start_date + timedelta(days=ovulation_day - 1)).isoformat(),
        "logged_cycles": len(entries),
        "phases": [
            {"key": "menstrual", "start": 1, "end": period_len},
            {"key": "follicular", "start": period_len + 1, "end": ovulation_day - 2},
            {"key": "ovulation", "start": ovulation_day - 1, "end": ovulation_day + 1},
            {"key": "luteal", "start": ovulation_day + 2, "end": cycle_len},
        ],
    }


def period_days(user, start, end):
    """Actual and predicted period days in a range, for the calendar."""
    actual, predicted = set(), set()
    for e in user.cycles.filter(start_date__lte=end):
        stop = e.end_date or (e.start_date + timedelta(days=DEFAULT_PERIOD - 1))
        d = e.start_date
        while d <= stop:
            if start <= d <= end:
                actual.add(d)
            d += timedelta(days=1)
    s = summary(user)
    if s.get("has_data"):
        nxt = date.fromisoformat(s["next_start"])
        for _ in range(3):
            for i in range(s["period_length"]):
                d = nxt + timedelta(days=i)
                if start <= d <= end and d not in actual and d >= date.fromisoformat(s["last_start"]) + timedelta(days=10):
                    predicted.add(d)
            nxt += timedelta(days=s["cycle_length"])
    return actual, predicted
