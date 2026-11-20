import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.cache import cache
from rest_framework.exceptions import APIException, ValidationError


class SteadfastUnavailable(APIException):
    status_code = 502
    default_detail = "Steadfast's calculator is unavailable. Retry or enter the merchant charge."


def quote_delivery(origin, destination, weight, delivery):
    # Regular parcels and standard service match this showroom's shipments.
    params = urlencode({
        "from": origin, "to": destination, "weight": weight, "category": 1,
        "service": 1, "delivery": int(delivery == "point"),
    })
    key = f"moderator:steadfast:{params}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    request = Request(f"https://steadfast.com.bd/pricing/quote?{params}", headers={
        "Accept": "application/json", "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "MahirSherwaniShowroom/1.0",
    })
    try:
        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read(16 * 1024))
        if data.get("available") is False:
            raise ValidationError({"destination": "Steadfast does not quote this delivery route."})
        charge = Decimal(str(data["charge"]))
        if data.get("available") is not True or not charge.is_finite() or not 0 <= charge <= Decimal("9999999999.99"):
            raise ValueError("Invalid Steadfast quote")
        amount = str(charge.quantize(Decimal("0.01")))
    except (OSError, ValueError, KeyError, AttributeError, InvalidOperation) as error:
        raise SteadfastUnavailable() from error

    cache.set(key, amount, 300)
    return amount
