from django.http import JsonResponse

def api_status(request):
    """Return a minimal public status response without exposing internals."""
    return JsonResponse(
        {
            "status": "success",
            "message": "Sales and Stock Management API is running",
        }
    )
