from django.db import connection
from django.http import JsonResponse


def healthcheck(request):
    """Simple liveness/readiness endpoint used by container health checks."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return JsonResponse(
            {
                "status": "unhealthy",
                "database": "down",
                "error": str(exc),
            },
            status=503,
        )

    return JsonResponse({"status": "ok", "database": "up"}, status=200)