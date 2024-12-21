from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Cria um usuário de teste para o sistema'

    def handle(self, *args, **kwargs):
        username = '+5579998830295'  # Número de telefone com código do país
        email = 'teste@example.com'
        password = 'senha123'  # Senha para testes

        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS('Usuário criado com sucesso!')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Username (telefone): {username}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Senha: {password}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Usuário {username} já existe!')
            )
