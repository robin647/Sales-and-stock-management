from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.utils import get_md5_hash_password

from .models import User


def check_showroom_access(user):
    if user.role == User.Role.SHOWROOM_USER and (
        not user.showroom_id or not user.showroom.is_active
    ):
        raise AuthenticationFailed("This account needs an active showroom assignment.")


def check_moderator_password(user, token):
    if user.role == User.Role.MODERATOR and token.get("moderator_password") != get_md5_hash_password(user.password):
        raise AuthenticationFailed("Sign in again.")


class ShowroomAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        check_showroom_access(user)
        check_moderator_password(user, validated_token)
        return user
