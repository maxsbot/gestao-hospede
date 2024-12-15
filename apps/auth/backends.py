from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class PhoneAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Formata o número de telefone
        if username:
            phone = ''.join(filter(str.isdigit, username))
            if not phone.startswith('55'):
                phone = '55' + phone
            if not phone.startswith('+'):
                phone = '+' + phone
            username = phone

        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
