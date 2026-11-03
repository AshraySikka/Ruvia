"""Ask My Health History: answers come from the person's own records, gathered in code first."""
import json
import re
from collections import Counter
from datetime import timedelta

from config.utils import user_today
from health.models import DailyLog
from health.services import extract as local
from health.services import insights
from health.services.cycle import summary as cycle_summary
from health.services.remedies import history_for

from . import llm
from .models import ChatMessage

ANSWER_SYSTEM = (
    "You are Ruvia, a calm companion in a personal health diary. Answer the person's question using ONLY the facts given, "
    "which come from their own diary. Speak to them directly, plain and warm, under 110 words. "
    "If the facts do not answer the question, say what is missing and what to log so you can answer next time. "
    "Say 'in your logs' rather than claiming medical causes. Never diagnose, never give doses. "
    "Do not use em dashes or en dashes. No emojis. Do not call yourself an AI."
)


def _window(text):
    t = text.lower()
    if "this week" in t or "past week" in t or "last 7" in t:
        return 7, "the last 7 days"
    if "last month" in t or "past month" in t or "this month" in t or "lately" in t or "recently" in t:
        return 30, "the last 30 days"
    if "year" in t:
        return 365, "the last year"
    return 90, "the last 3 months"


def gather(user, text):
    days, label = _window(text)
    t = text.lower()
    keys = local.find_symptoms(text)
    if not keys and ("tired" in t or "energy" in t):
        keys = ["fatigue"]
    facts = {"period": label}

    rows = insights.series(user, days)
    phys = [r["physical"] for r in rows if r["physical"] is not None]
    ment = [r["mental"] for r in rows if r["mental"] is not None]
    sleep = [r["sleep_hours"] for r in rows if r["sleep_hours"] is not None]
    water = [r["water_ml"] for r in rows if r["water_ml"]]
    facts["averages"] = {
        "physical_pct": round(sum(phys) / len(phys)) if phys else None,
        "mental_pct": round(sum(ment) / len(ment)) if ment else None,
        "sleep_hours": round(sum(sleep) / len(sleep), 1) if sleep else None,
        "water_ml": round(sum(water) / len(water)) if water else None,
        "days_logged": len(phys) or len(ment),
    }
    facts["symptom_counts"] = dict(Counter(s for r in rows for s in r["symptoms"]).most_common(6))

    for key in keys[:2]:
        h = insights.symptom_history(user, key, days)
        h["what_helped"] = history_for(user, key)
        facts.setdefault("symptoms", []).append(h)

    if any(w in t for w in ("tired", "energy", "sleep", "why", "feeling", "changed", "lately")):
        facts["what_changed"] = [l["text"] for l in insights.what_changed(user)["lines"]]
        b = insights.baseline(user)
        if b.get("ready"):
            facts["compared_to_usual"] = [n["text"] for n in b["notes"]]
        low_sleep = [r for r in rows[-14:] if r["sleep_hours"] is not None and r["sleep_hours"] < 6.5]
        facts["short_sleep_nights_last_14"] = len(low_sleep)

    pats = insights.patterns(user)
    if pats.get("ready") and pats["items"]:
        rel = [p for p in pats["items"] if not keys or any(k.replace("_", " ") in p["outcome"].lower() for k in keys)] or pats["items"]
        facts["patterns"] = [p["text"] for p in rel[:3]]
    elif not pats.get("ready"):
        facts["patterns_note"] = f"Patterns need about {pats['needs_days']} more days of logs."

    if user.track_cycle and any(w in t for w in ("period", "cycle", "cramp", "pms", "ovulat")):
        c = cycle_summary(user)
        if c.get("has_data"):
            facts["cycle"] = {k: c[k] for k in ("cycle_length", "period_length", "next_start", "phase", "days_until", "logged_cycles")}

    if "doctor" in t or "appointment" in t or "discuss" in t:
        facts["medicines"] = list(user.medications.filter(active=True).values_list("name", flat=True))
        facts["top_symptoms"] = facts["symptom_counts"]
        worse = user.episodes.filter(outcome="worse", date__gte=user_today(user) - timedelta(days=days))
        facts["got_worse"] = list(worse.values_list("label", flat=True).distinct())
        facts["upcoming"] = [f"{d.title} on {d.date}" for d in user.health_dates.filter(date__gte=user_today(user))[:3]]
    return facts, keys


def _template(facts, keys):
    parts = []
    for s in facts.get("symptoms", []):
        if s["count"]:
            parts.append(f"You logged {s['label'].lower()} {s['count']} time{'s' if s['count'] != 1 else ''} in {facts['period']}.")
            helped = s["what_helped"]["helped"]
            if helped:
                from .engine import _soft
                parts.append("What helped most: " + ", ".join(f"{_soft(h['item'])} ({h['times']} times)" for h in helped[:3]) + ".")
            if s["triggers"]:
                parts.append("It often came with " + ", ".join(t.lower() for t, _ in s["triggers"][:2]) + ".")
        elif s["key"] != "fatigue":
            parts.append(f"I could not find {s['label'].lower()} in your logs for {facts['period']}.")
    if facts.get("what_changed"):
        parts.append(". ".join(facts["what_changed"][:3]) + ".")
    if facts.get("short_sleep_nights_last_14"):
        n = facts["short_sleep_nights_last_14"]
        parts.append(f"You had {n} short night{'s' if n != 1 else ''} of sleep in the last two weeks, which often shows up as tiredness.")
    if facts.get("patterns"):
        parts.append("A pattern in your logs: " + facts["patterns"][0])
    if facts.get("medicines") is not None:
        parts.append("For your appointment, I would bring up: " + ", ".join(facts.get("top_symptoms", {}).keys() or ["how you have been feeling"]) + ". The doctor summary PDF in Me has the details.")
    if not parts:
        a = facts["averages"]
        parts.append(f"Over {facts['period']} your physical average was {a['physical_pct'] or 'not logged'} and mental {a['mental_pct'] or 'not logged'}.")
    return re.sub(r"\.\.", ".", " ".join(parts))


def answer(user, text, user_msg):
    from .engine import _serialize
    facts, keys = gather(user, text)
    prompt = f"Question: {text}\n\nFACTS FROM THEIR DIARY:\n{json.dumps(facts, default=str)}"
    reply, provider = llm.complete(ANSWER_SYSTEM, prompt, max_tokens=320)
    reply = reply or _template(facts, keys)
    cards = []
    for s in facts.get("symptoms", []):
        cards.append({"label": s["label"], "count": s["count"], "by_month": s["by_month"],
                      "helped": s["what_helped"]["helped"], "triggers": [t for t, _ in s["triggers"]]})
    msg = ChatMessage.objects.create(user=user, role="assistant", kind="ask", text=reply, provider=provider or "local",
                                     payload={"type": "history", "cards": cards, "patterns": facts.get("patterns", []),
                                              "period": facts["period"]})
    return {"messages": [_serialize(user_msg), _serialize(msg)]}
