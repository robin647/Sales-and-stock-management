from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from .models import Showroom


class ShowroomSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, required=False, allow_blank=False, max_length=150)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, min_length=8)
    login_username = serializers.SerializerMethodField()
    has_login = serializers.SerializerMethodField()

    class Meta:
        model = Showroom
        fields = [
            "id", "name", "address", "phone", "username", "password",
            "login_username", "has_login", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "login_username", "has_login", "created_at", "updated_at"]

    def _login_user(self, showroom):
        return showroom.users.filter(role=User.Role.SHOWROOM_USER).order_by("id").first()

    def get_login_username(self, showroom):
        user = self._login_user(showroom)
        return user.username if user else None

    def get_has_login(self, showroom):
        return self._login_user(showroom) is not None

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")
        if bool(username) != bool(password):
            raise serializers.ValidationError({
                "credentials": "Provide both a username and password when setting showroom login credentials."
            })
        if username and password:
            user = (self._login_user(self.instance) if self.instance else None) or User(username=username)
            user.username = username
            try:
                validate_password(password, user=user)
            except DjangoValidationError as error:
                raise serializers.ValidationError({"password": list(error.messages)}) from error
        if username:
            duplicates = User.objects.filter(username=username)
            if self.instance:
                current = self._login_user(self.instance)
                if current:
                    duplicates = duplicates.exclude(pk=current.pk)
            if duplicates.exists():
                raise serializers.ValidationError({"username": "This username is already in use."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        username = validated_data.pop("username", None)
        password = validated_data.pop("password", None)
        showroom = Showroom(**validated_data)
        showroom.username = username or ""
        showroom.password = make_password(password) if password else make_password(None)
        showroom.save()
        if username and password:
            user = User(
                username=username,
                role=User.Role.SHOWROOM_USER,
                showroom=showroom,
                is_active=showroom.is_active,
            )
            user.set_password(password)
            user.full_clean()
            user.save()
        return showroom

    @transaction.atomic
    def update(self, instance, validated_data):
        username = validated_data.pop("username", None)
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if username and password:
            instance.username = username
            instance.set_password(password)
            user = self._login_user(instance)
            if user:
                user.username = username
                user.set_password(password)
                user.is_active = instance.is_active
                user.full_clean()
                user.save(update_fields=["username", "password", "is_active"])
            else:
                user = User(
                    username=username,
                    role=User.Role.SHOWROOM_USER,
                    showroom=instance,
                    is_active=instance.is_active,
                )
                user.set_password(password)
                user.full_clean()
                user.save()
        else:
            instance.users.filter(role=User.Role.SHOWROOM_USER).update(is_active=instance.is_active)
        instance.save()
        return instance
