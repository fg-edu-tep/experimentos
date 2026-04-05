from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "project_id",
        "month",
        "total_cost",
        "currency",
        "idle_resources",
        "underutilized_instances",
        "estimated_waste",
    )
    search_fields = ("project_id", "month")
    list_filter = ("month", "currency")
