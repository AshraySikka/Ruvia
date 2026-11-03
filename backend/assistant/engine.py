"""
The check-in pipeline.

1. Safety rules run first. Crisis or red flag text gets a fixed reply, no model call.
2. A model reads the message into structured fields (with a keyword fallback).
3. Code saves the day, tags, symptoms, and decides on remedies, interactions and follow up timing.
4. A model writes a short, warm reply from those facts only (with a template fallback).
"""
import json
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from config.utils import user_now, user_today
from health.models import DailyLog, DayTag, MoodFeedback, SymptomEpisode
from health.services import extract as local
from health.services import insights
from health.services.cycle import summary as cycle_summary
from health.services.library import DOCTOR_LINE, FOLLOWUP_MINUTES, MOODS, SYMPTOMS
from health.services.remedies import suggestions_for, tried_options
from health.services.safety import CRISIS_REPLY, RED_FLAG_REPLY, screen, strip_doses
from health.services.scoring import refresh_estimates

from . import llm
from .models import ChatMessage, FollowUp

SEV_ORDER = {"mild": 1, "moderate": 2, "severe": 3, "extreme": 4}
MOOD_TAGS = {
    "everyone_hates_me": "Feeling unliked", "hate_everyone": "Irritable", "hate_myself": "Hard on self",
    "overwhelmed": "Overwhelmed", "anxious": "Anxious", "lonely": "Lonely", "sad": "Sad", "exhausted": "Drained",
    "cant_focus": "Foggy", "restless": "Restless", "cant_sleep": "Poor sleep", "good": "Good mood",
}

VOICE = (
    "You are Ruvia, a calm, kind companion inside a personal health diary app. "
    "Write like a thoughtful friend who knows a bit about health: plain words, short sentences, no jargon, no lists unless asked. "
    "Never diagnose. Never give doses or amounts of any medicine. Never suggest a medicine that is not in the allowed list you are given. "
    "Do not use em dashes or en dashes. Do not use emojis. Do not call yourself an AI or a bot. "
    "Keep it under 70 words unless told otherwise."
)

EXTRACT_SYSTEM = (
    "You read short health diary entries and return JSON only. Fields: "
    '"intent": "log" if the person describes how they feel, "ask" if they ask about their own past health, "chat" otherwise; '
    '"symptoms": list of {"key": one of [' + ", ".join(SYMPTOMS) + '], "severity": one of [mild, moderate, severe, extreme]}; '
    '"moods": list from [' + ", ".join(MOODS) + ']; '
    '"triggers": list of short phrases the person links to it, like "Late dinner", "Spicy food", "Coffee", "Poor sleep", "Stress"; '
    '"sleep_hours": number or null; '
    '"physical_estimate": 0 to 100 guess of how physically well they are today; '
    '"mental_estimate": 0 to 100 guess of how mentally well they are today. '
    "Only include symptoms that are clearly stated. Use the keys exactly."
)


def _valid_extract(data):
    return isinstance(data, dict) and isinstance(data.get("symptoms", []), list)


def read_message(text):
    data, provider = llm.complete_json(EXTRACT_SYSTEM, f"Entry: {text}", max_tokens=350, validate=_valid_extract)
    fallback = local.local_extract(text)
    if not data:
        return fallback, None
    symptoms = []
    for s in data.get("symptoms", []):
        key = s.get("key") if isinstance(s, dict) else None
        if key in SYMPTOMS:
            sev = s.get("severity") if s.get("severity") in SEV_ORDER else fallback["symptoms"][0]["severity"] if fallback["symptoms"] else "moderate"
            symptoms.append({"key": key, "label": SYMPTOMS[key]["label"], "severity": sev})
    known = {s["key"] for s in symptoms}
    symptoms += [s for s in fallback["symptoms"] if s["key"] not in known]  # keyword safety net
    moods = [m for m in data.get("moods", []) if m in MOODS] or fallback["moods"]
    triggers = [str(t)[:30].strip().capitalize() for t in data.get("triggers", []) if str(t).strip()][:4] or fallback["triggers"]
    intent = data.get("intent") if data.get("intent") in ("log", "ask", "chat") else fallback["intent"]
    if symptoms:
        intent = "log" if intent == "chat" else intent
    sleep = data.get("sleep_hours")
    sleep = sleep if isinstance(sleep, (int, float)) and 0 < sleep <= 16 else fallback["sleep_hours"]
    clamp = lambda v: max(0, min(100, int(v))) if isinstance(v, (int, float)) else None
    return {
        "intent": intent, "symptoms": symptoms, "moods": moods, "triggers": triggers, "sleep_hours": sleep,
        "physical_estimate": clamp(data.get("physical_estimate")), "mental_estimate": clamp(data.get("mental_estimate")),
    }, provider


def mood_card(user, mood_key):
    info = MOODS.get(mood_key)
    if not info:
        return None
    helped = {}
    for f in MoodFeedback.objects.filter(user=user, mood_key=mood_key):
        helped[f.activity] = helped.get(f.activity, 0) + (1 if f.helped else -1)
    options = [info["do"]] + info["more"]
    options.sort(key=lambda a: -helped.get(a, 0))
    best = options[0]
    return {
        "key": mood_key, "label": info["label"], "do": best, "why": info["why"] if best == info["do"] else
        f"You said this helped before. {info['why']}", "more": [o for o in options if o != best][:3],
        "helped_before": helped.get(best, 0) > 0,
    }


def schedule_followup(user, episode, minutes=None, round_no=1):
    from notify.services import queue
    if not user.followups_enabled:
        return None
    minutes = minutes or FOLLOWUP_MINUTES.get(episode.severity, 60)
    due = timezone.now() + timedelta(minutes=minutes)
    fu = FollowUp.objects.create(user=user, episode=episode, due_at=due, round=round_no)
    queue(user, "followup", f"How is the {episode.label.lower()} now?",
          "Tap to tell me if it is better, the same, or worse.", f"/followup/{fu.id}", due,
          payload={"followup_id": fu.id}, dedupe=f"followup:{fu.id}", respect_quiet=episode.severity in ("mild", "moderate"))
    return fu


def _apply_to_day(user, data, message):
    today = user_today(user)
    log, _ = DailyLog.objects.get_or_create(user=user, date=today)
    changed = []
    if data.get("moods"):
        log.moods = list(dict.fromkeys((log.moods or []) + data["moods"]))
        changed.append("moods")
    if data.get("sleep_hours") and log.sleep_hours is None:
        log.sleep_hours = data["sleep_hours"]
        changed.append("sleep_hours")
    if changed:
        log.save(update_fields=changed + ["updated_at"])

    tags = []
    for s in data["symptoms"]:
        tags.append(("symptom", s["label"]))
    for t in data.get("triggers", []):
        tags.append(("trigger", t))
    for m in data.get("moods", []):
        tags.append(("mood", MOOD_TAGS.get(m, m.title())))
    for kind, label in tags:
        DayTag.objects.get_or_create(user=user, date=today, label=label, defaults={"kind": kind, "source": "auto"})

    episodes = []
    for s in data["symptoms"]:
        ep = SymptomEpisode.objects.filter(user=user, key=s["key"], date=today, resolved=False).first()
        if ep:
            if SEV_ORDER[s["severity"]] > SEV_ORDER[ep.severity]:
                ep.severity = s["severity"]
            ep.triggers = list(dict.fromkeys(ep.triggers + data.get("triggers", [])))
            ep.save()
        else:
            ep = SymptomEpisode.objects.create(
                user=user, key=s["key"], label=s["label"], date=today, severity=s["severity"],
                started_at=timezone.now(), triggers=data.get("triggers", []), message=message,
            )
        episodes.append(ep)

    if data.get("physical_estimate") is not None or data.get("mental_estimate") is not None:
        refresh_estimates(log)
        log.refresh_from_db()
        # Blend the model guess with the rule based one so a single read cannot swing it far.
        for field, guess in (("physical_estimate", data.get("physical_estimate")), ("mental_estimate", data.get("mental_estimate"))):
            rule = getattr(log, field)
            if guess is not None and rule is not None:
                setattr(log, field, round((rule * 2 + guess) / 3))
        log.save(update_fields=["physical_estimate", "mental_estimate", "updated_at"])
    else:
        refresh_estimates(log)
    return log, episodes, [label for _, label in tags]


def _reply_prompt(context):
    return (
        "Write the reply to this diary entry using only these facts. "
        "Open with one short line that acknowledges how they feel. "
        "If history shows something helped before, mention it first. "
        "Then name one or two home remedies, then mention the allowed over the counter options by name only if there are any. "
        "End by saying you will check back in the stated number of minutes if a follow up is set. "
        "The app shows full lists in cards under your message, so do not list everything.\n\n"
        f"FACTS:\n{json.dumps(context, default=str)}"
    )


def _soft(item):
    """Lowercase the first letter of a home remedy, but leave brand names alone."""
    from health.services.library import OTC
    brands = {b.lower() for o in OTC.values() for b in o["brands"]}
    return item if item.lower() in brands else item[0].lower() + item[1:]


def _template_reply(context):
    parts = []
    sug = context.get("suggestions") or []
    mood = context.get("mood")
    if sug:
        s = sug[0]
        parts.append(f"Sorry about the {s['label'].lower()}.")
        helped = [h["item"] for h in s["history"].get("helped", [])][:2]
        if helped:
            parts.append(f"What has worked for you before: {' and '.join(_soft(h) for h in helped)}. Start there.")
        else:
            parts.append(f"Start with this: {_soft(s['home'][0])}.")
        if s["otc"]:
            names = [o["brands"][0] if o["brands"] else o["name"] for o in s["otc"][:2]]
            parts.append(f"If you need more, {' or '.join(names)} {'are options that fit' if len(names) > 1 else 'is an option that fits'} with what you take.")
    elif mood:
        parts.append(f"That is a heavy feeling. Best move right now: {_soft(mood['do'])}. {mood['why']}")
    else:
        parts.append("Thanks for checking in. I saved it to today.")
    if context.get("followup_minutes"):
        parts.append(f"I will check on you in about {context['followup_minutes']} minutes.")
    return " ".join(parts)


def _serialize(m):
    return {"id": m.id, "role": m.role, "kind": m.kind, "text": m.text, "source": m.source,
            "payload": m.payload, "created_at": m.created_at.isoformat()}


@transaction.atomic
def handle_message(user, text, source="text", mode="auto", client_id=""):
    text = (text or "").strip()[:2000]
    if client_id:
        dup = ChatMessage.objects.filter(user=user, client_id=client_id, role="user").first()
        if dup:
            reply = ChatMessage.objects.filter(user=user, role="assistant", created_at__gte=dup.created_at).first()
            return {"messages": [_serialize(dup)] + ([_serialize(reply)] if reply else [])}

    flag, reasons = screen(text)
    user_msg = ChatMessage.objects.create(user=user, role="user", text=text, source=source, client_id=client_id,
                                          kind="safety" if flag else "checkin")

    if flag == "crisis":
        reply = ChatMessage.objects.create(user=user, role="assistant", kind="safety", text=CRISIS_REPLY, payload={
            "type": "crisis",
            "resources": [
                {"label": "Call 9-8-8", "href": "tel:988"}, {"label": "Text 9-8-8", "href": "sms:988"},
                {"label": "Call 911", "href": "tel:911"},
            ],
        })
        return {"messages": [_serialize(user_msg), _serialize(reply)]}

    if flag == "red_flag":
        data = local.local_extract(text)
        for s in data["symptoms"]:
            s["severity"] = "severe" if s["severity"] in ("mild", "moderate") else s["severity"]
        log, episodes, tags = _apply_to_day(user, data, user_msg)
        if episodes:
            schedule_followup(user, episodes[0], minutes=30)
        reply = ChatMessage.objects.create(user=user, role="assistant", kind="safety", text=RED_FLAG_REPLY, payload={
            "type": "urgent", "reasons": reasons, "tags": tags,
            "resources": [{"label": "Call 911", "href": "tel:911"}, {"label": "Health811", "href": "tel:811"}],
        })
        return {"messages": [_serialize(user_msg), _serialize(reply)], "scores": log.scores()}

    if mode == "ask" or (mode == "auto" and local.detect_intent(text) == "ask"):
        user_msg.kind = "ask"
        user_msg.save(update_fields=["kind"])
        from .history import answer
        return answer(user, text, user_msg)

    data, provider = read_message(text)
    if mode == "auto" and data["intent"] == "ask":
        user_msg.kind = "ask"
        user_msg.save(update_fields=["kind"])
        from .history import answer
        return answer(user, text, user_msg)

    log, episodes, tags = _apply_to_day(user, data, user_msg)

    suggestions = [s for s in (suggestions_for(user, ep.key, ep.severity) for ep in
                               sorted(episodes, key=lambda e: -SEV_ORDER[e.severity])[:2]) if s]
    mood = mood_card(user, data["moods"][0]) if data.get("moods") else None
    followup = None
    if episodes:
        worst = max(episodes, key=lambda e: SEV_ORDER[e.severity])
        followup = schedule_followup(user, worst)

    context = {
        "entry": text,
        "suggestions": [{
            "label": s["label"], "severity": s["severity"], "history": s["history"],
            "home": s["home"][:3], "allowed_otc": [{"name": o["name"], "brands": o["brands"], "caution": o["reasons"]} for o in s["otc"]],
        } for s in suggestions],
        "mood": mood,
        "followup_minutes": FOLLOWUP_MINUTES.get(followup.episode.severity) if followup else None,
        "time_of_day": user_now(user).strftime("%H:%M"),
    }
    reply_text, reply_provider = llm.complete(VOICE, _reply_prompt(context), max_tokens=260)
    if not reply_text:
        reply_text = _template_reply({**context, "suggestions": suggestions})
    reply_text = strip_doses(reply_text)

    payload = {
        "type": "checkin",
        "tags": tags,
        "scores": log.scores(),
        "episodes": [{"id": e.id, "key": e.key, "label": e.label, "severity": e.severity} for e in episodes],
        "suggestions": suggestions,
        "mood": mood,
        "followup": {"id": followup.id, "due_at": followup.due_at.isoformat()} if followup else None,
        "tried_options": tried_options(suggestions[0]) if suggestions else [],
        "doctor_line": DOCTOR_LINE if any(s["otc"] for s in suggestions) else None,
    }
    reply = ChatMessage.objects.create(user=user, role="assistant", kind="checkin", text=reply_text, payload=payload,
                                       provider=reply_provider or provider or "local")
    return {"messages": [_serialize(user_msg), _serialize(reply)], "scores": log.scores()}


FOLLOWUP_USER_TEXT = {"better": "Feeling better", "same": "About the same", "worse": "Feeling worse"}


@transaction.atomic
def answer_followup(user, fu, answer, tried=None, note=""):
    ep = fu.episode
    tried = [t for t in (tried or []) if isinstance(t, str) and t.strip()][:8]
    if tried:
        ep.tried = list(dict.fromkeys(ep.tried + tried))
    fu.status, fu.answer, fu.answered_at = "answered", answer, timezone.now()
    fu.save()
    ep.outcome = answer
    if answer == "better":
        ep.resolved = True
        ep.ended_at = timezone.now()
        ep.duration_minutes = max(1, int((ep.ended_at - ep.started_at).total_seconds() // 60))
    if note:
        ep.note = (ep.note + "\n" if ep.note else "") + note[:500]
    ep.save()

    user_msg = ChatMessage.objects.create(user=user, role="user", kind="followup",
                                          text=FOLLOWUP_USER_TEXT[answer] + (f". Tried: {', '.join(tried)}" if tried else ""))
    sug = suggestions_for(user, ep.key, ep.severity)
    payload = {"type": "followup", "answer": answer, "episode": {"id": ep.id, "label": ep.label}}
    if answer == "better":
        helped = " and ".join(_soft(t) for t in tried[:2])
        text = (f"Really glad it eased. I saved what helped ({helped}) so it comes first next time." if tried
                else "Really glad it eased. Next time, tap what you tried so I can remember what works for you.")
    elif answer == "same":
        untried = [h for h in (sug["home"] if sug else []) if h not in ep.tried]
        text = "Thanks for letting me know. Some things take a little longer. "
        text += f"If you have not yet, try this: {untried[0].lower()}." if untried else "Give it a bit more time and rest if you can."
        payload["suggestions"] = [sug] if sug else []
        if fu.round < 3:
            nxt = schedule_followup(user, ep, minutes=90, round_no=fu.round + 1)
            if nxt:
                payload["followup"] = {"id": nxt.id, "due_at": nxt.due_at.isoformat()}
                text += " I will check again in about an hour and a half."
    else:
        text = ("I'm sorry it is getting worse. If it keeps building, or anything new and scary shows up, call Health811 at 811 "
                "to talk to a nurse, or 911 if it feels severe. ")
        if sug and sug.get("doctor_if"):
            text += f"Get care soon if {sug['doctor_if']}."
        payload["suggestions"] = [sug] if sug else []
        payload["resources"] = [{"label": "Health811", "href": "tel:811"}, {"label": "Call 911", "href": "tel:911"}]
        if fu.round < 3:
            nxt = schedule_followup(user, ep, minutes=45, round_no=fu.round + 1)
            if nxt:
                payload["followup"] = {"id": nxt.id, "due_at": nxt.due_at.isoformat()}
    payload["tried_options"] = tried_options(sug)
    reply = ChatMessage.objects.create(user=user, role="assistant", kind="followup", text=text, payload=payload)
    return {"messages": [_serialize(user_msg), _serialize(reply)], "episode_outcome": ep.outcome}


def rough_day_message(user):
    msg = ChatMessage.objects.create(
        user=user, role="assistant", kind="rough_day",
        text="Rough day noted. No questions. Drink some water, eat something small, and go easy on yourself tonight.",
        payload={"type": "rough_day"},
    )
    return _serialize(msg)


def serialize_message(m):
    return _serialize(m)
