import time

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Report

CACHE_TTL_SECONDS = 300


@require_GET
def health_check(request):
    return JsonResponse({"status": "ok", "service": "bite-latency-experiment"})


@require_GET
def report_view(request):
    start_time = time.perf_counter()

    project_id = request.GET.get("projectId")
    month = request.GET.get("month")

    if not project_id or not month:
        return JsonResponse(
            {"error": "Los parámetros 'projectId' y 'month' son obligatorios."}, status=400
        )

    cache_key = f"report:{project_id}:{month}"

    cached_report = cache.get(cache_key)
    if cached_report is not None:
        response_time_ms = (time.perf_counter() - start_time) * 1000
        print(f"[CACHE HIT] key={cache_key} timeMs={response_time_ms:.2f}")
        cached_report["source"] = "cache"
        cached_report["responseTimeMs"] = round(response_time_ms, 2)
        return JsonResponse(cached_report)

    try:
        report = Report.objects.get(project_id=project_id, month=month)
    except Report.DoesNotExist:
        return JsonResponse(
            {"error": "No se encontró un reporte para ese projectId y month."}, status=404
        )

    response_payload = {
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

    cache.set(cache_key, response_payload, timeout=CACHE_TTL_SECONDS)

    response_time_ms = (time.perf_counter() - start_time) * 1000
    print(f"[CACHE MISS] key={cache_key} timeMs={response_time_ms:.2f}")

    response_payload["responseTimeMs"] = round(response_time_ms, 2)
    return JsonResponse(response_payload)


@csrf_exempt
@require_POST
def clear_cache(request):
    cache.clear()
    return JsonResponse({"status": "ok", "message": "Cache limpiado correctamente."})
