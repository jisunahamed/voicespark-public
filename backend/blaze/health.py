"""
Health check endpoint for Docker container monitoring.
Returns 200 OK when the Django application is running.
"""
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "ok"})
