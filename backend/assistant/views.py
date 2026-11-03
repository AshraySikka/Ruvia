from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from . import engine, llm
from .models import ChatMessage, FollowUp


class ChatThrottle(UserRateThrottle):
    scope = "chat"


class ChatView(APIView):
    def get_throttles(self):
        return [ChatThrottle()] if self.request.method == "POST" else super().get_throttles()

    def get(self, request):
        qs = ChatMessage.objects.filter(user=request.user)
        before = request.query_params.get("before")
        if before:
            qs = qs.filter(id__lt=before)
        items = list(qs.order_by("-created_at", "-id")[:40])[::-1]
        return Response({"messages": [engine.serialize_message(m) for m in items], "status": llm.status()})

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "Say a little about how you feel."}, status=400)
        result = engine.handle_message(request.user, text, source=request.data.get("source", "text"),
                                       mode=request.data.get("mode", "auto"), client_id=str(request.data.get("client_id", ""))[:64])
        return Response(result, status=201)


class TranscribeView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        f = request.FILES.get("audio")
        if not f:
            return Response({"detail": "No audio received."}, status=400)
        if f.size > 15 * 1024 * 1024:
            return Response({"detail": "That recording is too long. Keep it under a couple of minutes."}, status=400)
        try:
            text = llm.transcribe(f.read(), f.name or "voice.webm")
        except llm.ProviderError as exc:
            return Response({"detail": str(exc)}, status=503)
        except Exception:
            return Response({"detail": "Could not reach the transcription service. Try again or type instead."}, status=503)
        return Response({"text": text})


class FollowUpView(APIView):
    def get(self, request, pk):
        fu = FollowUp.objects.filter(user=request.user, pk=pk).select_related("episode").first()
        if not fu:
            return Response({"detail": "Not found."}, status=404)
        from health.services.remedies import suggestions_for, tried_options
        sug = suggestions_for(request.user, fu.episode.key, fu.episode.severity)
        return Response({"id": fu.id, "status": fu.status, "answer": fu.answer, "due_at": fu.due_at.isoformat(),
                         "episode": {"id": fu.episode.id, "label": fu.episode.label, "severity": fu.episode.severity,
                                     "started_at": fu.episode.started_at.isoformat(), "tried": fu.episode.tried},
                         "tried_options": tried_options(sug), "tip": sug["home"][0] if sug else None})

    def post(self, request, pk):
        fu = FollowUp.objects.filter(user=request.user, pk=pk).select_related("episode").first()
        if not fu:
            return Response({"detail": "Not found."}, status=404)
        answer = request.data.get("answer")
        if answer not in ("better", "same", "worse"):
            return Response({"detail": "Pick better, same or worse."}, status=400)
        return Response(engine.answer_followup(request.user, fu, answer, request.data.get("tried"), request.data.get("note", "")))


class StatusView(APIView):
    def get(self, request):
        return Response(llm.status())
