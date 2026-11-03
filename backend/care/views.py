from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.emails import send_invite
from config.utils import user_today
from health.models import DailyLog, DayTag, HealthDate, SymptomEpisode, WaterLog
from health.services.cycle import summary as cycle_summary

from .models import SHARE_FIELDS, CircleMember, Invite, Nudge, ShareGrant
from .services import connect, disconnect, grant

User = get_user_model()

NUDGES = {
    "thinking": "is thinking of you",
    "water": "says drink some water",
    "hug": "sent you a hug",
    "checkin": "wants to know how you are",
}


def person_card(viewer, person):
    g = grant(person, viewer)
    mine = grant(viewer, person)
    flags = g.flags() if g else {f: False for f in SHARE_FIELDS}
    today = user_today(person)
    card = {
        "id": person.id, "name": person.display_name, "hue": person.avatar_hue,
        "relation": CircleMember.objects.filter(owner=viewer, member=person).values_list("relation", flat=True).first() or "",
        "they_share": flags, "i_share": mine.flags() if mine else {f: False for f in SHARE_FIELDS},
    }
    log = DailyLog.objects.filter(user=person, date=today).first()
    if flags["scores"]:
        card["today"] = log.scores() if log else None
        week = DailyLog.objects.filter(user=person, date__gte=today - timedelta(days=6))
        card["week"] = [{"date": l.date.isoformat(), "overall": l.scores()["overall"]} for l in week.order_by("date")]
    if flags["tags"]:
        card["tags"] = list(DayTag.objects.filter(user=person, date=today).exclude(kind="mood").values_list("label", flat=True))
    if flags["water"]:
        card["water"] = {"ml": WaterLog.objects.filter(user=person, date=today).aggregate(t=Sum("amount_ml"))["t"] or 0,
                         "goal": person.water_goal_ml}
    if flags["rough_day"] and log and log.rough_day:
        card["rough_day"] = True
    if flags["cycle"] and person.track_cycle:
        c = cycle_summary(person)
        if c.get("has_data"):
            card["cycle"] = {"next_start": c["next_start"], "days_until": c["days_until"], "on_period": c["on_period"],
                             "phase_title": c["phase_title"]}
    return card


class CareView(APIView):
    def get(self, request):
        me = request.user
        people = [person_card(me, m.member) for m in CircleMember.objects.filter(owner=me).select_related("member")]
        received = [{"id": i.id, "from": i.inviter.display_name, "email": i.inviter.email, "relation": i.relation}
                    for i in Invite.objects.filter(invitee=me, status="pending").select_related("inviter")]
        sent = [{"id": i.id, "email": i.email, "status": i.status}
                for i in Invite.objects.filter(inviter=me, status="pending")]
        nudges = [{"id": n.id, "from": n.sender.display_name, "kind": n.kind, "text": NUDGES.get(n.kind, ""),
                   "message": n.message, "at": n.created_at.isoformat(), "read": n.read}
                  for n in Nudge.objects.filter(recipient=me).select_related("sender")[:10]]
        return Response({"people": people, "invites_received": received, "invites_sent": sent, "nudges": nudges,
                         "share_fields": SHARE_FIELDS})


class InviteView(APIView):
    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        relation = (request.data.get("relation") or "")[:40]
        if not email or "@" not in email:
            return Response({"detail": "Enter a valid email."}, status=400)
        if email == request.user.email:
            return Response({"detail": "That is your own email."}, status=400)
        invitee = User.objects.filter(email=email).first()
        if invitee and CircleMember.objects.filter(owner=request.user, member=invitee).exists():
            return Response({"detail": "Already in your circle."}, status=400)
        inv, _ = Invite.objects.get_or_create(inviter=request.user, email=email, status="pending",
                                              defaults={"invitee": invitee, "relation": relation})
        if invitee:
            from notify.services import queue
            queue(invitee, "care", f"{request.user.display_name} invited you to their care circle",
                  "You choose what you share.", "/care", timezone.now(), dedupe=f"invite:{inv.id}")
        else:
            send_invite(email, request.user.display_name)
        return Response({"ok": True, "existing_user": bool(invitee)}, status=201)


class InviteActionView(APIView):
    def post(self, request, pk, action):
        inv = Invite.objects.filter(pk=pk, invitee=request.user, status="pending").first()
        if not inv:
            return Response({"detail": "Invite not found."}, status=404)
        if action == "accept":
            connect(inv.inviter, request.user, relation_a=inv.relation, relation_b=request.data.get("relation", ""))
            inv.status = "accepted"
        else:
            inv.status = "declined"
        inv.save(update_fields=["status"])
        return Response({"ok": True})

    def delete(self, request, pk, action=None):
        Invite.objects.filter(pk=pk, inviter=request.user).delete()
        return Response(status=204)


class ShareView(APIView):
    def patch(self, request, viewer_id):
        if not CircleMember.objects.filter(owner=request.user, member_id=viewer_id).exists():
            return Response({"detail": "Not in your circle."}, status=404)
        g, _ = ShareGrant.objects.get_or_create(owner=request.user, viewer_id=viewer_id)
        for f in SHARE_FIELDS:
            if f in request.data:
                setattr(g, f, bool(request.data[f]))
        if not g.cycle:
            g.cycle_alerts = False
        g.save()
        return Response(g.flags())


class PersonView(APIView):
    def get(self, request, pk):
        if not CircleMember.objects.filter(owner=request.user, member_id=pk).exists():
            return Response({"detail": "Not in your circle."}, status=404)
        person = User.objects.get(pk=pk)
        card = person_card(request.user, person)
        flags = card["they_share"]
        today = user_today(person)
        if flags["symptoms"]:
            card["recent_symptoms"] = [{"label": e.label, "severity": e.severity, "date": e.date.isoformat(), "outcome": e.outcome}
                                       for e in SymptomEpisode.objects.filter(user=person, date__gte=today - timedelta(days=14))[:12]]
        if flags["dates"]:
            card["dates"] = [{"title": d.title, "kind": d.kind, "date": d.date.isoformat(), "time": d.time.strftime("%H:%M") if d.time else None}
                             for d in HealthDate.objects.filter(user=person, shared=True, date__gte=today)[:8]]
        if flags["emergency_card"]:
            from health.views import emergency_payload
            card["emergency_card"] = emergency_payload(person)
        if flags["medications"]:
            card["medications"] = list(person.medications.filter(active=True).values("name", "kind", "frequency"))
        return Response(card)

    def delete(self, request, pk):
        other = User.objects.filter(pk=pk).first()
        if other:
            disconnect(request.user, other)
        return Response(status=204)


class NudgeView(APIView):
    def post(self, request):
        to = request.data.get("to")
        kind = request.data.get("kind", "thinking")
        if kind not in NUDGES:
            kind = "thinking"
        if not CircleMember.objects.filter(owner=request.user, member_id=to).exists():
            return Response({"detail": "Not in your circle."}, status=404)
        recipient = User.objects.get(pk=to)
        message = (request.data.get("message") or "")[:200]
        n = Nudge.objects.create(sender=request.user, recipient=recipient, kind=kind, message=message)
        from notify.services import queue
        queue(recipient, "nudge", f"{request.user.display_name} {NUDGES[kind]}", message or "Open Ruvia to send one back.",
              "/care", timezone.now(), dedupe=f"nudge:{n.id}")
        return Response({"ok": True}, status=201)

    def patch(self, request):
        Nudge.objects.filter(recipient=request.user, read=False).update(read=True)
        return Response({"ok": True})


class SharedCalendarView(APIView):
    """Own health dates plus whatever the circle shares: their dates and predicted periods."""

    def get(self, request):
        me = request.user
        today = user_today(me)
        start = today - timedelta(days=7)
        end = today + timedelta(days=60)
        items = [{"title": d.title, "kind": d.kind, "date": d.date.isoformat(), "time": d.time.strftime("%H:%M") if d.time else None,
                  "who": "You", "who_id": me.id, "id": d.id, "location": d.location, "notes": d.notes, "mine": True}
                 for d in HealthDate.objects.filter(user=me, date__range=(start, end))]
        if me.track_cycle:
            c = cycle_summary(me)
            if c.get("has_data"):
                items.append({"title": "Period expected", "kind": "cycle", "date": c["next_start"], "who": "You", "who_id": me.id, "mine": True})
        for g in ShareGrant.objects.filter(viewer=me).select_related("owner"):
            p = g.owner
            if g.dates:
                items += [{"title": d.title, "kind": d.kind, "date": d.date.isoformat(), "time": d.time.strftime("%H:%M") if d.time else None,
                           "who": p.display_name, "who_id": p.id, "mine": False}
                          for d in HealthDate.objects.filter(user=p, shared=True, date__range=(start, end))]
            if g.cycle and p.track_cycle:
                c = cycle_summary(p)
                if c.get("has_data"):
                    items.append({"title": "Period expected", "kind": "cycle", "date": c["next_start"], "who": p.display_name,
                                  "who_id": p.id, "mine": False})
        items.sort(key=lambda x: (x["date"], x.get("time") or ""))
        return Response({"items": items})
