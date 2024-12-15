from typing import Optional
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.http import HttpRequest

User = get_user_model()

class PhoneAuthenticationBackend(BaseBackend):
    """
    Custom authentication backend for phone-based authentication.
    """

    def authenticate(
        self, 
        request: HttpRequest, 
        phone: str = None, 
        **kwargs
    ) -> Optional[User]:
        """
        Authenticate a user based on phone number.

        Args:
            request: The HTTP request
            phone: The full phone number with country code
            **kwargs: Additional keyword arguments

        Returns:
            User object if authentication successful, None otherwise
        """
        if not phone:
            return None

        try:
            user = User.objects.get(username=phone)
            return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Retrieve user by ID.

        Args:
            user_id: The user's ID

        Returns:
            User object if found, None otherwise
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
