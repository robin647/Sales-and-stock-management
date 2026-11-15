from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from core.permissions import IsAdmin
from .engine import respond


class AssistantRateThrottle(UserRateThrottle):
    scope = "assistant"


class AssistantChatSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000, trim_whitespace=True)
    context = serializers.CharField(max_length=8000, required=False, allow_blank=True)


class AssistantChatView(APIView):
    permission_classes = [IsAdmin]
    throttle_classes = [AssistantRateThrottle]

    def get(self, request):
        from apps.employees.models import Employee
        from apps.wholesale.models import WholesaleParty
        from apps.swing.models import SwingLot
        examples = []
        employee = Employee.objects.filter(is_active=True).values_list("name", flat=True).first()
        party = WholesaleParty.objects.filter(is_active=True).values_list("name", flat=True).first()
        lot = SwingLot.objects.filter(is_active=True).exclude(lot_number="").values_list("lot_number", flat=True).first()
        if employee: examples.append(f"{employee} এর এই মাসে বেতন ও অনুপস্থিতি কত?")
        if party: examples.append(f"{party} পার্টির শেষ পেমেন্ট কত, আর বাকি কত?")
        if lot: examples.append(f"লট {lot} কে সেলাই করেছে?")
        examples.append("মূল স্টক মোট কত আছে?")
        return Response({"mode": "local", "examples": examples})

    def post(self, request):
        serializer = AssistantChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(respond(request.user, serializer.validated_data["question"], serializer.validated_data.get("context", "")))
