import csv
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List
import re
from django.db import transaction
from djmoney.money import Money

from .models import Pessoa, Reserva, Plataforma, Contato


class AirbnbCSVImporter:
    """
    Classe responsável por importar dados do Airbnb via CSV.
    Formato novo do CSV:
    - Código de confirmação
    - Status
    - Nome do hóspede
    - Entrar em contato
    - Nº de adultos
    - Nº de crianças
    - Nº de bebês
    - Data de início
    - Data de término
    - Nº de noites
    - Reservado
    - Anúncio
    - Ganhos
    """
    
    def __init__(self):
        self.plataforma, _ = Plataforma.objects.get_or_create(
            nome='Airbnb',
            defaults={'ativo': True}
        )
        self.erros: List[str] = []
        self.sucessos: List[str] = []
        
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Converte string de data do CSV para objeto datetime."""
        if not date_str:
            return None
            
        try:
            # Formato DD/MM/YYYY
            return datetime.strptime(date_str.strip(), '%d/%m/%Y').date()
        except (ValueError, TypeError):
            try:
                # Formato YYYY-MM-DD
                return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return None
    
    def parse_decimal(self, value_str: str) -> Decimal:
        """Converte string de valor para Decimal."""
        try:
            # Remove o símbolo da moeda e converte para decimal
            clean_value = value_str.replace('R$', '').replace('.', '').replace(',', '.').strip()
            return Decimal(clean_value)
        except (ValueError, TypeError, AttributeError):
            return Decimal('0')
    
    def parse_phone(self, phone_str: str) -> str:
        """Limpa e formata o número de telefone."""
        if not phone_str:
            return ""
        return re.sub(r'[^0-9+]', '', phone_str)

    def map_status(self, status: str) -> str:
        """Mapeia o status do Airbnb para o status do sistema."""
        status_map = {
            'Confirmada': 'CONFIRMADA',
            'Estadia em andamento': 'CHECKIN',
            'Aguardando avaliação do hóspede': 'CHECKOUT',
            'Hóspede anterior': 'FINALIZADA',
            'Cancelada': 'CANCELADA'
        }
        return status_map.get(status, 'PENDENTE')

    def process_reservation(self, row: Dict) -> None:
        """Processa uma linha do CSV."""
        try:
            with transaction.atomic():
                # Verifica campos obrigatórios
                required_fields = [
                    'Código de confirmação', 'Nome do hóspede', 
                    'Data de início', 'Data de término'
                ]
                for field in required_fields:
                    if not row.get(field):
                        self.erros.append(f'Campo obrigatório não encontrado: {field}')
                        return

                # Cria ou obtém a pessoa
                pessoa, created = Pessoa.objects.get_or_create(
                    nome=row['Nome do hóspede'].strip()
                )

                # Adiciona contato se disponível
                if telefone := self.parse_phone(row.get('Entrar em contato', '')):
                    Contato.objects.get_or_create(
                        pessoa=pessoa,
                        tipo='WHATSAPP',
                        valor=telefone,
                        defaults={'principal': True}
                    )
                
                # Processa as datas
                data_reserva = self.parse_date(row['Reservado'])
                data_entrada = self.parse_date(row['Data de início'])
                data_saida = self.parse_date(row['Data de término'])
                
                if not all([data_reserva, data_entrada, data_saida]):
                    self.erros.append(f'Data inválida para reserva {row["Código de confirmação"]}')
                    return

                # Processa valores financeiros
                valor_bruto = Money(self.parse_decimal(row['Ganhos']), 'BRL')
                
                # Cria ou atualiza a reserva
                reserva, created = Reserva.objects.update_or_create(
                    codigo_confirmacao=row['Código de confirmação'],
                    defaults={
                        'hospede_principal': pessoa,
                        'plataforma': self.plataforma,
                        'data_reserva': data_reserva,
                        'data_entrada': data_entrada,
                        'data_saida': data_saida,
                        'noites': int(row.get('Nº de noites', 0) or 0),
                        'num_adultos': int(row.get('Nº de adultos', 1) or 1),
                        'num_criancas': int(row.get('Nº de crianças', 0) or 0) + int(row.get('Nº de bebês', 0) or 0),
                        'valor_bruto': valor_bruto,
                        'ganhos_brutos': valor_bruto,
                        'status': self.map_status(row['Status'])
                    }
                )

                action = 'criada' if created else 'atualizada'
                self.sucessos.append(f'Reserva {row["Código de confirmação"]} {action} com sucesso')
                    
        except Exception as e:
            self.erros.append(f'Erro ao processar reserva: {str(e)}')

    def import_csv(self, file_path: str) -> Dict:
        """Importa CSV de reservas."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    self.process_reservation(row)
        except Exception as e:
            self.erros.append(str(e))
        
        return self.get_result()

    def get_result(self) -> Dict:
        """Retorna o resultado da importação."""
        return {
            'success': len(self.erros) == 0,
            'imported': len(self.sucessos),
            'errors': self.erros
        }
