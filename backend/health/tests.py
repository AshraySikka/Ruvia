from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from care.services import connect
from care.models import ShareGrant
from config.utils import user_today
from health.models import Allergy, CycleEntry, Medication
from health.services.cycle import summary
from health.services.remedies import check_otc, suggestions_for
from health.services.safety import screen, strip_doses
from notify.models import Notification
from notify.scheduler import run_tick

User = get_user_model()


def make_user(email="a@test.com", **kw):
    defaults = dict(email_verified=True, onboarded=True, first_name="Ana")
    defaults.update(kw)
    return User.objects.create_user(email, "Pass-word-123", **defaults)


class SafetyTests(TestCase):
    def test_crisis_language(self):
        for text in ["I want to kill myself", "honestly i want to die", "thinking about hurting myself", "no reason to live"]:
            self.assertEqual(screen(text)[0], "crisis", text)

    def test_red_flags(self):
        self.assertEqual(screen("worst headache of my life")[0], "red_flag")
        self.assertEqual(screen("chest pain and my arm feels weird")[0], "red_flag")
        self.assertEqual(screen("my lips are swelling after peanuts")[0], "red_flag")

    def test_ordinary_entries_pass(self):
        for text in ["mild headache after work", "acidity after dinner", "I hate everyone today", "feeling tired"]:
            self.assertIsNone(screen(text)[0], text)

    def test_doses_are_removed(self):
        out = strip_doses("Try Tylenol 500 mg every 6 hours. Drink 500 ml of water.")
        self.assertNotIn("500 mg", out)
        self.assertIn("500 ml of water", out)


class InteractionTests(TestCase):
    def test_blood_thinner_rules_out_ibuprofen(self):
        ok, level, reasons = check_otc("ibuprofen", ["Warfarin"], [])
        self.assertFalse(ok)
        self.assertEqual(level, "avoid")

    def test_thyroid_med_flags_antacid(self):
        ok, level, _ = check_otc("calcium_carbonate", ["Synthroid"], [])
        self.assertTrue(ok)
        self.assertEqual(level, "caution")

    def test_allergy_rules_out_family(self):
        ok, _, _ = check_otc("naproxen", [], ["Aspirin"])
        self.assertFalse(ok)

    def test_suggestions_skip_unsafe_options(self):
        u = make_user()
        Medication.objects.create(user=u, name="Eliquis")
        s = suggestions_for(u, "headache")
        keys = [o["key"] for o in s["otc"]]
        self.assertIn("acetaminophen", keys)
        self.assertNotIn("ibuprofen", keys)
        self.assertTrue(any(o["key"] == "ibuprofen" for o in s["skipped"]))


class ChatTests(TestCase):
    def setUp(self):
        self.u = make_user()
        self.c = APIClient()
        self.c.force_authenticate(self.u)

    def test_checkin_creates_tags_episode_and_followup(self):
        r = self.c.post("/api/chat/", {"text": "having extreme headache because of acidity"}, format="json")
        self.assertEqual(r.status_code, 201)
        payload = r.json()["messages"][1]["payload"]
        self.assertIn("Headache", payload["tags"])
        self.assertIn("Acidity", payload["tags"])
        self.assertIsNotNone(payload["followup"])
        self.assertEqual(self.u.episodes.count(), 2)

    def test_crisis_never_reaches_remedies(self):
        r = self.c.post("/api/chat/", {"text": "I want to end my life"}, format="json")
        msg = r.json()["messages"][1]
        self.assertEqual(msg["payload"]["type"], "crisis")
        self.assertIn("9-8-8", msg["text"])
        self.assertEqual(self.u.episodes.count(), 0)

    def test_offline_replay_is_not_duplicated(self):
        body = {"text": "mild headache", "client_id": "abc-1"}
        self.c.post("/api/chat/", body, format="json")
        self.c.post("/api/chat/", body, format="json")
        self.assertEqual(self.u.messages.filter(role="user").count(), 1)


class CareTests(TestCase):
    def test_nothing_shared_by_default(self):
        a, b = make_user("a@test.com"), make_user("b@test.com", first_name="Ben")
        connect(a, b)
        c = APIClient()
        c.force_authenticate(b)
        card = c.get(f"/api/care/people/{a.id}/").json()
        self.assertNotIn("today", card)
        self.assertNotIn("cycle", card)
        ShareGrant.objects.filter(owner=a, viewer=b).update(scores=True)
        self.assertIn("today", c.get(f"/api/care/people/{a.id}/").json())

    def test_rough_day_sends_no_details(self):
        a, b = make_user("a@test.com"), make_user("b@test.com")
        connect(a, b)
        c = APIClient()
        c.force_authenticate(a)
        c.post("/api/rough-day/")
        n = Notification.objects.get(user=b, kind="care")
        self.assertIn("rough day", n.title)
        self.assertIn("No details", n.body)


class CycleTests(TestCase):
    def test_prediction_uses_average(self):
        u = make_user(sex="female", track_cycle=True)
        today = user_today(u)
        for d in (90, 60, 30):
            CycleEntry.objects.create(user=u, start_date=today - timedelta(days=d), end_date=today - timedelta(days=d - 4))
        s = summary(u)
        self.assertEqual(s["cycle_length"], 30)
        self.assertEqual(s["days_until"], 0)


class SchedulerTests(TestCase):
    def test_tick_is_idempotent(self):
        u = make_user(first_checkin_time=time(0, 0), checkins_per_day=1, quiet_start=time(23, 59), quiet_end=time(0, 0))
        run_tick()
        run_tick()
        self.assertLessEqual(Notification.objects.filter(user=u, kind="checkin").count(), 1)
