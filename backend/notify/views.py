import secrets

from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, PushSubscription
from .scheduler import run_tick
from .services import push


def ser(n):
    return {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "url": n.url, "payload": n.payload,
            "at": (n.sent_at or n.send_at).isoformat(), "read": bool(n.read_at)}


class InboxView(APIView):
    def get(self, request):
        qs = Notification.objects.filter(user=request.user, cancelled=False, send_at__lte=timezone.now()).order_by("-send_at")[:60]
        unread = Notification.objects.filter(user=request.user, cancelled=False, read_at__isnull=True,
                                             send_at__lte=timezone.now()).count()
        return Response({"items": [ser(n) for n in qs], "unread": unread})

    def post(self, request):
        """Mark read. Body: {"ids": [...]} or {"all": true}."""
        qs = Notification.objects.filter(user=request.user, read_at__isnull=True)
        if not request.data.get("all"):
            qs = qs.filter(id__in=request.data.get("ids", []))
        qs.update(read_at=timezone.now())
        return Response({"ok": True})


class PushKeyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"public_key": settings.VAPID_PUBLIC_KEY, "enabled": bool(settings.VAPID_PUBLIC_KEY)})


class PushSubscribeView(APIView):
    def post(self, request):
        sub = request.data.get("subscription") or {}
        endpoint, keys = sub.get("endpoint"), sub.get("keys") or {}
        if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
            return Response({"detail": "Subscription is missing fields."}, status=400)
        PushSubscription.objects.update_or_create(endpoint=endpoint, defaults={
            "user": request.user, "p256dh": keys["p256dh"], "auth": keys["auth"],
            "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:200]})
        return Response({"ok": True})

    def delete(self, request):
        PushSubscription.objects.filter(user=request.user, endpoint=request.data.get("endpoint", "")).delete()
        return Response(status=204)


class PushTestView(APIView):
    def post(self, request):
        n = push(request.user, "Ruvia is set up", "This is how your reminders will look.", "/")
        return Response({"sent": n, "push_configured": bool(settings.VAPID_PUBLIC_KEY)})


class CronTickView(APIView):
    """Called by the scheduler (Render cron or GitHub Actions) with the shared secret."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def post(self, request):
        given = request.headers.get("X-Cron-Secret", "")
        if not settings.CRON_SECRET or not secrets.compare_digest(given, settings.CRON_SECRET):
            return Response({"detail": "Forbidden"}, status=403)
        return Response(run_tick())
