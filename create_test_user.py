import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Criar um usuário de teste
username = '+5579998830295'  # Número de telefone com código do país
email = 'teste@example.com'

if not User.objects.filter(username=username).exists():
    user = User.objects.create_user(
        username=username,
        email=email,
        password='senha123'  # Senha para testes
    )
    print(f'Usuário criado com sucesso!')
    print(f'Username (telefone): {username}')
    print(f'Senha: senha123')
else:
    print(f'Usuário {username} já existe!')
