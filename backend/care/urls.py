from django.urls import path

from . import views

urlpatterns = [
    path("care/", views.CareView.as_view()),
    path("care/invite/", views.InviteView.as_view()),
    path("care/invites/<int:pk>/<str:action>/", views.InviteActionView.as_view()),
    path("care/share/<int:viewer_id>/", views.ShareView.as_view()),
    path("care/people/<int:pk>/", views.PersonView.as_view()),
    path("care/nudge/", views.NudgeView.as_view()),
    path("care/calendar/", views.SharedCalendarView.as_view()),
]
