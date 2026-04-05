import csv

from django.core.management.base import BaseCommand
from reports.models import Report


class Command(BaseCommand):
    help = "Genera CSV de projectId y month para JMeter."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="jmeter/report_requests.csv",
            help="Ruta de salida del CSV.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Número máximo de filas a exportar.",
        )

    def handle(self, *args, **options):
        output = options["output"]
        limit = options["limit"]

        queryset = Report.objects.all().order_by("project_id", "month")
        if limit is not None:
            queryset = queryset[:limit]

        rows = list(queryset.values_list("project_id", "month"))

        import os

        os.makedirs("jmeter", exist_ok=True)

        with open(output, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["projectId", "month"])
            writer.writerows(rows)

        self.stdout.write(
            self.style.SUCCESS(f"CSV generado correctamente en: {output} ({len(rows)} filas)")
        )
