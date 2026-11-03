from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse({"ok": True, "app": "ruvia"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check),
    path("api/", include("accounts.urls")),
    path("api/", include("health.urls")),
    path("api/", include("assistant.urls")),
    path("api/", include("care.urls")),
    path("api/", include("notify.urls")),
]
