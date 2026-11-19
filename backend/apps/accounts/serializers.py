from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .authentication import check_showroom_access
from .models import User

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Adds role and showroom info directly into the JWT payload so the
    frontend knows immediately (without an extra API call) whether the
    logged-in user is an Admin or which Showroom they belong to.
    """

    allowed_roles = (User.Role.ADMIN, User.Role.ECOMMERCE_STAFF)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        from rest_framework.exceptions import AuthenticationFailed
        if len(attrs.get("password", "")) > 1024:
            raise AuthenticationFailed("Invalid username or password.")
        user = authenticate(request=self.context.get("request"), username=attrs.get("username"), password=attrs.get("password"))
        from rest_framework_simplejwt.settings import api_settings
        if not api_settings.USER_AUTHENTICATION_RULE(user):
            raise AuthenticationFailed(self.error_messages["no_active_account"], "no_active_account")
        if user.role not in self.allowed_roles:
            raise AuthenticationFailed("Use the customer email login or showroom login page for this account.")
        self.user = user
        refresh = self.get_token(user)
        if api_settings.UPDATE_LAST_LOGIN:
            from django.contrib.auth.models import update_last_login
            update_last_login(None, user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        if user.role == User.Role.MODERATOR:
            from rest_framework_simplejwt.utils import get_md5_hash_password
            token["moderator_password"] = get_md5_hash_password(user.password)
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
    password = serializers.CharField(write_only=True, max_length=1024, trim_whitespace=False)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        from django.db import IntegrityError, transaction

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

        check_showroom_access(user)
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
            "role", "showroom", "showroom_name", "is_active", "email_verified",
        ]
        read_only_fields = ["id", "email_verified"]

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


class EmailOtpRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(choices=["signup", "verify"], default="signup")

    def validate_email(self, value):
        from .email_verification import normalize_email
        return normalize_email(value)


class CustomerSignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8, max_length=1024, trim_whitespace=False)
    otp = serializers.RegexField(r"^[0-9]{6}$", write_only=True)

    def validate_email(self, value):
        from .email_verification import normalize_email
        value = normalize_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_phone_number(self, value):
        return "".join(value.split())

    def validate(self, attrs):
        user = User(email=attrs["email"], first_name=attrs["name"])
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return attrs

    def create(self, validated_data):
        from .email_verification import consume_code
        return consume_code(email=validated_data["email"], purpose="signup", code=validated_data["otp"], signup=validated_data)

    def to_representation(self, instance):
        return {"detail": "Email verified and customer account created. Sign in with your email and password."}


class EmailOtpVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.RegexField(r"^[0-9]{6}$", write_only=True)


class CustomerTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, max_length=1024, trim_whitespace=False)

    def validate(self, attrs):
        from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
        users = list(User.objects.filter(role="customer", email__iexact=attrs["email"].strip())[:2])
        user = users[0] if len(users) == 1 else None
        if not user or not user.is_active or not user.check_password(attrs["password"]):
            if not user:
                from django.contrib.auth.hashers import make_password
                make_password(attrs["password"])
            raise AuthenticationFailed("Email or password is incorrect.")
        if not user.email_verified:
            raise PermissionDenied({"detail": "Verify your email before signing in.", "code": "email_verification_required"})
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class VerifiedCustomerRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework.exceptions import AuthenticationFailed
        refresh = RefreshToken(attrs["refresh"])
        user = User.objects.filter(pk=refresh.get("user_id")).first()
        if not user or not user.is_active or user.role == "customer" and not user.email_verified:
            raise AuthenticationFailed("Sign in again. Customer email verification may be required.")
        check_showroom_access(user)
        from .authentication import check_moderator_password
        check_moderator_password(user, refresh)
        data = super().validate(attrs)
        access = AccessToken(data["access"])
        access["role"] = user.role
        access["showroom_id"] = user.showroom_id
        access["showroom_name"] = user.showroom.name if user.showroom_id else None
        access["full_name"] = user.get_full_name() or user.username
        data["access"] = str(access)
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, max_length=1024, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, max_length=1024, trim_whitespace=False, min_length=8)
    confirm_password = serializers.CharField(write_only=True, max_length=1024, trim_whitespace=False)

    def validate(self, attrs):
        from django.contrib.auth.password_validation import validate_password

        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "Current password is incorrect."})
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match."})
        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"new_password": list(error.messages)}) from error
        return attrs

    def save(self, **kwargs):
        from django.db import transaction
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

        user = self.context["request"].user
        with transaction.atomic():
            user.set_password(self.validated_data["new_password"])
            user.save(update_fields=["password"])
            for token in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=token)
        return user
