from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User


def check_showroom_access(user):
    if user.role == User.Role.SHOWROOM_USER and (
        not user.showroom_id or not user.showroom.is_active
    ):
        raise AuthenticationFailed("This account needs an active showroom assignment.")


class ShowroomAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        check_showroom_access(user)
        return user
