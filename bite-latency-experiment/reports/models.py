from decimal import Decimal

from django.db import models


class Report(models.Model):
    project_id = models.CharField(max_length=100)
    month = models.CharField(max_length=7)  # formato: YYYY-MM
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="COP")
    idle_resources = models.IntegerField(default=0)
    underutilized_instances = models.IntegerField(default=0)
    estimated_waste = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("project_id", "month")
        indexes = [
            models.Index(fields=["project_id", "month"]),
        ]

    def __str__(self):
        return f"{self.project_id} - {self.month}"
