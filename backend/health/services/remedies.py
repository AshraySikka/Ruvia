"""Builds remedy suggestions: past wins first, then home remedies, then OTC options that pass the checks."""
from collections import Counter

from .library import ALLERGY_FAMILIES, DOCTOR_LINE, INTERACTIONS, MED_GROUPS, OTC, REMEDIES, SYMPTOMS


def _med_groups_for(med_names):
    groups = set()
    for name in med_names:
        low = name.lower()
        for group, words in MED_GROUPS.items():
            if any(w in low for w in words):
                groups.add(group)
    return groups


def check_otc(otc_key, med_names, allergy_names):
    """Returns (allowed, level, reasons). Pure code, no model involved."""
    info = OTC[otc_key]
    reasons, level = [], "ok"
    allergy_low = [a.lower() for a in allergy_names]
    for allergy in allergy_low:
        hit = otc_key in ALLERGY_FAMILIES.get(allergy.strip(), [])
        hit = hit or info["name"].lower().split()[0] in allergy
        hit = hit or any(b.lower() in allergy for b in info["brands"])
        for word, family in ALLERGY_FAMILIES.items():
            if word in allergy and otc_key in family:
                hit = True
        if hit:
            return False, "avoid", [f"you listed an allergy to {allergy}"]
    groups = _med_groups_for(med_names)
    for group, rule_level, reason in INTERACTIONS.get(otc_key, []):
        if group in groups:
            reasons.append(reason)
            if rule_level == "avoid":
                level = "avoid"
            elif level != "avoid":
                level = "caution"
    return level != "avoid", level, reasons


def _in_cabinet(otc_key, cabinet_names):
    info = OTC[otc_key]
    keys = [info["name"].lower().split()[0]] + [b.lower() for b in info["brands"]]
    return any(any(k in c.lower() for k in keys) for c in cabinet_names)


def history_for(user, key, limit=20):
    """What the person tried before for this symptom, and whether it helped."""
    from health.models import SymptomEpisode
    past = list(SymptomEpisode.objects.filter(user=user, key=key).exclude(outcome="unknown").order_by("-started_at")[:limit])
    helped = Counter()
    for ep in past:
        if ep.outcome == "better":
            for item in ep.tried:
                helped[item] += 1
    last_better = next((ep for ep in past if ep.outcome == "better" and ep.tried), None)
    return {
        "count": len(past),
        "helped": [{"item": item, "times": n} for item, n in helped.most_common(4)],
        "last_win": {
            "date": last_better.date.isoformat(),
            "tried": last_better.tried,
            "severity": last_better.severity,
        } if last_better else None,
    }


def suggestions_for(user, key, severity="moderate"):
    if key not in REMEDIES:
        return None
    lib = REMEDIES[key]
    meds = list(user.medications.filter(active=True).values_list("name", flat=True))
    allergies = list(user.allergies.values_list("substance", flat=True))
    cabinet = list(user.cabinet.values_list("name", flat=True))

    otc, skipped = [], []
    for otc_key in lib["otc"]:
        ok, level, reasons = check_otc(otc_key, meds, allergies)
        info = OTC[otc_key]
        entry = {
            "key": otc_key,
            "name": info["name"],
            "brands": info["brands"],
            "level": level,
            "reasons": reasons,
            "at_home": _in_cabinet(otc_key, cabinet),
        }
        (otc if ok else skipped).append(entry)
    otc.sort(key=lambda e: (not e["at_home"], e["level"] != "ok"))

    return {
        "key": key,
        "label": SYMPTOMS.get(key, {}).get("label", key.title()),
        "severity": severity,
        "history": history_for(user, key),
        "home": lib["home"],
        "otc": otc,
        "skipped": skipped,
        "doctor_if": lib["doctor_if"],
        "doctor_line": DOCTOR_LINE,
        "has_meds_on_file": bool(meds),
    }


def tried_options(suggestion):
    """Short labels the person can tap later to say what they tried."""
    if not suggestion:
        return []
    items = list(suggestion["home"][:4])
    for o in suggestion["otc"]:
        items.append(o["brands"][0] if o["brands"] else o["name"])
    return items
