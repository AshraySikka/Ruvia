"""Doctor visit summary as a PDF. Plain, factual, easy to scan in a short appointment."""
from collections import Counter
from datetime import timedelta
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config.utils import user_today

from .cycle import summary as cycle_summary
from .insights import _avg, patterns, series

SAGE = colors.HexColor("#56664A")
INK = colors.HexColor("#1F1C17")
MUTED = colors.HexColor("#6E655A")
LINE = colors.HexColor("#E0D6C5")
SOFT = colors.HexColor("#F3EDE3")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontName="Times-Roman", fontSize=24, textColor=SAGE, alignment=0, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=9.5, textColor=MUTED, spaceAfter=10),
        "h": ParagraphStyle("h", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, textColor=INK, spaceBefore=12, spaceAfter=6),
        "p": ParagraphStyle("p", parent=base["Normal"], fontSize=9.5, leading=13, textColor=INK),
        "small": ParagraphStyle("sm", parent=base["Normal"], fontSize=8, leading=10, textColor=MUTED),
    }


def _table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def build_report(user, days=90):
    s = _styles()
    today = user_today(user)
    since = today - timedelta(days=days - 1)
    P = lambda text, st="p": Paragraph(text, s[st])
    story = [
        P("Ruvia health summary", "title"),
        P(f"{user.display_name} &nbsp;|&nbsp; {since.strftime('%b %d, %Y')} to {today.strftime('%b %d, %Y')} &nbsp;|&nbsp; "
          f"Self-reported diary, not a medical record", "sub"),
    ]

    meds = list(user.medications.filter(active=True))
    allergies = list(user.allergies.all())
    story.append(P("Medicines and allergies", "h"))
    if meds:
        story.append(_table([["Medicine", "Type", "Dose as entered", "How often", "Since"]] + [
            [m.name, m.get_kind_display(), m.dose_text or "", m.frequency or "", m.start_date.strftime("%b %Y") if m.start_date else ""]
            for m in meds], [48 * mm, 30 * mm, 36 * mm, 36 * mm, 22 * mm]))
    else:
        story.append(P("No current medicines entered."))
    story.append(Spacer(1, 4))
    story.append(P("Allergies: " + (", ".join(f"{a.substance}" + (f" ({a.reaction})" if a.reaction else "") for a in allergies) or "None entered")))

    eps = list(user.episodes.filter(date__gte=since).order_by("-started_at"))
    story.append(P("Symptoms at a glance", "h"))
    if eps:
        counts = Counter(e.label for e in eps)
        rows = [["Symptom", "Times", "Most common severity", "Average length", "Usually helped"]]
        for label, n in counts.most_common(10):
            group = [e for e in eps if e.label == label]
            sev = Counter(e.severity for e in group).most_common(1)[0][0].title()
            dur = _avg(e.duration_minutes for e in group)
            dur_txt = (f"{dur / 60:.1f} h" if dur and dur >= 90 else f"{dur:.0f} min") if dur else ""
            helped = Counter(t for e in group if e.outcome == "better" for t in e.tried).most_common(2)
            rows.append([label, str(n), sev, dur_txt, ", ".join(h for h, _ in helped)])
        story.append(_table(rows, [36 * mm, 14 * mm, 34 * mm, 26 * mm, 62 * mm]))

        story.append(P("Recent episodes", "h"))
        rows = [["Date", "Symptom", "Severity", "Possible triggers", "Tried", "Result"]]
        for e in eps[:25]:
            rows.append([e.date.strftime("%b %d"), e.label, e.severity.title(), ", ".join(e.triggers),
                         ", ".join(e.tried)[:60], e.get_outcome_display()])
        story.append(_table(rows, [16 * mm, 26 * mm, 18 * mm, 34 * mm, 58 * mm, 20 * mm]))
    else:
        story.append(P("No symptoms logged in this period."))

    rows = series(user, min(days, 90))
    story.append(P("Daily wellbeing (self-rated)", "h"))
    phys, ment = _avg(r["physical"] for r in rows), _avg(r["mental"] for r in rows)
    sleep, water = _avg(r["sleep_hours"] for r in rows), _avg(r["water_ml"] or None for r in rows)
    story.append(P(f"Average physical {phys or 'n/a'}%, mental {ment or 'n/a'}%. "
                   f"Average sleep {sleep or 'n/a'} h. Average water {int(water) if water else 'n/a'} ml a day."))

    if user.track_cycle:
        c = cycle_summary(user)
        if c.get("has_data"):
            story.append(P("Cycle", "h"))
            story.append(P(f"Average cycle {c['cycle_length']} days, period about {c['period_length']} days, "
                           f"{c['logged_cycles']} cycles logged. Last period started {c['last_start']}. "
                           + (f"Cycle length varies by about {c['variability_days']} days." if c.get("variability_days") is not None else "")))

    pats = patterns(user)
    if pats.get("ready") and pats["items"]:
        story.append(P("Patterns seen in the diary", "h"))
        for it in pats["items"][:5]:
            story.append(P(f"&bull; {it['text']}"))
        story.append(P(pats["note"], "small"))

    story.append(P("Questions worth asking", "h"))
    qs = []
    if eps:
        top, n = Counter(e.label for e in eps).most_common(1)[0]
        qs.append(f"{top} came up {n} times in {days} days. Is that worth looking into?")
        worse = [e for e in eps if e.outcome == "worse"]
        if worse:
            qs.append(f"Some episodes got worse after home care ({', '.join(sorted(set(e.label for e in worse)))}). What should I do next time?")
        if any(e.severity in ("severe", "extreme") for e in eps):
            qs.append("I had some severe episodes. When should I seek care right away?")
    if meds:
        qs.append("Are my current medicines safe with the over the counter options I use?")
    if pats.get("items"):
        qs.append(f"Could \"{pats['items'][0]['condition'].lower()}\" be linked to my {pats['items'][0]['outcome'].lower()}?")
    qs.append("Is there anything in this summary you would like me to track more closely?")
    for q in qs:
        story.append(P(f"&bull; {q}"))

    story.append(Spacer(1, 14))
    story.append(P("Made with Ruvia. This summary is self-reported and is meant to support a conversation with a clinician, not replace one.", "small"))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Ruvia health summary", author="Ruvia")
    doc.build(story)
    return buf.getvalue()
