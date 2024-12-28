import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Lista de usuários de teste
test_users = [
    {
        'username': '+5579998830295',
        'email': 'teste@example.com',
        'password': 'senha123'
    },
    {
        'username': '+557999002792',
        'email': 'teste2@example.com',
        'password': 'anac9465'
    },
    {
        'username': '+5583996617860',
        'email': 'teste3@example.com',
        'password': '1303babi'
    }
]

# Criar usuários de teste
for user_data in test_users:
    username = user_data['username']
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(
            username=username,
            email=user_data['email'],
            password=user_data['password']
        )
        print(f'Usuário criado com sucesso!')
        print(f'Username (telefone): {username}')
        print(f'Senha: {user_data["password"]}')
    else:
        print(f'Usuário {username} já existe!')
