from django.core.cache import cache
from django.core.management.base import BaseCommand
from reports.models import Report

CACHE_TTL_SECONDS = 300


class Command(BaseCommand):
    help = "Precarga reportes en Redis para pruebas warm cache."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Número máximo de reportes a precargar.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        queryset = Report.objects.all().order_by("project_id", "month")
        if limit is not None:
            queryset = queryset[:limit]

        count = 0

        for report in queryset:
            cache_key = f"report:{report.project_id}:{report.month}"
            payload = {
                "projectId": report.project_id,
                "month": report.month,
                "source": "database",
                "report": {
                    "totalCost": float(report.total_cost),
                    "currency": report.currency,
                    "wasteIndicators": {
                        "idleResources": report.idle_resources,
                        "underutilizedInstances": report.underutilized_instances,
                        "estimatedWaste": float(report.estimated_waste),
                    },
                },
            }

            cache.set(cache_key, payload, timeout=CACHE_TTL_SECONDS)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Warm cache completado: {count} reportes cargados en Redis.")
        )
