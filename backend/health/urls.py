from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register("medications", views.MedicationViewSet, basename="medications")
router.register("allergies", views.AllergyViewSet, basename="allergies")
router.register("cabinet", views.CabinetViewSet, basename="cabinet")
router.register("health-dates", views.HealthDateViewSet, basename="health-dates")

urlpatterns = [
    path("today/", views.TodayView.as_view()),
    path("days/<str:day>/", views.DayView.as_view()),
    path("days/<str:day>/tags/", views.TagView.as_view()),
    path("days/<str:day>/tags/<int:pk>/", views.TagView.as_view()),
    path("calendar/", views.CalendarView.as_view()),
    path("water/", views.WaterView.as_view()),
    path("water/<int:pk>/", views.WaterView.as_view()),
    path("episodes/", views.EpisodeView.as_view()),
    path("episodes/<int:pk>/", views.EpisodeView.as_view()),
    path("rough-day/", views.RoughDayView.as_view()),
    path("moods/", views.MoodListView.as_view()),
    path("moods/feedback/", views.MoodFeedbackView.as_view()),
    path("insights/", views.InsightsView.as_view()),
    path("cycle/", views.CycleView.as_view()),
    path("cycle/confirm/", views.CycleConfirmView.as_view()),
    path("cycle/<int:pk>/", views.CycleEntryView.as_view()),
    path("report.pdf", views.ReportView.as_view()),
    path("export/", views.ExportView.as_view()),
    path("emergency-card/", views.EmergencyView.as_view()),
    path("interactions/", views.InteractionCheckView.as_view()),
    path("geo/", views.GeoView.as_view()),
    path("explainer/", views.ExplainerView.as_view()),
    path("medications/<int:pk>/taken/", views.MedTakenView.as_view()),
    path("goals/", views.GoalsView.as_view()),
    path("goals/<int:pk>/", views.GoalCheckView.as_view()),
] + router.urls
