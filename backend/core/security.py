"""Early, bounded request checks. Network DDoS protection belongs at the edge."""
import hashlib
import ipaddress
import logging
import time

from django.conf import settings
from django.core.cache import caches
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def client_ip(request):
    # Trust forwarded addresses only when the deployment explicitly specifies
    # its trusted proxy count. Never key on the whole caller-controlled header.
    hops = settings.REST_FRAMEWORK.get("NUM_PROXIES", 0)
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
    address = request.META.get("REMOTE_ADDR", "")
    if hops and len(forwarded) >= hops:
        address = forwarded[-hops].strip()
    try:
        return str(ipaddress.ip_address(address))
    except ValueError:
        return "unknown"


class RequestGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        protected = request.path.startswith(("/api/", "/admin/"))
        if not protected or request.path == "/api/health/":
            return self.get_response(request)
        if len(request.META.get("QUERY_STRING", "")) > 8192:
            return JsonResponse({"detail": "Query string is too long."}, status=414)
        try:
            length = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            return JsonResponse({"detail": "Invalid content length."}, status=400)
        if length < 0:
            return JsonResponse({"detail": "Invalid content length."}, status=400)
        if length > settings.REQUEST_MAX_BYTES:
            return JsonResponse({"detail": "Request body is too large."}, status=413)
        if settings.REQUEST_GUARD_ENABLED and request.method != "OPTIONS":
            identity = hashlib.sha256(client_ip(request).encode()).hexdigest()
            policies = [("all", settings.REQUESTS_PER_MINUTE)]
            if request.method == "POST" and (request.path.startswith("/api/auth/") or request.path == "/admin/login/"):
                policies.append(("auth", settings.AUTH_REQUESTS_PER_MINUTE))
            window = int(time.time()) // 60
            cache = caches["security"]
            try:
                for scope, limit in policies:
                    key = f"guard:{scope}:{identity}:{window}"
                    if cache.add(key, 1, timeout=120):
                        count = 1
                    else:
                        try:
                            count = cache.incr(key)
                        except ValueError:  # Entry expired/evicted between add and incr.
                            if cache.add(key, 1, timeout=120):
                                count = 1
                            else:
                                count = cache.incr(key)
                    if count > limit:
                        response = JsonResponse({"detail": "Too many requests. Please try again shortly."}, status=429)
                        response["Retry-After"] = str(60 - int(time.time()) % 60)
                        response["Cache-Control"] = "no-store"
                        return response
            except Exception:
                logger.error("Security rate-limit cache unavailable")
                return JsonResponse({"detail": "Service temporarily unavailable."}, status=503)
        return self.get_response(request)
