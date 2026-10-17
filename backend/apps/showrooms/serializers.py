from rest_framework import serializers

from .models import Showroom


class ShowroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Showroom
        fields = ["id", "name", "address", "phone", "username", "password", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        """Hash password when creating a showroom."""
        password = validated_data.pop("password", None)
        showroom = Showroom(**validated_data)
        if password:
            showroom.set_password(password)
        showroom.save()
        return showroom

    def update(self, instance, validated_data):
        """Hash password when updating a showroom."""
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
