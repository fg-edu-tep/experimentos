from django.urls import path

from .views import clear_cache, health_check, report_view

urlpatterns = [
    path("health/", health_check, name="health"),
    path("report/", report_view, name="report"),
    path("cache/clear/", clear_cache, name="clear_cache"),
]
