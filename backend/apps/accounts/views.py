from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from core.permissions import IsAdmin

from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    ShowroomTokenObtainPairSerializer,
    ShowroomUserCreateSerializer,
    UserSerializer,
)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

class ShowroomLoginView(APIView):
    """Authenticate a showroom by username and password, return JWT tokens."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = ShowroomTokenObtainPairSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

class MeView(APIView):
    """Returns the logged-in user's own profile (role, showroom, etc)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_change"

    def post(self, request):
        if request.user.role != User.Role.SHOWROOM_USER:
            raise PermissionDenied("Password change is available from showroom accounts only.")
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password changed. Please sign in again."}, status=status.HTTP_200_OK)

class ShowroomUserListCreateView(generics.ListCreateAPIView):
    """Admin-only: list all showroom users, or create a new one."""

    permission_classes = [IsAdmin]
    queryset = User.objects.filter(role=User.Role.SHOWROOM_USER).select_related("showroom")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ShowroomUserCreateSerializer
        return UserSerializer

class ShowroomUserDetailView(generics.RetrieveUpdateAPIView):
    """Admin-only: view or activate/deactivate a showroom user."""

    permission_classes = [IsAdmin]
    queryset = User.objects.filter(role=User.Role.SHOWROOM_USER)
    serializer_class = UserSerializer
