import logging
from django.db import DatabaseError

logger = logging.getLogger(__name__)


class CommerceAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        paths = ("/api/ecommerce/", "/api/products/online/", "/api/products/online-categories/", "/api/shop/", "/api/wholesale/online-stock-adjustments/", "/api/auth/login/", "/api/accounts/customers/")
        if request.method in ("POST", "PATCH", "PUT", "DELETE") and request.path.startswith(paths):
            from .models import AuditEvent
            user = getattr(request, "user", None)
            authenticated = user and user.is_authenticated
            try:
                AuditEvent.objects.create(actor=user if authenticated else None,
                    actor_name=user.username if authenticated else "Anonymous",
                    action=request.method if response.status_code < 400 else "DENIED",
                    module=request.path.split("/")[2], summary=f"{request.method} {request.path[:190]} · HTTP {response.status_code}")
            except DatabaseError:
                logger.exception("Could not record ecommerce activity")
        return response
