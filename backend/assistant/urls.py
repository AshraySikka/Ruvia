from django.urls import path

from . import views

urlpatterns = [
    path("chat/", views.ChatView.as_view()),
    path("transcribe/", views.TranscribeView.as_view()),
    path("followups/<int:pk>/", views.FollowUpView.as_view()),
    path("assistant/status/", views.StatusView.as_view()),
]
