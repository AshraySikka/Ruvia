"""Keyword based reading of a check-in. Used when no model is reachable, and to sanity check model output."""
import re

from .library import MOODS, SEVERITY_WORDS, SYMPTOMS, TRIGGER_WORDS

QUESTION_STARTS = ("what", "why", "how", "when", "is my", "am i", "did i", "do i", "have i", "has my",
                   "show me", "tell me", "which", "was my", "were my", "should i discuss", "what should i")
HISTORY_HINTS = ("last time", "usually", "lately", "this month", "last month", "this week", "my history",
                 "before", "pattern", "trend", "how often", "frequency", "increasing", "changed", "compare")


def _contains(text, phrase):
    return re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", text) is not None


def find_symptoms(text):
    t = text.lower()
    found = []
    for key, info in SYMPTOMS.items():
        if any(_contains(t, w) for w in info["words"]):
            found.append(key)
    # Specific beats general
    if "cramps" in found and "stomach_ache" in found:
        found.remove("stomach_ache")
    if "low_mood" in found and "stress" in found and "sad" not in t:
        found.remove("low_mood")
    return found


def find_severity(text):
    t = text.lower()
    for level, words in SEVERITY_WORDS:
        if any(_contains(t, w) for w in words):
            return level
    return "moderate"


def find_moods(text):
    t = text.lower()
    hits = [key for key, info in MOODS.items() if any(_contains(t, w) for w in info["words"])]
    # The three internet rules are more specific than general moods
    specific = {"everyone_hates_me", "hate_everyone", "hate_myself"}
    if specific & set(hits):
        hits = [h for h in hits if h in specific] + [h for h in hits if h not in specific and h != "sad"]
    return hits[:3]


def find_triggers(text):
    t = text.lower()
    return [label for label, words in TRIGGER_WORDS.items() if any(_contains(t, w) for w in words)]


def find_sleep(text):
    m = re.search(r"(\d+(\.\d)?)\s?(hours?|hrs?|h)\s?(of )?sleep|slept (for )?(\d+(\.\d)?)\s?(hours?|hrs?|h)", text.lower())
    if not m:
        return None
    value = m.group(1) or m.group(6)
    try:
        v = float(value)
        return v if 0 < v <= 16 else None
    except (TypeError, ValueError):
        return None


def detect_intent(text):
    t = text.strip().lower()
    if t.endswith("?") or t.startswith(QUESTION_STARTS):
        if any(h in t for h in HISTORY_HINTS) or t.startswith(("what helped", "why have i", "how has", "is my", "what should i discuss", "how often")):
            return "ask"
        if not find_symptoms(t):
            return "ask"
    return "log"


def local_extract(text):
    symptoms = find_symptoms(text)
    severity = find_severity(text)
    moods = find_moods(text)
    if "stress" in symptoms and not moods:
        moods = ["anxious"] if "anx" in text.lower() else ["overwhelmed"] if "overwhelm" in text.lower() else []
    return {
        "intent": detect_intent(text),
        "symptoms": [{"key": k, "label": SYMPTOMS[k]["label"], "severity": severity} for k in symptoms],
        "moods": moods,
        "triggers": find_triggers(text),
        "sleep_hours": find_sleep(text),
        "summary": "",
    }
