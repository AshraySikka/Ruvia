"""
Creates two demo accounts with enough history to show every feature.

  Jane  demoruvia@yopmail.com   (shares with Joe)
  Joe   demo1ruvia@yopmail.com  (in Jane's care circle)

Run:  python manage.py seed_demo          (safe to run again, it rebuilds both)
Yopmail inboxes are public, so never put real data in these accounts.
"""
import random
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from assistant.engine import handle_message
from assistant.models import ChatMessage, FollowUp
from care.models import Nudge, ShareGrant
from care.services import connect
from config.utils import user_today, user_tz
from health.models import (Allergy, CabinetItem, CycleEntry, DailyLog, DayTag, EmergencyCard, Goal, GoalCheck, HealthDate,
                           Medication, MedLog, MoodFeedback, SymptomEpisode, WaterLog, WeatherDay)
from health.services.library import SYMPTOMS
from notify.models import Notification

JANE = "demoruvia@yopmail.com"
JOE = "demo1ruvia@yopmail.com"


class Command(BaseCommand):
    help = "Create or rebuild the Jane and Joe demo accounts."

    def add_arguments(self, parser):
        parser.add_argument("--if-missing", action="store_true", help="Only seed when the demo accounts do not exist yet.")

    def handle(self, *args, **opts):
        User = get_user_model()
        if opts.get("if_missing") and User.objects.filter(email=JANE).exists():
            self.stdout.write("Demo accounts already exist. Skipping.")
            return
        with transaction.atomic():
            User.objects.filter(email__in=[JANE, JOE]).delete()
            jane = User.objects.create_user(
                JANE, settings.DEMO_PASSWORD, first_name="Jane", email_verified=True, onboarded=True, sex="female",
                birth_year=1995, water_goal_ml=2200, track_cycle=True, city="Toronto, Ontario, CA", latitude=43.6532,
                longitude=-79.3832, avatar_hue=18, checkins_per_day=3, first_checkin_time=time(9, 30), checkin_interval_hours=5,
                quiet_start=time(22, 30), quiet_end=time(7, 0),
            )
            joe = User.objects.create_user(
                JOE, settings.DEMO_PASSWORD, first_name="Joe", email_verified=True, onboarded=True, sex="male",
                birth_year=1993, water_goal_ml=2800, track_cycle=False, city="Toronto, Ontario, CA", latitude=43.6532,
                longitude=-79.3832, avatar_hue=150, checkins_per_day=2, first_checkin_time=time(10, 0), checkin_interval_hours=8,
            )
            self.seed_jane(jane)
            self.seed_joe(joe)
            self.seed_circle(jane, joe)
        self.stdout.write(self.style.SUCCESS(
            f"Demo ready.\n  Jane: {JANE}\n  Joe:  {JOE}\n  Password: {settings.DEMO_PASSWORD}"))

    # helpers
    def at(self, user, day, hh, mm=0):
        return datetime.combine(day, time(hh, mm), tzinfo=user_tz(user))

    def weather(self, user, today, days, rnd):
        p, drops = 1014.0, []
        for i in range(days, -1, -1):
            d = today - timedelta(days=i)
            change = rnd.uniform(-2.5, 2.5)
            if i in (66, 58, 47, 39, 31, 22, 15, 8, 2):
                change = rnd.uniform(-7.5, -4.6)
                drops.append(d)
            p = max(992, min(1032, p + change + (1014 - p) * 0.08))
            WeatherDay.objects.create(user=user, date=d, temp_max=round(rnd.uniform(3, 14), 1), temp_min=round(rnd.uniform(-4, 5), 1),
                                      pressure_mean=round(p, 1), pressure_change=round(change, 1), humidity_mean=round(rnd.uniform(55, 88), 1))
        return set(drops)

    def episode(self, user, day, key, severity, hh, tried, outcome, triggers=(), minutes=None):
        start = self.at(user, day, hh, 15)
        mins = minutes or {"mild": 70, "moderate": 140, "severe": 240, "extreme": 300}[severity]
        return SymptomEpisode.objects.create(
            user=user, key=key, label=SYMPTOMS[key]["label"], date=day, severity=severity, started_at=start,
            ended_at=start + timedelta(minutes=mins) if outcome == "better" else None,
            duration_minutes=mins if outcome == "better" else None, triggers=list(triggers), tried=list(tried),
            outcome=outcome, resolved=outcome != "unknown",
        )

    def tag(self, user, day, label, kind="symptom"):
        DayTag.objects.get_or_create(user=user, date=day, label=label, defaults={"kind": kind, "source": "auto"})

    def chat(self, user, when, text, reply, payload=None, kind="checkin", source="text"):
        ChatMessage.objects.create(user=user, role="user", kind=kind, text=text, source=source, created_at=when)
        ChatMessage.objects.create(user=user, role="assistant", kind=kind, text=reply, payload=payload or {"type": "checkin"},
                                   created_at=when + timedelta(seconds=4), provider="seed")

    # Jane
    def seed_jane(self, u):
        rnd = random.Random(11)
        today = user_today(u)
        DAYS = 75
        drops = self.weather(u, today, DAYS, rnd)

        Medication.objects.create(user=u, name="Levothyroxine", kind="prescribed", dose_text="As prescribed", frequency="Every morning, empty stomach",
                                  start_date=today - timedelta(days=700), notes="Thyroid")
        vit = Medication.objects.create(user=u, name="Vitamin D3", kind="supplement", dose_text="1 softgel", frequency="Daily with lunch",
                                        start_date=today - timedelta(days=200))
        Medication.objects.create(user=u, name="Magnesium glycinate", kind="supplement", frequency="Evenings in the week before my period",
                                  start_date=today - timedelta(days=60))
        Allergy.objects.create(user=u, substance="Penicillin", reaction="Hives")
        for name, note in [("Pepcid", "Bathroom cabinet"), ("Tylenol", "Kitchen drawer"), ("Advil", "Purse"), ("Tums", "Nightstand"),
                           ("Ginger tea", "Running low"), ("Heating pad", "Bedroom closet")]:
            CabinetItem.objects.create(user=u, name=name, note=note, running_low=name == "Ginger tea",
                                       expires_on=today + timedelta(days=rnd.randint(60, 400)) if name not in ("Heating pad", "Ginger tea") else None)
        for i in range(10):
            MedLog.objects.create(user=u, medication=vit, name=vit.name, taken_at=self.at(u, today - timedelta(days=i), 13, 5))
        EmergencyCard.objects.create(
            user=u, full_name="Jane Demo", date_of_birth=datetime(1995, 4, 12).date(), blood_type="O+",
            conditions="Hypothyroidism, managed with medication", doctor="Dr. Meera Shah, Bloor West Family Health, 416-555-0190",
            health_card_note="Ontario health card in wallet", notes="Allergic to penicillin.",
            contacts=[{"name": "Joe", "relation": "Husband", "phone": "416-555-0142"}, {"name": "Mom", "relation": "Mother", "phone": "905-555-0117"}],
        )
        HealthDate.objects.create(user=u, title="Family doctor checkup", kind="checkup", date=today + timedelta(days=6), time=time(10, 30),
                                  location="Bloor West Family Health", notes="Bring the doctor summary")
        HealthDate.objects.create(user=u, title="Thyroid blood test", kind="test", date=today + timedelta(days=12), time=time(8, 0),
                                  location="LifeLabs", notes="Skip levothyroxine until after the draw")
        HealthDate.objects.create(user=u, title="Levothyroxine renewal", kind="renewal", date=today + timedelta(days=20))
        HealthDate.objects.create(user=u, title="Flu shot", kind="vaccine", date=today - timedelta(days=3), time=time(17, 30), location="Shoppers")

        # Cycles: average 29 days, next one due in about 4 days
        starts = [today - timedelta(days=d) for d in (112, 82, 54, 25)]
        period = set()
        for i, s in enumerate(starts):
            CycleEntry.objects.create(user=u, start_date=s, end_date=s + timedelta(days=4), flow="medium" if i % 2 else "heavy",
                                      pain=[6, 5, 6, 4][i], on_time=None if i == 0 else True)
            for k in range(5):
                period.add(s + timedelta(days=k))

        late_dinners = {today - timedelta(days=d) for d in (70, 63, 55, 48, 41, 33, 26, 19, 12, 5)}
        low_water = {today - timedelta(days=d) for d in (67, 59, 52, 47, 40, 31, 23, 16, 9, 2, 1)}
        skip = {today - timedelta(days=d) for d in (73, 61, 44, 29)}
        headache_days = {today - timedelta(days=d) for d in (67, 58, 52, 47, 39, 31, 23, 16, 9, 2)}
        acidity_days = {today - timedelta(days=d) for d in (70, 63, 55, 48, 41, 33, 26, 12, 5)}

        for i in range(DAYS, 0, -1):
            d = today - timedelta(days=i)
            if d in skip:
                continue
            phys, ment = rnd.randint(7, 9), rnd.randint(6, 9)
            sleep = round(rnd.uniform(6.5, 8.4), 1)
            moods = []
            if d.weekday() == 6 and rnd.random() < 0.7:
                ment -= 3
                moods = ["overwhelmed"]
                self.tag(u, d, "Overwhelmed", "mood")
                self.episode(u, d, "stress", "moderate", 19, ["Write down the 3 things on your mind", "A 10 minute walk without your phone"],
                             "better", ["Long workday"])
                self.tag(u, d, "Stress")
            if d in low_water:
                sleep = round(rnd.uniform(5.2, 6.4), 1)
            total_water = rnd.randint(800, 1250) if d in low_water else rnd.randint(1850, 2700)
            for k, amt in enumerate(self._split(total_water, rnd)):
                WaterLog.objects.create(user=u, date=d, amount_ml=amt, logged_at=self.at(u, d, min(21, 8 + k * 1), rnd.randint(0, 59)))
            if d in late_dinners:
                self.tag(u, d, "Late dinner", "trigger")
            if d in headache_days:
                sev = rnd.choice(["moderate", "moderate", "severe", "mild"])
                tried = rnd.choice([["Drink a full glass of water now", "Tylenol"], ["Rest in a quiet, dim room for 20 minutes", "Drink a full glass of water now"],
                                    ["Tylenol", "Cold compress on your forehead or the back of your neck"]])
                trig = ["Dehydrated"] if d in low_water else []
                if d in drops:
                    trig.append("Weather change")
                self.episode(u, d, "headache", sev, rnd.choice([11, 14, 16]), tried, "better" if rnd.random() < 0.85 else "same", trig)
                self.tag(u, d, "Headache")
                phys -= {"mild": 1, "moderate": 3, "severe": 4}[sev]
            if d in acidity_days:
                sev = rnd.choice(["moderate", "severe", "moderate"])
                tried = rnd.choice([["Sip warm water slowly", "Pepcid"], ["Pepcid", "Stay upright for at least 2 hours, no lying down"],
                                    ["Tums", "Sip warm water slowly"], ["Sip warm water slowly", "Pepcid"]])
                self.episode(u, d, "acidity", sev, 22, tried, "better", ["Late dinner", "Spicy food"] if rnd.random() < 0.5 else ["Late dinner"])
                self.tag(u, d, "Acidity")
                phys -= 2
            if d in period and (d - timedelta(days=1)) not in period:
                pass
            if d in period:
                day_n = min((d - s).days for s in starts if (d - s).days >= 0) + 1
                if day_n <= 2:
                    self.episode(u, d, "cramps", "moderate" if day_n == 2 else "severe", 9,
                                 ["Heating pad or hot water bottle on your lower belly", "Advil"], "better", [])
                    self.tag(u, d, "Cramps")
                    phys -= 3
                    self.tag(u, d, "Period", "note")
            if rnd.random() < 0.08:
                sleep = round(rnd.uniform(4.5, 5.6), 1)
                self.episode(u, d, "insomnia", "mild", 7, ["Skip caffeine after noon"], "better")
                self.tag(u, d, "Poor sleep")
                ment -= 2
            log = DailyLog.objects.create(user=u, date=d, physical_rating=max(2, phys), mental_rating=max(2, ment), sleep_hours=sleep, moods=moods)
            if i == 2:
                log.rough_day = True
                log.mental_rating = 3
                log.save()
                self.tag(u, d, "Rough day", "mood")

        for _ in range(2):
            MoodFeedback.objects.create(user=u, mood_key="hate_everyone", activity="Eat something", helped=True)
        MoodFeedback.objects.create(user=u, mood_key="overwhelmed", activity="Write it down and pick one thing", helped=True)

        # Recent conversation history
        y3, y2, y1 = today - timedelta(days=3), today - timedelta(days=2), today - timedelta(days=1)
        self.chat(u, self.at(u, today - timedelta(days=5), 22, 40), "Acidity again after a late dinner, burning a bit",
                  "Sorry, that burning is no fun. Last time warm water and Pepcid settled it, and you have Pepcid at home. "
                  "Stay upright for a couple of hours tonight. I'll check back in an hour.",
                  {"type": "checkin", "tags": ["Acidity", "Late dinner"]})
        self.chat(u, self.at(u, today - timedelta(days=5), 23, 45), "Feeling better. Tried: Sip warm water slowly, Pepcid",
                  "Really glad it eased. I noted that warm water and Pepcid helped, so they stay at the top next time.",
                  {"type": "followup", "answer": "better"}, kind="followup")
        self.chat(u, self.at(u, y3, 17, 50), "Got my flu shot, arm is a bit sore but I'm fine",
                  "Nice, one less thing on the list. A sore arm for a day or two is common. Keep moving it gently.",
                  {"type": "checkin", "tags": ["Flu shot"]})
        self.tag(u, y3, "Flu shot", "note")
        self.chat(u, self.at(u, y2, 20, 10), "Honestly feel like I hate everyone today", "Hunger shows up as irritation more often than we think. "
                  "You said eating something helped before, so start there. Something with protein.",
                  {"type": "checkin", "tags": ["Irritable"], "mood": {"key": "hate_everyone", "label": "Feeling like you hate everyone",
                   "do": "Eat something", "why": "You said this helped before.", "more": ["Snack with protein", "Glass of water too"], "helped_before": True}})
        self.tag(u, y2, "Irritable", "mood")
        self.chat(u, self.at(u, y1, 15, 20), "What helped my acidity last time?",
                  "In your logs, acidity came up 9 times over the last 3 months, almost always after a late dinner. "
                  "Pepcid and sipping warm water helped most, 6 times. Staying upright helped too. An earlier, lighter dinner is the one change worth trying.",
                  {"type": "history", "period": "the last 3 months", "cards": [{"label": "Acidity", "count": 9, "helped": [{"item": "Pepcid", "times": 6}, {"item": "Sip warm water slowly", "times": 6}],
                                                  "triggers": ["Late dinner", "Spicy food"], "by_month": {}}]}, kind="ask")

        # Today: a real check-in through the pipeline
        DailyLog.objects.get_or_create(user=u, date=today, defaults={"mental_rating": 7, "sleep_hours": 6.1})
        WaterLog.objects.create(user=u, date=today, amount_ml=350, logged_at=timezone.now() - timedelta(hours=2))
        WaterLog.objects.create(user=u, date=today, amount_ml=250, logged_at=timezone.now() - timedelta(minutes=40))
        result = handle_message(u, "Woke up with a pretty bad headache, I think I didn't drink enough water yesterday", source="voice")
        for m in result["messages"]:
            ChatMessage.objects.filter(pk=m["id"]).update(created_at=timezone.now() - timedelta(minutes=25))
        FollowUp.objects.filter(user=u, status="pending").update(due_at=timezone.now() + timedelta(minutes=35))
        Notification.objects.filter(user=u, kind="followup").update(send_at=timezone.now() + timedelta(minutes=35))

        now = timezone.now()
        for title, body, kind, url, hours in [
            ("How are you today?", "Tell me in a sentence or a voice note. It takes ten seconds.", "checkin", "/chat", 1),
            ("600 ml so far today", "A glass now keeps you on track for 2200 ml.", "water", "/?water=1", 0.5),
            ("Your week in Ruvia", "See what changed this week.", "weekly", "/insights", 30),
            ("Tomorrow: Flu shot", "Vaccine at 5:30 PM.", "date", "/care?tab=dates", 96),
        ]:
            Notification.objects.create(user=u, kind=kind, title=title, body=body, url=url, send_at=now - timedelta(hours=hours),
                                        sent_at=now - timedelta(hours=hours), read_at=now if hours > 20 else None)

    def _split(self, total, rnd):
        parts, left = [], total
        while left > 0:
            amt = min(left, rnd.choice([250, 250, 350, 500]))
            parts.append(amt)
            left -= amt
        return parts

    # Joe
    def seed_joe(self, u):
        rnd = random.Random(23)
        today = user_today(u)
        self.weather(u, today, 40, random.Random(11))
        Medication.objects.create(user=u, name="Ramipril", kind="prescribed", dose_text="As prescribed", frequency="Every morning",
                                  start_date=today - timedelta(days=400), notes="Blood pressure")
        CabinetItem.objects.create(user=u, name="Tylenol", note="Kitchen")
        CabinetItem.objects.create(user=u, name="Voltaren gel", note="Gym bag")
        HealthDate.objects.create(user=u, title="Dentist cleaning", kind="appointment", date=today + timedelta(days=9), time=time(16, 0),
                                  location="Queen West Dental")
        EmergencyCard.objects.create(user=u, full_name="Joe Demo", blood_type="A+", conditions="High blood pressure",
                                     contacts=[{"name": "Jane", "relation": "Wife", "phone": "416-555-0138"}])
        for i in range(40, 0, -1):
            d = today - timedelta(days=i)
            if rnd.random() < 0.12:
                continue
            phys, ment = rnd.randint(6, 9), rnd.randint(6, 9)
            if i in (34, 27, 20, 13, 6):
                self.episode(u, d, "back_pain", "moderate", 19, ["Heat for 15 to 20 minutes", "Gentle stretches like knee to chest"], "better", ["Gym"])
                self.tag(u, d, "Back pain")
                phys -= 3
            if i in (30, 16):
                self.episode(u, d, "acidity", "mild", 23, ["Tums"], "better", ["Spicy food"])
                self.tag(u, d, "Acidity")
            DailyLog.objects.create(user=u, date=d, physical_rating=phys, mental_rating=ment, sleep_hours=round(rnd.uniform(6, 8), 1))
            for amt in self._split(rnd.randint(1900, 3000), rnd):
                WaterLog.objects.create(user=u, date=d, amount_ml=amt, logged_at=self.at(u, d, 12))
        DailyLog.objects.create(user=u, date=today, physical_rating=8, mental_rating=7, sleep_hours=7.2)
        WaterLog.objects.create(user=u, date=today, amount_ml=500, logged_at=timezone.now() - timedelta(hours=1))
        self.chat(u, self.at(u, today - timedelta(days=6), 20, 5), "Lower back is sore after deadlifts",
                  "Sounds like it worked hard today. Heat and gentle stretching helped you last time. "
                  "Since you take ramipril, check with a pharmacist before ibuprofen. Tylenol is an option that fits.",
                  {"type": "checkin", "tags": ["Back pain", "Gym"]})

    def seed_circle(self, jane, joe):
        connect(jane, joe, relation_a="Husband", relation_b="Wife")
        ShareGrant.objects.filter(owner=jane, viewer=joe).update(scores=True, tags=True, water=True, cycle=True, cycle_alerts=True,
                                                                  rough_day=True, dates=True, emergency_card=True)
        ShareGrant.objects.filter(owner=joe, viewer=jane).update(scores=True, rough_day=True, water=True, dates=True, emergency_card=True)
        today = user_today(jane)
        now = timezone.now()
        Nudge.objects.create(sender=joe, recipient=jane, kind="hug", message="Hope the headache eases. Tea is on the counter.")
        Nudge.objects.create(sender=jane, recipient=joe, kind="water", message="", read=True)
        Notification.objects.create(user=jane, kind="nudge", title="Joe sent you a hug", body="Hope the headache eases. Tea is on the counter.",
                                    url="/care", send_at=now - timedelta(minutes=10), sent_at=now - timedelta(minutes=10))
        Notification.objects.create(user=joe, kind="care", title="Jane is having a rough day",
                                    body="No details, just a heads up. Maybe check in or send a little love.", url=f"/care/person/{jane.id}",
                                    send_at=now - timedelta(days=2), sent_at=now - timedelta(days=2))
        goals = [("Walk 20 minutes", "", "walk", 1), ("8 glasses of water", "", "glasses", 8), ("Lights out by 11", "", "night", 1)]
        rnd = random.Random(5)
        for title, emoji, unit, target in goals:
            g = Goal.objects.create(title=title, emoji=emoji, unit=unit, target=target, created_by=jane)
            g.members.add(jane, joe)
            for i in range(0, 7):
                d = today - timedelta(days=i)
                for person in (jane, joe):
                    if i == 0 and person == jane and target > 1:
                        GoalCheck.objects.create(goal=g, user=person, date=d, value=3)
                    elif i == 0:
                        continue
                    elif rnd.random() < 0.75:
                        GoalCheck.objects.create(goal=g, user=person, date=d, value=target if rnd.random() < 0.7 else max(1, target - 2))
