from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import User

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Adds role and showroom info directly into the JWT payload so the
    frontend knows immediately (without an extra API call) whether the
    logged-in user is an Admin or which Showroom they belong to.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["showroom_id"] = user.showroom_id
        token["showroom_name"] = user.showroom.name if user.showroom_id else None
        token["full_name"] = user.get_full_name() or user.username
        return token

class ShowroomTokenObtainPairSerializer(serializers.Serializer):
    """
    Authenticates a showroom by username and password.
    Returns a JWT token with showroom info in the payload.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        from django.db import IntegrityError, transaction
        from rest_framework_simplejwt.tokens import RefreshToken

        username = attrs.get("username")
        password = attrs.get("password")
        from apps.showrooms.models import Showroom
        user = User.objects.filter(username=username).first()
        if user:
            if user.role != User.Role.SHOWROOM_USER or not user.is_active:
                raise serializers.ValidationError({"detail": "Invalid username or password."})
            authenticated = authenticate(
                request=self.context.get("request"), username=username, password=password,
            )
            if not authenticated or authenticated.pk != user.pk:
                raise serializers.ValidationError({"detail": "Invalid username or password."})
            user = authenticated
        else:

            showroom = next((
                row for row in Showroom.objects.filter(username=username, is_active=True).order_by("id")
                if row.check_password(password)
            ), None)
            if showroom is None:
                raise serializers.ValidationError({"detail": "Invalid username or password."})
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username,
                        password=password,
                        role=User.Role.SHOWROOM_USER,
                        showroom=showroom,
                        is_active=showroom.is_active,
                    )
            except IntegrityError:
                user = User.objects.filter(username=username).first()
                if not user or user.role != User.Role.SHOWROOM_USER or not user.is_active:
                    raise serializers.ValidationError({"detail": "Invalid username or password."})
                authenticated = authenticate(
                    request=self.context.get("request"), username=username, password=password,
                )
                if not authenticated or authenticated.pk != user.pk:
                    raise serializers.ValidationError({"detail": "Invalid username or password."})
                user = authenticated

        refresh = CustomTokenObtainPairSerializer.get_token(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

class UserSerializer(serializers.ModelSerializer):
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email",
            "role", "showroom", "showroom_name", "is_active",
        ]
        read_only_fields = ["id"]

class ShowroomUserCreateSerializer(serializers.ModelSerializer):
    """Used by Admin to create a new showroom user account."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "password", "showroom", "is_active"]

    def validate(self, attrs):
        if not attrs.get("showroom"):
            raise serializers.ValidationError({"showroom": "Showroom is required for a showroom user."})
        user = User(
            username=attrs["username"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
            email=attrs.get("email", ""),
            showroom=attrs["showroom"],
        )
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(role=User.Role.SHOWROOM_USER, **validated_data)
        user.set_password(password)
        user.full_clean()
        user.save()
        return user
