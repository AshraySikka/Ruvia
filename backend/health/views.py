from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from config.utils import user_now, user_today

from .models import (Allergy, CabinetItem, CycleEntry, CyclePrompt, DailyLog, DayTag, EmergencyCard, Goal, GoalCheck,
                     HealthDate, Medication, MedLog, MoodFeedback, SymptomEpisode, WaterLog, WeatherDay)
from .services import insights
from .services.cycle import period_days
from .services.cycle import summary as cycle_summary
from .services.library import MOODS, OTC
from .services.remedies import check_otc
from .services.scoring import SCORING_EXPLAINER


def parse_day(value, user):
    if value in (None, "", "today"):
        return user_today(user)
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def water_total(user, day):
    return WaterLog.objects.filter(user=user, date=day).aggregate(t=Sum("amount_ml"))["t"] or 0


def log_payload(log):
    if not log:
        return None
    return {"date": log.date.isoformat(), "physical_rating": log.physical_rating, "mental_rating": log.mental_rating,
            "sleep_hours": log.sleep_hours, "moods": log.moods, "rough_day": log.rough_day, "note": log.note,
            "scores": log.scores()}


def episode_payload(e):
    return {"id": e.id, "key": e.key, "label": e.label, "date": e.date.isoformat(), "severity": e.severity,
            "started_at": e.started_at.isoformat(), "ended_at": e.ended_at.isoformat() if e.ended_at else None,
            "duration_minutes": e.duration_minutes, "triggers": e.triggers, "tried": e.tried, "outcome": e.outcome,
            "resolved": e.resolved, "note": e.note}


def emergency_payload(user):
    card = EmergencyCard.objects.filter(user=user).first()
    return {
        "full_name": (card.full_name if card and card.full_name else user.display_name),
        "date_of_birth": card.date_of_birth.isoformat() if card and card.date_of_birth else None,
        "blood_type": card.blood_type if card else "",
        "conditions": card.conditions if card else "",
        "contacts": card.contacts if card else [],
        "doctor": card.doctor if card else "",
        "health_card_note": card.health_card_note if card else "",
        "notes": card.notes if card else "",
        "allergies": [{"substance": a.substance, "reaction": a.reaction} for a in user.allergies.all()],
        "medications": [{"name": m.name, "dose_text": m.dose_text, "frequency": m.frequency} for m in user.medications.filter(active=True)],
        "updated_at": card.updated_at.isoformat() if card else None,
    }


class TodayView(APIView):
    def get(self, request):
        u = request.user
        today = user_today(u)
        log = DailyLog.objects.filter(user=u, date=today).first()
        from assistant.models import FollowUp
        from notify.models import Notification
        pending = FollowUp.objects.filter(user=u, status="pending").select_related("episode").order_by("due_at").first()
        mood = None
        if log and log.moods:
            from assistant.engine import mood_card
            mood = mood_card(u, log.moods[0])
        elif log and log.scores()["mental"] is not None and log.scores()["mental"] <= 45:
            from assistant.engine import mood_card
            mood = mood_card(u, "exhausted")
        cycle = cycle_summary(u) if u.track_cycle else None
        wc = insights.what_changed(u)
        pats = insights.patterns(u)
        hour = user_now(u).hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        goals = []
        for g in u.goals.filter(active=True):
            done = GoalCheck.objects.filter(goal=g, user=u, date=today).aggregate(t=Sum("value"))["t"] or 0
            goals.append({"id": g.id, "title": g.title, "emoji": g.emoji, "target": g.target, "unit": g.unit, "done": done,
                          "members": g.members.count()})
        return Response({
            "date": today.isoformat(),
            "greeting": f"{greeting}, {u.display_name}",
            "log": log_payload(log),
            "scores": log.scores() if log else {"physical": None, "mental": None, "overall": None},
            "water": {"total": water_total(u, today), "goal": u.water_goal_ml,
                      "logs": [{"id": w.id, "amount_ml": w.amount_ml, "at": w.logged_at.isoformat()} for w in WaterLog.objects.filter(user=u, date=today)[:12]]},
            "tags": [{"id": t.id, "label": t.label, "kind": t.kind} for t in DayTag.objects.filter(user=u, date=today)],
            "open_episodes": [episode_payload(e) for e in SymptomEpisode.objects.filter(user=u, resolved=False, date__gte=today - timedelta(days=1))[:5]],
            "followup": {"id": pending.id, "label": pending.episode.label, "due_at": pending.due_at.isoformat(),
                         "due": pending.due_at <= timezone.now()} if pending else None,
            "mood": mood,
            "cycle": cycle,
            "streak": insights.streak(u),
            "insight": (pats["items"][0]["text"] if pats.get("items") else (wc["lines"][0]["text"] if wc["lines"] else None)),
            "upcoming": [{"id": d.id, "title": d.title, "kind": d.kind, "date": d.date.isoformat(), "time": d.time.strftime("%H:%M") if d.time else None}
                         for d in HealthDate.objects.filter(user=u, date__gte=today, date__lte=today + timedelta(days=14))[:3]],
            "goals": goals,
            "unread": Notification.objects.filter(user=u, read_at__isnull=True, cancelled=False, send_at__lte=timezone.now()).count(),
            "has_checked_in": DayTag.objects.filter(user=u, date=today).exists() or bool(log and (log.physical_rating is not None or log.mental_rating is not None)),
            "explainer": SCORING_EXPLAINER,
        })


class DayView(APIView):
    def get(self, request, day):
        u = request.user
        d = parse_day(day, u)
        if not d:
            return Response({"detail": "Bad date."}, status=400)
        from assistant.models import ChatMessage
        from config.utils import user_tz
        tz = user_tz(u)
        start = datetime.combine(d, datetime.min.time(), tzinfo=tz)
        msgs = ChatMessage.objects.filter(user=u, created_at__gte=start, created_at__lt=start + timedelta(days=1), role="user")
        w = WeatherDay.objects.filter(user=u, date=d).first()
        actual, predicted = period_days(u, d, d) if u.track_cycle else (set(), set())
        return Response({
            "date": d.isoformat(),
            "log": log_payload(DailyLog.objects.filter(user=u, date=d).first()),
            "tags": [{"id": t.id, "label": t.label, "kind": t.kind, "source": t.source} for t in DayTag.objects.filter(user=u, date=d)],
            "episodes": [episode_payload(e) for e in SymptomEpisode.objects.filter(user=u, date=d)],
            "checkins": [{"id": m.id, "text": m.text, "source": m.source, "at": m.created_at.isoformat(), "kind": m.kind} for m in msgs],
            "water": {"total": water_total(u, d), "goal": u.water_goal_ml},
            "dates": [{"title": h.title, "kind": h.kind, "time": h.time.strftime("%H:%M") if h.time else None} for h in HealthDate.objects.filter(user=u, date=d)],
            "weather": {"temp_max": w.temp_max, "temp_min": w.temp_min, "pressure_change": w.pressure_change, "humidity": w.humidity_mean} if w else None,
            "period": "actual" if d in actual else "predicted" if d in predicted else None,
        })

    def patch(self, request, day):
        u = request.user
        d = parse_day(day, u)
        if not d or d > user_today(u):
            return Response({"detail": "Pick today or a past day."}, status=400)
        log, _ = DailyLog.objects.get_or_create(user=u, date=d)
        for field in ("physical_rating", "mental_rating"):
            if field in request.data:
                v = request.data[field]
                if v is None or v == "":
                    setattr(log, field, None)
                else:
                    try:
                        v = int(v)
                    except (TypeError, ValueError):
                        return Response({"detail": f"{field} must be 0 to 10."}, status=400)
                    if not 0 <= v <= 10:
                        return Response({"detail": f"{field} must be 0 to 10."}, status=400)
                    setattr(log, field, v)
        if "sleep_hours" in request.data:
            v = request.data["sleep_hours"]
            log.sleep_hours = None if v in (None, "") else max(0, min(16, float(v)))
        if "note" in request.data:
            log.note = (request.data["note"] or "")[:2000]
        log.save()
        return Response(log_payload(log))


class CalendarView(APIView):
    def get(self, request):
        u = request.user
        month = request.query_params.get("month") or user_today(u).strftime("%Y-%m")
        try:
            y, m = map(int, month.split("-"))
            first = date(y, m, 1)
        except ValueError:
            return Response({"detail": "Use month=YYYY-MM."}, status=400)
        last = date(y, m, monthrange(y, m)[1])
        logs = {l.date: l for l in DailyLog.objects.filter(user=u, date__range=(first, last))}
        tags = defaultdict(list)
        for t in DayTag.objects.filter(user=u, date__range=(first, last)):
            tags[t.date].append({"label": t.label, "kind": t.kind})
        sym_days = defaultdict(list)
        for e in SymptomEpisode.objects.filter(user=u, date__range=(first, last)):
            sym_days[e.date].append(e.severity)
        dates = defaultdict(list)
        for h in HealthDate.objects.filter(user=u, date__range=(first, last)):
            dates[h.date].append(h.title)
        actual, predicted = period_days(u, first, last) if u.track_cycle else (set(), set())
        days = []
        d = first
        while d <= last:
            s = logs[d].scores() if d in logs else {"overall": None, "physical": None, "mental": None}
            days.append({
                "date": d.isoformat(), "overall": s["overall"], "physical": s["physical"], "mental": s["mental"],
                "tags": tags.get(d, []), "rough_day": bool(d in logs and logs[d].rough_day),
                "period": "actual" if d in actual else "predicted" if d in predicted else None,
                "dates": dates.get(d, []), "symptoms": len(sym_days.get(d, [])),
            })
            d += timedelta(days=1)
        logged = [x for x in days if x["overall"] is not None]
        return Response({"month": month, "days": days,
                         "summary": {"logged": len(logged),
                                     "average": round(sum(x["overall"] for x in logged) / len(logged)) if logged else None,
                                     "best": max(logged, key=lambda x: x["overall"])["date"] if logged else None}})


class WaterView(APIView):
    def post(self, request):
        u = request.user
        try:
            amount = int(request.data.get("amount_ml", 250))
        except (TypeError, ValueError):
            return Response({"detail": "Amount must be a number."}, status=400)
        if not 50 <= amount <= 2000:
            return Response({"detail": "Pick between 50 and 2000 ml."}, status=400)
        d = parse_day(request.data.get("date"), u) or user_today(u)
        WaterLog.objects.create(user=u, date=d, amount_ml=amount)
        DailyLog.objects.get_or_create(user=u, date=d)
        return Response({"total": water_total(u, d), "goal": u.water_goal_ml}, status=201)

    def delete(self, request, pk=None):
        u = request.user
        w = WaterLog.objects.filter(user=u, pk=pk).first() if pk else WaterLog.objects.filter(user=u, date=user_today(u)).first()
        d = w.date if w else user_today(u)
        if w:
            w.delete()
        return Response({"total": water_total(u, d), "goal": u.water_goal_ml})


class TagView(APIView):
    def post(self, request, day):
        u = request.user
        d = parse_day(day, u)
        label = (request.data.get("label") or "").strip()[:40]
        if not d or not label:
            return Response({"detail": "Add a label."}, status=400)
        label = label[0].upper() + label[1:]
        t, _ = DayTag.objects.get_or_create(user=u, date=d, label=label, defaults={"kind": request.data.get("kind", "note"), "source": "manual"})
        DailyLog.objects.get_or_create(user=u, date=d)
        return Response({"id": t.id, "label": t.label, "kind": t.kind, "source": t.source}, status=201)

    def patch(self, request, day, pk):
        t = DayTag.objects.filter(user=request.user, pk=pk).first()
        label = (request.data.get("label") or "").strip()[:40]
        if not t or not label:
            return Response({"detail": "Not found."}, status=404)
        t.label, t.source = label, "manual"
        t.save()
        return Response({"id": t.id, "label": t.label, "kind": t.kind, "source": t.source})

    def delete(self, request, day, pk):
        DayTag.objects.filter(user=request.user, pk=pk).delete()
        return Response(status=204)


class EpisodeView(APIView):
    def get(self, request, pk=None):
        u = request.user
        qs = SymptomEpisode.objects.filter(user=u)
        if request.query_params.get("key"):
            qs = qs.filter(key=request.query_params["key"])
        return Response([episode_payload(e) for e in qs[:100]])

    def patch(self, request, pk=None):
        e = SymptomEpisode.objects.filter(user=request.user, pk=pk).first()
        if not e:
            return Response({"detail": "Not found."}, status=404)
        if request.data.get("severity") in ("mild", "moderate", "severe", "extreme"):
            e.severity = request.data["severity"]
        if request.data.get("outcome") in ("unknown", "better", "same", "worse"):
            e.outcome = request.data["outcome"]
        if isinstance(request.data.get("tried"), list):
            e.tried = [str(x)[:80] for x in request.data["tried"]][:10]
        if isinstance(request.data.get("triggers"), list):
            e.triggers = [str(x)[:40] for x in request.data["triggers"]][:6]
        if "duration_minutes" in request.data:
            v = request.data["duration_minutes"]
            e.duration_minutes = int(v) if v not in (None, "") else None
        if "resolved" in request.data:
            e.resolved = bool(request.data["resolved"])
            if e.resolved and not e.ended_at:
                e.ended_at = timezone.now()
                e.duration_minutes = e.duration_minutes or max(1, int((e.ended_at - e.started_at).total_seconds() // 60))
        if "note" in request.data:
            e.note = (request.data["note"] or "")[:1000]
        e.save()
        from .services.scoring import refresh_estimates
        log = DailyLog.objects.filter(user=e.user, date=e.date).first()
        if log:
            refresh_estimates(log)
        return Response(episode_payload(e))

    def delete(self, request, pk=None):
        SymptomEpisode.objects.filter(user=request.user, pk=pk).delete()
        return Response(status=204)


class RoughDayView(APIView):
    def post(self, request):
        from assistant.engine import rough_day_message
        from care.services import notify_rough_day
        u = request.user
        log, _ = DailyLog.objects.get_or_create(user=u, date=user_today(u))
        log.rough_day = True
        if log.mental_rating is None and log.mental_estimate is None:
            log.mental_estimate = 35
        log.save()
        DayTag.objects.get_or_create(user=u, date=log.date, label="Rough day", defaults={"kind": "mood", "source": "manual"})
        told = notify_rough_day(u)
        return Response({"message": rough_day_message(u), "told": told, "scores": log.scores()})

    def delete(self, request):
        u = request.user
        DailyLog.objects.filter(user=u, date=user_today(u)).update(rough_day=False)
        DayTag.objects.filter(user=u, date=user_today(u), label="Rough day").delete()
        return Response(status=204)


class MoodFeedbackView(APIView):
    def post(self, request):
        key = request.data.get("mood_key")
        if key not in MOODS:
            return Response({"detail": "Unknown mood."}, status=400)
        MoodFeedback.objects.create(user=request.user, mood_key=key, activity=str(request.data.get("activity", ""))[:120],
                                    helped=bool(request.data.get("helped", True)))
        return Response({"ok": True}, status=201)


class MoodListView(APIView):
    def get(self, request):
        from assistant.engine import mood_card
        return Response([mood_card(request.user, k) for k in MOODS])


class InsightsView(APIView):
    def get(self, request):
        u = request.user
        rng = request.query_params.get("range", "week")
        days = 30 if rng == "month" else 7
        try:
            from .services.weather import maybe_sync
            maybe_sync(u)
        except Exception:
            pass
        rows = insights.series(u, days)
        weather = [{"date": w.date.isoformat(), "pressure": w.pressure_mean, "change": w.pressure_change, "temp_max": w.temp_max}
                   for w in WeatherDay.objects.filter(user=u, date__gte=user_today(u) - timedelta(days=days - 1)).order_by("date")]
        from collections import Counter
        return Response({
            "range": rng, "series": rows, "what_changed": insights.what_changed(u), "baseline": insights.baseline(u),
            "patterns": insights.patterns(u), "streak": insights.streak(u), "weather": weather,
            "top_symptoms": Counter(s for r in rows for s in r["symptoms"]).most_common(5),
            "has_location": u.latitude is not None,
        })


class CycleView(APIView):
    def get(self, request):
        u = request.user
        today = user_today(u)
        prompt = CyclePrompt.objects.filter(user=u, asked_on=today).first()
        s = cycle_summary(u)
        return Response({
            "summary": s,
            "entries": [{"id": e.id, "start_date": e.start_date.isoformat(), "end_date": e.end_date.isoformat() if e.end_date else None,
                         "flow": e.flow, "pain": e.pain, "on_time": e.on_time, "notes": e.notes} for e in u.cycles.all()[:12]],
            "ask_today": bool(s.get("has_data") and s["days_until"] <= 0 and not s["on_period"] and not prompt),
        })

    def post(self, request):
        u = request.user
        try:
            start = date.fromisoformat(request.data.get("start_date"))
        except (TypeError, ValueError):
            return Response({"detail": "Add a start date."}, status=400)
        end = request.data.get("end_date")
        end = date.fromisoformat(end) if end else None
        if end and end < start:
            return Response({"detail": "End date is before start."}, status=400)
        s = cycle_summary(u)
        on_time = None
        if s.get("has_data"):
            on_time = abs((start - date.fromisoformat(s["next_start"])).days) <= 2
        e = CycleEntry.objects.create(user=u, start_date=start, end_date=end, flow=request.data.get("flow", "medium"),
                                      pain=request.data.get("pain"), on_time=on_time, notes=(request.data.get("notes") or "")[:300])
        if not u.track_cycle:
            u.track_cycle = True
            u.save(update_fields=["track_cycle"])
        DayTag.objects.get_or_create(user=u, date=start, label="Period started", defaults={"kind": "note", "source": "auto"})
        return Response({"id": e.id, "on_time": on_time, "summary": cycle_summary(u)}, status=201)


class CycleEntryView(APIView):
    def patch(self, request, pk):
        e = CycleEntry.objects.filter(user=request.user, pk=pk).first()
        if not e:
            return Response({"detail": "Not found."}, status=404)
        for f in ("start_date", "end_date"):
            if f in request.data:
                setattr(e, f, date.fromisoformat(request.data[f]) if request.data[f] else None)
        for f in ("flow", "pain", "notes"):
            if f in request.data:
                setattr(e, f, request.data[f])
        e.save()
        return Response({"ok": True, "summary": cycle_summary(request.user)})

    def delete(self, request, pk):
        CycleEntry.objects.filter(user=request.user, pk=pk).delete()
        return Response(status=204)


class CycleConfirmView(APIView):
    """Answers 'did your period start today?'."""

    def post(self, request):
        u = request.user
        today = user_today(u)
        answer = request.data.get("answer")
        s = cycle_summary(u)
        if answer == "yes":
            d = date.fromisoformat(request.data["date"]) if request.data.get("date") else today
            on_time = abs((d - date.fromisoformat(s["next_start"])).days) <= 2 if s.get("has_data") else None
            CycleEntry.objects.create(user=u, start_date=d, on_time=on_time)
            DayTag.objects.get_or_create(user=u, date=d, label="Period started", defaults={"kind": "note", "source": "auto"})
            CyclePrompt.objects.update_or_create(user=u, asked_on=today, defaults={"predicted_date": date.fromisoformat(s["next_start"]) if s.get("has_data") else today, "answer": "yes"})
            msg = "Logged. Right on time." if on_time else "Logged. Thanks, this keeps the predictions honest."
        elif answer == "ended":
            e = u.cycles.first()
            if e and not e.end_date:
                e.end_date = today
                e.save(update_fields=["end_date"])
            msg = "Noted that your period ended."
        else:
            if s.get("has_data"):
                CyclePrompt.objects.update_or_create(user=u, asked_on=today, defaults={"predicted_date": date.fromisoformat(s["next_start"]), "answer": "not_yet"})
            msg = "Okay. I will ask again tomorrow."
        return Response({"message": msg, "summary": cycle_summary(u)})


class ReportView(APIView):
    def get(self, request):
        from .services.report import build_report
        try:
            days = max(7, min(365, int(request.query_params.get("days", 90))))
        except ValueError:
            days = 90
        pdf = build_report(request.user, days)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="ruvia-summary-{user_today(request.user)}.pdf"'
        return resp


class ExportView(APIView):
    def get(self, request):
        u = request.user
        from assistant.models import ChatMessage
        data = {
            "exported_at": timezone.now().isoformat(),
            "profile": {"email": u.email, "name": u.first_name, "sex": u.sex, "birth_year": u.birth_year, "water_goal_ml": u.water_goal_ml},
            "days": [log_payload(l) for l in u.days.all()],
            "water": list(u.water_logs.values("date", "amount_ml", "logged_at")),
            "tags": list(u.tags.values("date", "label", "kind")),
            "symptoms": [episode_payload(e) for e in u.episodes.all()],
            "medications": list(u.medications.values("name", "kind", "dose_text", "frequency", "start_date", "active")),
            "allergies": list(u.allergies.values("substance", "reaction")),
            "cabinet": list(u.cabinet.values("name", "note", "expires_on")),
            "cycles": list(u.cycles.values("start_date", "end_date", "flow", "pain", "notes")),
            "health_dates": list(u.health_dates.values("title", "kind", "date", "time", "notes")),
            "emergency_card": emergency_payload(u),
            "messages": [{"role": m.role, "text": m.text, "at": m.created_at.isoformat()} for m in ChatMessage.objects.filter(user=u)],
        }
        resp = Response(data)
        resp["Content-Disposition"] = 'attachment; filename="ruvia-export.json"'
        return resp


class EmergencyView(APIView):
    def get(self, request):
        return Response(emergency_payload(request.user))

    def put(self, request):
        card, _ = EmergencyCard.objects.get_or_create(user=request.user)
        for f in ("full_name", "blood_type", "conditions", "doctor", "health_card_note", "notes"):
            if f in request.data:
                setattr(card, f, (request.data[f] or "")[:2000])
        if "date_of_birth" in request.data:
            card.date_of_birth = date.fromisoformat(request.data["date_of_birth"]) if request.data["date_of_birth"] else None
        if isinstance(request.data.get("contacts"), list):
            card.contacts = [{"name": str(c.get("name", ""))[:80], "phone": str(c.get("phone", ""))[:40], "relation": str(c.get("relation", ""))[:40]}
                             for c in request.data["contacts"][:4] if isinstance(c, dict)]
        card.save()
        return Response(emergency_payload(request.user))


class InteractionCheckView(APIView):
    """Lets the profile screen show which OTC options are fine with the current medicines."""

    def get(self, request):
        meds = list(request.user.medications.filter(active=True).values_list("name", flat=True))
        allergies = list(request.user.allergies.values_list("substance", flat=True))
        out = []
        for key, info in OTC.items():
            ok, level, reasons = check_otc(key, meds, allergies)
            if level != "ok":
                out.append({"key": key, "name": info["name"], "brands": info["brands"], "level": level, "reasons": reasons})
        return Response({"flags": out, "meds": meds, "allergies": allergies})


class GeoView(APIView):
    def get(self, request):
        from .services.weather import geocode
        q = (request.query_params.get("q") or "").strip()
        return Response(geocode(q) if len(q) >= 2 else [])


class ExplainerView(APIView):
    def get(self, request):
        return Response({"scoring": SCORING_EXPLAINER})


# Simple CRUD for profile lists, always scoped to the signed in person.
def scoped_viewset(model, fields_list):
    class S(serializers.ModelSerializer):
        class Meta:
            pass
    S.Meta.model = model
    S.Meta.fields = ["id"] + fields_list

    class V(viewsets.ModelViewSet):
        serializer_class = S

        def get_queryset(self):
            return model.objects.filter(user=self.request.user)

        def perform_create(self, serializer):
            serializer.save(user=self.request.user)

    V.__name__ = f"{model.__name__}ViewSet"
    return V


MedicationViewSet = scoped_viewset(Medication, ["name", "kind", "dose_text", "frequency", "start_date", "active", "notes"])
AllergyViewSet = scoped_viewset(Allergy, ["substance", "reaction"])
CabinetViewSet = scoped_viewset(CabinetItem, ["name", "note", "expires_on", "running_low"])
HealthDateViewSet = scoped_viewset(HealthDate, ["title", "kind", "date", "time", "location", "notes", "shared"])


class MedTakenView(APIView):
    def post(self, request, pk):
        m = Medication.objects.filter(user=request.user, pk=pk).first()
        if not m:
            return Response({"detail": "Not found."}, status=404)
        MedLog.objects.create(user=request.user, medication=m, name=m.name)
        return Response({"ok": True, "taken_at": timezone.now().isoformat()}, status=201)

    def get(self, request, pk):
        logs = MedLog.objects.filter(user=request.user, medication_id=pk)[:20]
        return Response([{"at": l.taken_at.isoformat()} for l in logs])


class GoalsView(APIView):
    def get(self, request):
        u = request.user
        today = user_today(u)
        out = []
        for g in u.goals.filter(active=True).prefetch_related("members"):
            week = []
            for i in range(6, -1, -1):
                d = today - timedelta(days=i)
                week.append({"date": d.isoformat(), "members": {("You" if m == u else m.display_name): (GoalCheck.objects.filter(goal=g, user=m, date=d).aggregate(t=Sum("value"))["t"] or 0) for m in g.members.all()}})
            out.append({"id": g.id, "title": g.title, "emoji": g.emoji, "unit": g.unit, "target": g.target,
                        "members": [{"id": m.id, "name": "You" if m == u else m.display_name, "hue": m.avatar_hue} for m in g.members.all()],
                        "today": {("You" if m == u else m.display_name): GoalCheck.objects.filter(goal=g, user=m, date=today).aggregate(t=Sum("value"))["t"] or 0 for m in g.members.all()},
                        "week": week, "mine": g.created_by_id == u.id})
        return Response(out)

    def post(self, request):
        from care.models import CircleMember
        u = request.user
        title = (request.data.get("title") or "").strip()[:80]
        if not title:
            return Response({"detail": "Give the goal a name."}, status=400)
        g = Goal.objects.create(title=title, emoji=(request.data.get("emoji") or "")[:8], unit=(request.data.get("unit") or "times")[:20],
                                target=max(1, int(request.data.get("target") or 1)), created_by=u)
        g.members.add(u)
        for mid in request.data.get("members", []):
            if CircleMember.objects.filter(owner=u, member_id=mid).exists():
                g.members.add(mid)
                from notify.services import queue
                from django.contrib.auth import get_user_model
                other = get_user_model().objects.get(pk=mid)
                queue(other, "goal", f"{u.display_name} started a shared goal", title, "/care?tab=goals", timezone.now(), dedupe=f"goal:{g.id}:{mid}")
        return Response({"id": g.id}, status=201)


class GoalCheckView(APIView):
    def post(self, request, pk):
        u = request.user
        g = u.goals.filter(pk=pk).first()
        if not g:
            return Response({"detail": "Not found."}, status=404)
        d = parse_day(request.data.get("date"), u) or user_today(u)
        value = int(request.data.get("value", 1))
        gc, _ = GoalCheck.objects.get_or_create(goal=g, user=u, date=d, defaults={"value": 0})
        gc.value = max(0, value if request.data.get("set") else gc.value + value)
        gc.save()
        return Response({"value": gc.value})

    def delete(self, request, pk):
        g = Goal.objects.filter(pk=pk, created_by=request.user).first()
        if g:
            g.active = False
            g.save(update_fields=["active"])
        else:
            request.user.goals.remove(pk)
        return Response(status=204)
