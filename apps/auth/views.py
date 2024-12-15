from typing import Any
from django.contrib import messages
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from .forms import PhoneLoginForm, CustomAuthenticationForm
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomLoginView(LoginView):
    """
    View for handling user authentication via phone number.
    """
    template_name = 'auth/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # Se o usuário é staff, mantém o next parameter para permitir acesso ao admin
        if self.request.user.is_staff and self.request.GET.get('next'):
            return self.request.GET.get('next')
        return reverse_lazy('hospedes:dashboard')

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('auth:login')
    http_method_names = ['get', 'post']  # Permite tanto GET quanto POST

@method_decorator(csrf_protect, name='dispatch')
@method_decorator(sensitive_post_parameters('phone'), name='post')
class PhoneLoginView(FormView):
    """
    View for handling user authentication via phone number.
    """
    template_name = 'auth/login.html'
    form_class = PhoneLoginForm
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form: PhoneLoginForm) -> HttpResponse:
        """
        Handle valid form submission.

        Args:
            form: Validated form instance

        Returns:
            HttpResponse: Redirect to success URL or back to login form
        """
        try:
            phone = form.cleaned_data['full_phone']
            user = self.authenticate_user(phone)

            if user is not None:
                login(self.request, user)
                logger.info(f"User {user.username} logged in successfully")
                return super().form_valid(form)
            else:
                logger.warning(f"Failed login attempt for phone number: {phone}")
                messages.error(
                    self.request,
                    'Número de telefone não encontrado.'
                )
                return self.form_invalid(form)

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            messages.error(
                self.request,
                'Ocorreu um erro durante o login. Tente novamente.'
            )
            return self.form_invalid(form)

    def authenticate_user(self, phone: str) -> Any:
        """
        Authenticate user with phone number.

        Args:
            phone: Full phone number with country code

        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            # Procura o usuário pelo número de telefone (username)
            user = User.objects.get(username=phone)
            return user
        except User.DoesNotExist:
            return None
