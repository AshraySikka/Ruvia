"""
How scores work, in plain words (this text is also shown in the app):

Physical and mental scores are self-rated. You pick 0 to 10 and we show it as a percentage.
If you skip the rating, we estimate it from what you logged that day and label it as an estimate:
  start at 85, then take off 8 for a mild symptom, 18 moderate, 30 severe, 40 extreme.
  Mental estimate takes off 10 to 20 for heavy moods (stressed, anxious, low) and adds 5 for good ones.
Overall is the plain average of physical and mental.
These are wellbeing check-ins, not medical measurements.
"""

PENALTY = {"mild": 8, "moderate": 18, "severe": 30, "extreme": 40}
MENTAL_SYMPTOMS = {"stress", "low_mood", "insomnia"}
MOOD_PENALTY = {
    "anxious": 15, "overwhelmed": 18, "sad": 15, "lonely": 12, "exhausted": 12, "everyone_hates_me": 18,
    "hate_everyone": 12, "hate_myself": 22, "cant_focus": 8, "cant_sleep": 10, "restless": 6,
}

SCORING_EXPLAINER = [
    "Physical and mental scores are self-rated. You pick 0 to 10 and we show it as a percentage.",
    "If you have not rated the day yet, we estimate from what you logged and mark it as estimated.",
    "Estimates start at 85 and drop for each symptom: 8 for mild, 18 moderate, 30 severe, 40 extreme.",
    "Heavy moods lower the mental estimate. Good moods nudge it up a little.",
    "Overall is the average of physical and mental.",
    "These are wellbeing check-ins, not medical measurements.",
]


def estimate_scores(episodes, moods):
    physical, mental = 85, 85
    for ep in episodes:
        p = PENALTY.get(ep.severity if hasattr(ep, "severity") else ep.get("severity", "moderate"), 18)
        key = ep.key if hasattr(ep, "key") else ep.get("key")
        if key in MENTAL_SYMPTOMS:
            mental -= p
        else:
            physical -= p
    for m in moods or []:
        if m == "good":
            mental += 5
        mental -= MOOD_PENALTY.get(m, 0)
    clamp = lambda v: max(5, min(100, v))
    return clamp(physical), clamp(mental)


def day_scores(log):
    if log is None:
        return {"physical": None, "mental": None, "overall": None, "physical_source": None, "mental_source": None}
    def pick(rating, estimate):
        if rating is not None:
            return rating * 10, "self"
        if estimate is not None:
            return estimate, "estimate"
        return None, None
    physical, ps = pick(log.physical_rating, log.physical_estimate)
    mental, ms = pick(log.mental_rating, log.mental_estimate)
    values = [v for v in (physical, mental) if v is not None]
    overall = round(sum(values) / len(values)) if values else None
    return {"physical": physical, "mental": mental, "overall": overall, "physical_source": ps, "mental_source": ms}


def refresh_estimates(log):
    """Recompute estimates for a day from its episodes and moods."""
    episodes = list(log.user.episodes.filter(date=log.date))
    p, m = estimate_scores(episodes, log.moods)
    if not episodes and not log.moods:
        return
    log.physical_estimate, log.mental_estimate = p, m
    log.save(update_fields=["physical_estimate", "mental_estimate", "updated_at"])
