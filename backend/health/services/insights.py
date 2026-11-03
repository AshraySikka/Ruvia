"""
Trends, baselines and pattern detection, all computed in code.
Patterns only show once there is enough data, and they show counts, not made up confidence numbers.
"""
from collections import Counter, defaultdict
from datetime import timedelta
from statistics import mean

from django.db.models import Sum

from config.utils import user_today

from .cycle import summary as cycle_summary
from .library import SYMPTOMS

MIN_DAYS = 21          # days of logs before any pattern shows
MIN_TRIGGER_DAYS = 5   # a condition must happen this many times
MIN_OUTCOME_HITS = 3   # and the symptom must appear with it this many times
MIN_LIFT = 1.6         # and be this much more common than on other days

TITLES = {
    "low_water": "low water", "short_sleep": "short sleep", "pressure_drop": "pressure drops", "humid": "humid days",
    "late_dinner": "late dinners", "period": "period days", "pre_period": "the days before a period",
    "weekend": "weekends", "sunday": "Sundays",
}
PHRASES = {
    "low_water": "days you drank under 60% of your water goal", "short_sleep": "days after less than 6 hours of sleep",
    "pressure_drop": "days the air pressure dropped 4 hPa or more", "humid": "very humid days",
    "late_dinner": "days with or after a late dinner", "period": "period days", "pre_period": "days just before a period",
    "weekend": "weekend days", "sunday": "Sundays",
}


def _days(user, start, end):
    from health.models import DailyLog, DayTag, SymptomEpisode, WaterLog, WeatherDay
    logs = {l.date: l for l in DailyLog.objects.filter(user=user, date__range=(start, end))}
    water = defaultdict(int)
    for row in WaterLog.objects.filter(user=user, date__range=(start, end)).values("date").annotate(t=Sum("amount_ml")):
        water[row["date"]] = row["t"]
    eps = defaultdict(list)
    for e in SymptomEpisode.objects.filter(user=user, date__range=(start, end)):
        eps[e.date].append(e)
    tags = defaultdict(set)
    for t in DayTag.objects.filter(user=user, date__range=(start, end)):
        tags[t.date].add(t.label)
    weather = {w.date: w for w in WeatherDay.objects.filter(user=user, date__range=(start, end))}
    return logs, water, eps, tags, weather


def series(user, days=7):
    end = user_today(user)
    start = end - timedelta(days=days - 1)
    logs, water, eps, tags, _ = _days(user, start, end)
    out = []
    d = start
    while d <= end:
        log = logs.get(d)
        s = log.scores() if log else {"physical": None, "mental": None, "overall": None}
        out.append({
            "date": d.isoformat(), "physical": s["physical"], "mental": s["mental"], "overall": s["overall"],
            "water_ml": water.get(d, 0), "sleep_hours": log.sleep_hours if log else None,
            "symptoms": [e.label for e in eps.get(d, [])],
        })
        d += timedelta(days=1)
    return out


def _avg(values):
    vals = [v for v in values if v is not None]
    return round(mean(vals), 1) if vals else None


def _window_stats(rows):
    return {
        "physical": _avg(r["physical"] for r in rows),
        "mental": _avg(r["mental"] for r in rows),
        "overall": _avg(r["overall"] for r in rows),
        "water": _avg(r["water_ml"] or None for r in rows),
        "sleep": _avg(r["sleep_hours"] for r in rows),
        "symptom_days": sum(1 for r in rows if r["symptoms"]),
        "logged_days": sum(1 for r in rows if r["overall"] is not None),
        "symptoms": Counter(s for r in rows for s in r["symptoms"]),
    }


def what_changed(user):
    rows = series(user, 14)
    prev, cur = _window_stats(rows[:7]), _window_stats(rows[7:])
    lines = []

    def compare(key, label, unit="", good_up=True, threshold=3):
        a, b = prev[key], cur[key]
        if a is None or b is None:
            return
        diff = round(b - a) if key in ("physical", "mental", "water") else round(b - a, 1)
        if abs(diff) < threshold:
            return
        up = diff > 0
        tone = "good" if up == good_up else "watch"
        word = "up" if up else "down"
        lines.append({"text": f"{label} {word} {abs(diff):g}{unit} compared with last week", "tone": tone})

    compare("physical", "Physical score", " points")
    compare("mental", "Mental score", " points")
    compare("water", "Water", " ml a day", threshold=150)
    compare("sleep", "Sleep", " hours a night", threshold=0.4)

    for label in set(prev["symptoms"]) | set(cur["symptoms"]):
        a, b = prev["symptoms"][label], cur["symptoms"][label]
        if a != b and (a >= 1 or b >= 2):
            fewer = b < a
            lines.append({
                "text": f"{label}: {b} time{'s' if b != 1 else ''} this week, {a} the week before",
                "tone": "good" if fewer else "watch",
            })
    if not lines and cur["logged_days"]:
        lines.append({"text": "A steady week. No big changes from the week before.", "tone": "neutral"})
    return {"this_week": {k: v for k, v in cur.items() if k != "symptoms"},
            "last_week": {k: v for k, v in prev.items() if k != "symptoms"}, "lines": lines[:6]}


def baseline(user):
    """Usual levels from the 28 days before this week, compared with this week."""
    rows = series(user, 35)
    base, cur = _window_stats(rows[:28]), _window_stats(rows[28:])
    if base["logged_days"] < 10:
        return {"ready": False, "needs_days": 10 - base["logged_days"]}
    notes = []
    for key, label, unit, th in [("physical", "Physical", "", 6), ("mental", "Mental", "", 6), ("water", "Water", " ml", 250), ("sleep", "Sleep", " h", 0.6)]:
        a, b = base[key], cur[key]
        if a is None or b is None:
            continue
        fa, fb = (round(a), round(b)) if key != "sleep" else (a, b)
        if b <= a - th:
            notes.append({"text": f"{label} is lower than your usual this week ({fb:g}{unit} vs {fa:g}{unit}).", "tone": "watch"})
        elif b >= a + th:
            notes.append({"text": f"{label} is higher than your usual this week ({fb:g}{unit} vs {fa:g}{unit}).", "tone": "good"})
    sym_rate = base["symptom_days"] / 4
    if cur["symptom_days"] >= sym_rate + 2:
        notes.append({"text": f"More symptom days than usual: {cur['symptom_days']} this week, about {sym_rate:.0f} in a normal week.", "tone": "watch"})
    return {"ready": True, "usual": {k: v for k, v in base.items() if k != "symptoms"},
            "this_week": {k: v for k, v in cur.items() if k != "symptoms"}, "notes": notes}


def patterns(user, days=90):
    end = user_today(user)
    start = end - timedelta(days=days - 1)
    logs, water, eps, tags, weather = _days(user, start, end)
    logged = sorted(set(logs) | set(eps) | set(water))
    if len(logged) < MIN_DAYS:
        return {"ready": False, "logged_days": len(logged), "needs_days": MIN_DAYS - len(logged), "items": []}

    goal = user.water_goal_ml or 2000
    cyc = cycle_summary(user) if user.track_cycle else {"has_data": False}
    period_days = set()
    if cyc.get("has_data"):
        from .cycle import period_days as pdays
        period_days, _ = pdays(user, start, end)

    conditions = {
        "low_water": ("Low water days", lambda d: d in logs and water.get(d, 0) < goal * 0.6),
        "short_sleep": ("Days after under 6 hours of sleep", lambda d: logs.get(d) is not None and logs[d].sleep_hours is not None and logs[d].sleep_hours < 6),
        "pressure_drop": ("Days the air pressure dropped", lambda d: d in weather and weather[d].pressure_change is not None and weather[d].pressure_change <= -4),
        "humid": ("Very humid days", lambda d: d in weather and (weather[d].humidity_mean or 0) >= 80),
        "late_dinner": ("Days after a late dinner", lambda d: "Late dinner" in tags.get(d, set()) or "Late dinner" in tags.get(d - timedelta(days=1), set())),
        "period": ("Period days", lambda d: d in period_days),
        "pre_period": ("The 3 days before a period", lambda d: any((d + timedelta(days=k)) in period_days and (d + timedelta(days=k - 1)) not in period_days for k in (1, 2, 3))),
        "weekend": ("Weekends", lambda d: d.weekday() >= 5),
        "sunday": ("Sundays", lambda d: d.weekday() == 6),
    }
    outcomes = defaultdict(set)
    for d, items in eps.items():
        for e in items:
            outcomes[e.label].add(d)
    for d, log in logs.items():
        s = log.scores()
        if s["mental"] is not None and s["mental"] <= 45:
            outcomes["Low mental score"].add(d)
        if s["physical"] is not None and s["physical"] <= 45:
            outcomes["Low physical score"].add(d)

    items = []
    for ckey, (clabel, test) in conditions.items():
        cond_days = [d for d in logged if test(d)]
        other_days = [d for d in logged if not test(d)]
        if len(cond_days) < MIN_TRIGGER_DAYS or len(other_days) < MIN_TRIGGER_DAYS:
            continue
        for olabel, odays in outcomes.items():
            if ckey == "period" and olabel == "Cramps":
                continue
            hits = sum(1 for d in cond_days if d in odays)
            other_hits = sum(1 for d in other_days if d in odays)
            if hits < MIN_OUTCOME_HITS:
                continue
            rate, base_rate = hits / len(cond_days), other_hits / len(other_days)
            lift = rate / base_rate if base_rate else float("inf")
            if lift < MIN_LIFT or rate - base_rate < 0.2:
                continue
            strength = "strong" if hits >= 6 and lift >= 2.5 else "worth watching"
            items.append({
                "condition": clabel, "outcome": olabel, "strength": strength, "title": f"{olabel} and {TITLES.get(ckey, clabel.lower())}",
                "hits": hits, "condition_days": len(cond_days),
                "other_hits": other_hits, "other_days": len(other_days),
                "text": f"{olabel} on {hits} of {len(cond_days)} {PHRASES.get(ckey, clabel.lower())}, compared with {other_hits} of {len(other_days)} other days.",
                "score": rate - base_rate,
            })
    items.sort(key=lambda x: (-x["hits"] * x["score"]))
    return {"ready": True, "logged_days": len(logged), "items": items[:6],
            "note": "These are patterns in your own logs. They show things that happen together, not what causes what."}


def streak(user):
    from health.models import DailyLog
    days = set(DailyLog.objects.filter(user=user).values_list("date", flat=True))
    today = user_today(user)
    d = today if today in days else today - timedelta(days=1)
    count = 0
    while d in days:
        count += 1
        d -= timedelta(days=1)
    last30 = sum(1 for i in range(30) if (today - timedelta(days=i)) in days)
    return {"current": count, "last_30": last30}


def symptom_history(user, key, days=180):
    from health.models import SymptomEpisode
    since = user_today(user) - timedelta(days=days)
    eps = list(SymptomEpisode.objects.filter(user=user, key=key, date__gte=since).order_by("date"))
    by_month = Counter(e.date.strftime("%b %Y") for e in eps)
    return {
        "key": key, "label": SYMPTOMS.get(key, {}).get("label", key),
        "count": len(eps), "by_month": dict(by_month),
        "severity": dict(Counter(e.severity for e in eps)),
        "triggers": Counter(t for e in eps for t in e.triggers).most_common(4),
        "avg_duration": _avg(e.duration_minutes for e in eps),
        "last": eps[-1].date.isoformat() if eps else None,
    }
