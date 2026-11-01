from django.contrib import admin

from .models import SwingLot, SwingOperator, SwingPayment, SwingReject


@admin.register(SwingOperator)
class SwingOperatorAdmin(admin.ModelAdmin):
    list_display = ("name", "nid_number", "is_active", "created_at")
    search_fields = ("name", "nid_number")
    list_filter = ("is_active",)


@admin.register(SwingLot)
class SwingLotAdmin(admin.ModelAdmin):
    list_display = ("lot_number", "operator", "lot_date", "quantity", "rate", "is_active")
    search_fields = ("lot_number", "operator__name", "fabric_specification")
    list_filter = ("is_active", "lot_date")


@admin.register(SwingPayment)
class SwingPaymentAdmin(admin.ModelAdmin):
    list_display = ("operator", "payment_date", "amount", "is_active")
    list_filter = ("is_active", "payment_date")


@admin.register(SwingReject)
class SwingRejectAdmin(admin.ModelAdmin):
    list_display = ("lot", "reject_date", "quantity", "is_active")
    list_filter = ("is_active", "reject_date")
