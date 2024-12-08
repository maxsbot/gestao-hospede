from django.core.management.base import BaseCommand, CommandError
from apps.hospedes.services import AirbnbCSVImporter
import os


class Command(BaseCommand):
    help = 'Importa dados de reservas do Airbnb a partir de um arquivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Caminho para o arquivo CSV')
        parser.add_argument(
            '--pending',
            action='store_true',
            help='Define se o arquivo contém reservas pendentes',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        is_pending = options['pending']

        if not os.path.exists(csv_file):
            raise CommandError(f'Arquivo não encontrado: {csv_file}')

        try:
            importer = AirbnbCSVImporter(is_pending=is_pending)
            result = importer.import_csv(csv_file)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Importação concluída com sucesso! {result["imported"]} registros importados.'
                    )
                )
            
            if result['errors']:
                self.stdout.write(
                    self.style.WARNING(
                        'Alguns registros não puderam ser importados:'
                    )
                )
                for error in result['errors']:
                    self.stdout.write(self.style.WARNING(f'- {error}'))
                    
        except Exception as e:
            raise CommandError(f'Erro durante a importação: {str(e)}')
