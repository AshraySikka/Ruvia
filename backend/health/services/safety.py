"""
Hard coded safety rules. These run before any language model is called.
If a rule fires, the reply is fixed text from here and no model is used.
"""
import re

CRISIS_PATTERNS = [
    r"\bkill (my ?self|me)\b", r"\bkms\b", r"\bsuicid", r"\bend (my|it all|my life)\b", r"\bend it\b",
    r"\bwant to die\b", r"\bwanna die\b", r"\bwish i (was|were) dead\b", r"\bbetter off dead\b",
    r"\bno reason to live\b", r"\bdon'?t want to (live|be here|exist)\b", r"\bnot want to (live|be here)\b",
    r"\bhurt(ing)? my ?self\b", r"\bself[- ]?harm\b", r"\bcut(ting)? my ?self\b", r"\boverdose\b",
    r"\btake all my (pills|meds)\b", r"\bcan'?t go on\b", r"\bgive up on (life|everything)\b",
]

# (pattern, short reason). Matching any of these means urgent care, not home remedies.
RED_FLAGS = [
    (r"worst headache (of my life|ever)|thunderclap|sudden (and )?(severe|extreme) headache", "a sudden, very severe headache"),
    (r"headache.*(stiff neck|confus|vision|can'?t see|blurr|faint|passed out|numb|weak)|(stiff neck|confus|vision loss|blurr).*headache", "a headache with nerve or vision symptoms"),
    (r"chest (pain|pressure|tightness|is tight)|pain in my chest|crushing", "chest pain or pressure"),
    (r"can'?t breathe|cannot breathe|trouble breathing|hard to breathe|short(ness)? of breath|gasping", "trouble breathing"),
    (r"face (droop|drooping)|slurred|slurring|can'?t (move|feel) (my )?(arm|leg|face)|one side of my (face|body)", "possible stroke signs"),
    (r"passed out|fainted|blacked out|unconscious|seizure|convuls", "fainting or a seizure"),
    (r"(vomit|throw(ing)? up|cough(ing)? up) blood|blood in (my )?(vomit|stool|poop)|black (tarry )?stool", "bleeding from the gut or lungs"),
    (r"(lips|tongue|throat|face) (is |are )?(swelling|swollen)|throat (is )?closing|anaphyla", "a possible severe allergic reaction"),
    (r"(severe|extreme|unbearable|worst) (stomach|abdominal|belly) pain|pain in (my )?lower right", "severe belly pain"),
    (r"fever (of |is )?(4[0-9]|10[4-9])|(4[0-9]|10[4-9]) ?(c|f|degree)", "a very high fever"),
    (r"hit my head|head injury|concussion", "a head injury"),
    (r"pregnan.*(bleed|cramp|pain)|(bleed|cramp|pain).*pregnan", "pain or bleeding in pregnancy"),
    (r"took too many|swallowed (a lot|too much|bleach)|poison", "possible poisoning"),
]

CRISIS_REPLY = (
    "I'm really glad you told me. You don't have to carry this alone.\n\n"
    "Please reach out right now:\n"
    "Call or text 9-8-8, the Suicide Crisis Helpline. It's free and open all day and night.\n"
    "If you are in immediate danger, call 911.\n\n"
    "If you can, tell someone near you how you're feeling. I'll be here when you want to talk."
)

RED_FLAG_REPLY = (
    "What you described can be a sign of something that needs care today, not home remedies.\n\n"
    "Call 911 or go to the nearest emergency department now if it is severe or getting worse.\n"
    "If you are not sure, call Health811 (dial 811 in Ontario) to talk to a nurse any time.\n\n"
    "I saved this in your diary so you can show it to whoever sees you."
)


def _norm(text):
    return re.sub(r"\s+", " ", (text or "").lower()).replace("’", "'")


def check_crisis(text):
    t = _norm(text)
    return any(re.search(p, t) for p in CRISIS_PATTERNS)


def check_red_flags(text):
    t = _norm(text)
    reasons = [reason for pattern, reason in RED_FLAGS if re.search(pattern, t)]
    return reasons


def screen(text):
    """Returns ('crisis'|'red_flag'|None, reasons)."""
    if check_crisis(text):
        return "crisis", []
    reasons = check_red_flags(text)
    if reasons:
        return "red_flag", reasons
    return None, []


DOSE_PATTERN = re.compile(
    r"\b\d+(\.\d+)?\s?(mg|mcg|µg|milligrams?|ml|tablets?|tabs?|pills?|caplets?|capsules?)\b(\s?(every|each|per|a|twice|three times)\b[^.\n]*)?",
    re.IGNORECASE,
)


def _drug_words():
    from .library import OTC
    words = set()
    for info in OTC.values():
        words.add(info["name"].lower().split()[0])
        words.update(b.lower() for b in info["brands"])
    return words


def strip_doses(text):
    """Model replies must never include doses. Lines that mention a medicine have doses replaced."""
    if not text:
        return text
    drugs = _drug_words()
    out = []
    for line in re.split(r"(?<=[.!?\n])", text):
        low = line.lower()
        if any(d in low for d in drugs) or re.search(r"\b(take|dose|tablet|pill)\b", low):
            line = DOSE_PATTERN.sub("the dose on the label", line)
        out.append(line)
    return "".join(out)
