import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from reports.models import Report


class Command(BaseCommand):
    help = "Genera datos de prueba para el experimento de latencia."

    def add_arguments(self, parser):
        parser.add_argument(
            "--projects",
            type=int,
            default=100,
            help="Número de proyectos a generar.",
        )
        parser.add_argument(
            "--months",
            type=int,
            default=3,
            help="Número de meses por proyecto.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Borra los datos existentes antes de sembrar.",
        )

    def handle(self, *args, **options):
        projects = options["projects"]
        months = options["months"]
        replace = options["replace"]

        if replace:
            deleted_count, _ = Report.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Se eliminaron {deleted_count} registros existentes.")
            )

        month_values = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
        selected_months = month_values[:months]

        reports_to_create = []

        for project_index in range(1, projects + 1):
            project_id = f"proj-{project_index:03d}"

            for month in selected_months:
                total_cost = Decimal(random.randint(500000, 5000000))
                idle_resources = random.randint(0, 10)
                underutilized_instances = random.randint(0, 8)
                estimated_waste = Decimal(random.randint(50000, 800000))

                reports_to_create.append(
                    Report(
                        project_id=project_id,
                        month=month,
                        total_cost=total_cost,
                        currency="COP",
                        idle_resources=idle_resources,
                        underutilized_instances=underutilized_instances,
                        estimated_waste=estimated_waste,
                    )
                )

        Report.objects.bulk_create(reports_to_create, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(f"Seed completado: {len(reports_to_create)} reportes creados.")
        )
