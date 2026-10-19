from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import DailyBalance, DailyStock, StockAdjustment
from apps.showrooms.models import Showroom

from .helpers import resolve_showroom_scope


class DashboardView(APIView):
    """
    Admin: totals across all showrooms for today + showroom-wise breakdown.
    Showroom user: today's own numbers only.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = request.query_params.get("date", timezone.localdate().isoformat())
        showrooms_qs, showroom_id = resolve_showroom_scope(request)

        balances = DailyBalance.objects.filter(date=today, showroom__in=showrooms_qs)
        if showroom_id:
            balances = balances.filter(showroom_id=showroom_id)

        totals = balances.aggregate(
            total_sale=Sum("total_sale"),
            cash_sale=Sum("cash_sale"),
            card_sale=Sum("card_sale"),
            expense=Sum("expense"),
            salary=Sum("salary"),
            deposit=Sum("deposit"),
            closing_balance=Sum("closing_balance"),
        )
        totals = {k: (v or 0) for k, v in totals.items()}

        stock_totals = DailyStock.objects.filter(date=today, showroom__in=showrooms_qs).aggregate(
            received=Sum("received_qty"), sold=Sum("sold_qty"), returned=Sum("return_qty"),
        )
        adjustment_total = StockAdjustment.objects.filter(
            location="showroom", showroom__in=showrooms_qs, created_at__date=today,
        ).aggregate(value=Sum("difference"))["value"] or 0

        data = {
            "date": today,
            "total_showrooms": showrooms_qs.count(),
            **totals,
            "stock_summary": {
                "received": stock_totals["received"] or 0,
                "sold": stock_totals["sold"] or 0,
                "returned": stock_totals["returned"] or 0,
                "adjustment": adjustment_total,
            },
            "showroom_wise": list(
                balances.values("showroom__id", "showroom__name").annotate(
                    total_sale=Sum("total_sale"),
                    cash_sale=Sum("cash_sale"),
                    card_sale=Sum("card_sale"),
                )
            ),
        }

        if request.user.role != "admin":
            data.pop("showroom_wise", None)
            data.pop("total_showrooms", None)
        else:
            from apps.wholesale.models import WholesaleParty
            from apps.wholesale.services import all_party_summary

            _, wholesale_totals = all_party_summary({})
            data["wholesale_summary"] = {
                "total_parties": WholesaleParty.objects.count(),
                "active_parties": WholesaleParty.objects.filter(is_active=True).count(),
                **wholesale_totals,
            }

        return Response(data)


class DailyStatementView(APIView):
    """Returns the full daily statement (stock table + balance row) for one showroom + date."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        target_date = request.query_params.get("date", timezone.localdate().isoformat())
        showrooms_qs, showroom_id = resolve_showroom_scope(request)

        if not showroom_id:
            return Response({"detail": "showroom parameter is required."}, status=400)

        stock_qs = DailyStock.objects.filter(showroom_id=showroom_id, date=target_date).select_related("product")
        category_id = request.query_params.get("category")
        product_id = request.query_params.get("product")
        if category_id:
            stock_qs = stock_qs.filter(product__category_id=category_id)
        if product_id:
            stock_qs = stock_qs.filter(product_id=product_id)

        adjustments_qs = StockAdjustment.objects.filter(
            location="showroom", showroom_id=showroom_id, created_at__date=target_date,
        ).select_related("product")
        if category_id:
            adjustments_qs = adjustments_qs.filter(product__category_id=category_id)
        if product_id:
            adjustments_qs = adjustments_qs.filter(product_id=product_id)
        adjustment_by_product = {}
        for adjustment in adjustments_qs:
            row = adjustment_by_product.setdefault(adjustment.product_id, {
                "product": adjustment.product.name, "opening": 0, "received": 0,
                "sold": 0, "return": 0, "adjustment": 0, "closing": 0,
            })
            row["adjustment"] += adjustment.difference
            row["closing"] = adjustment.new_quantity

        stock_rows = []
        for stock in stock_qs:
            adjustment = adjustment_by_product.pop(stock.product_id, None)
            adjustment_amount = adjustment["adjustment"] if adjustment else 0
            stock_rows.append({
                "product": stock.product.name, "opening": stock.opening_qty,
                "received": stock.received_qty, "sold": stock.sold_qty,
                "return": stock.return_qty, "adjustment": adjustment_amount,
                "closing": stock.closing_qty + adjustment_amount,
            })
        for row in adjustment_by_product.values():
            row["closing"] = row["adjustment"]

        balance = DailyBalance.objects.filter(showroom_id=showroom_id, date=target_date).first()

        return Response({
            "date": target_date,
            "showroom": Showroom.objects.filter(id=showroom_id).values("id", "name").first(),
            "stock": stock_rows + list(adjustment_by_product.values()),
            "balance": {
                "opening_balance": balance.opening_balance,
                "cash_sale": balance.cash_sale,
                "card_sale": balance.card_sale,
                "total_sale": balance.total_sale,
                "expense": balance.expense,
                "salary": balance.salary,
                "deposit": balance.deposit,
                "closing_balance": balance.closing_balance,
            } if balance else None,
        })


class MonthlyReportView(APIView):
    """Aggregated monthly totals for a showroom (or all showrooms for admin)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year = int(request.query_params.get("year", timezone.localdate().year))
        month = int(request.query_params.get("month", timezone.localdate().month))
        showrooms_qs, showroom_id = resolve_showroom_scope(request)

        balances = DailyBalance.objects.filter(
            date__year=year, date__month=month, showroom__in=showrooms_qs
        )
        if showroom_id:
            balances = balances.filter(showroom_id=showroom_id)

        summary = balances.values("showroom__id", "showroom__name").annotate(
            total_sale=Sum("total_sale"),
            cash_sale=Sum("cash_sale"),
            card_sale=Sum("card_sale"),
            expense=Sum("expense"),
            salary=Sum("salary"),
            deposit=Sum("deposit"),
        )

        stock_qs = DailyStock.objects.filter(
            date__year=year, date__month=month, showroom__in=showrooms_qs
        )
        if showroom_id:
            stock_qs = stock_qs.filter(showroom_id=showroom_id)
        product_id = request.query_params.get("product")
        category_id = request.query_params.get("category")
        if product_id:
            stock_qs = stock_qs.filter(product_id=product_id)
        if category_id:
            stock_qs = stock_qs.filter(product__category_id=category_id)

        stock_summary = stock_qs.values("product__id", "product__name").annotate(
            received=Sum("received_qty"),
            sold=Sum("sold_qty"),
            returned=Sum("return_qty"),
        )
        for row in stock_summary:
            row["adjustment"] = 0

        adjustment_qs = StockAdjustment.objects.filter(
            location="showroom", showroom__in=showrooms_qs,
            created_at__date__year=year, created_at__date__month=month,
        )
        if showroom_id:
            adjustment_qs = adjustment_qs.filter(showroom_id=showroom_id)
        if product_id:
            adjustment_qs = adjustment_qs.filter(product_id=product_id)
        if category_id:
            adjustment_qs = adjustment_qs.filter(product__category_id=category_id)
        adjustment_totals = adjustment_qs.values("product_id", "product__name").annotate(adjustment=Sum("difference"))
        stock_rows = {row["product__id"]: row for row in stock_summary}
        for row in adjustment_totals:
            existing = stock_rows.get(row["product_id"])
            if existing:
                existing["adjustment"] = row["adjustment"] or 0
            else:
                stock_rows[row["product_id"]] = {
                    "product__id": row["product_id"], "product__name": row["product__name"],
                    "received": 0, "sold": 0, "returned": 0, "adjustment": row["adjustment"] or 0,
                }

        return Response({
            "year": year,
            "month": month,
            "balance_summary": list(summary),
            "stock_summary": list(stock_rows.values()),
        })
