from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.InboxView.as_view()),
    path("push/key/", views.PushKeyView.as_view()),
    path("push/subscribe/", views.PushSubscribeView.as_view()),
    path("push/test/", views.PushTestView.as_view()),
    path("cron/tick/", views.CronTickView.as_view()),
]
