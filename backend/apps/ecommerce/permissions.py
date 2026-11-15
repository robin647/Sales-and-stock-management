from rest_framework.permissions import BasePermission, SAFE_METHODS


ROLE_MODULES = {
    "manager": {"dashboard", "brands", "vendors", "suppliers", "purchases", "payments", "returns", "shipping", "reviews", "support", "content", "campaigns", "finance", "seo", "locales", "products", "inventory", "orders", "customers", "reports", "settings"},
    "catalog": {"dashboard", "brands", "products", "inventory", "content", "seo", "reviews", "reports"},
    "fulfillment": {"dashboard", "orders", "inventory", "shipping", "returns", "reports"},
    "support": {"dashboard", "orders", "customers", "support", "reviews", "returns"},
    "finance": {"dashboard", "orders", "payments", "finance", "purchases", "suppliers", "reports"},
    "viewer": {"dashboard", "products", "inventory", "orders", "reports"},
}

ROLE_WRITE_MODULES = {
    "manager": ROLE_MODULES["manager"],
    "catalog": {"brands", "products", "inventory", "content", "seo", "reviews"},
    "fulfillment": {"orders", "inventory", "shipping", "returns"},
    "support": {"support", "reviews", "returns"},
    "finance": {"payments", "finance", "purchases", "suppliers"},
    "viewer": set(),
}


def commerce_allowed(user, module, write=False):
    if not user or not user.is_authenticated:
        return False
    if user.role == "admin":
        return True
    if user.role != "ecommerce_staff":
        return False
    membership = getattr(user, "commerce_membership", None)
    return bool(membership and membership.is_active
                and module in ROLE_MODULES.get(membership.access_role, set())
                and (not write or module in ROLE_WRITE_MODULES.get(membership.access_role, set())))


class CommercePermission(BasePermission):
    def has_permission(self, request, view):
        return commerce_allowed(request.user, getattr(view, "commerce_module", "dashboard"), request.method not in SAFE_METHODS)
