from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

User = get_user_model()

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Telefone',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite seu telefone'})
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Digite sua senha'})
    )

    def clean_username(self):
        phone = self.cleaned_data.get('username')
        if phone:
            # Remove qualquer formatação e adiciona o código do país se necessário
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('55'):
                phone = '55' + phone
            if not phone.startswith('+'):
                phone = '+' + phone
        return phone

class PhoneLoginForm(forms.Form):
    """
    Form for handling phone-based authentication.
    """
    COUNTRY_CHOICES = [
        ('55', 'Brasil (+55)'),
        ('351', 'Portugal (+351)'),
        ('1', 'Estados Unidos (+1)'),
    ]

    country_code = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        initial='55',
        label='País/Região'
    )

    phone_regex = RegexValidator(
        regex=r'^\d{8,15}$',
        message='Digite um número de telefone válido (8-15 dígitos)'
    )

    phone = forms.CharField(
        validators=[phone_regex],
        max_length=15,
        label='Número de telefone',
        widget=forms.TextInput(attrs={
            'placeholder': 'Digite seu número de telefone',
            'class': 'form-control'
        })
    )

    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Digite sua senha'})
    )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove qualquer formatação e adiciona o código do país se necessário
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('55'):
                phone = '55' + phone
            if not phone.startswith('+'):
                phone = '+' + phone
            
            # Verifica se o usuário existe
            try:
                User.objects.get(username=phone)
            except User.DoesNotExist:
                raise ValidationError('Usuário não encontrado com este número de telefone.')
        return phone

    def clean(self) -> dict:
        """
        Custom validation to format the phone number with country code.
        """
        cleaned_data = super().clean()
        country_code = cleaned_data.get('country_code')
        phone = cleaned_data.get('phone')

        if country_code and phone:
            cleaned_data['full_phone'] = f"+{country_code}{phone}"

        return cleaned_data
