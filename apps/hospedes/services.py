import csv
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List

from django.db import transaction
from djmoney.money import Money

from .models import Pessoa, Reserva, Plataforma


class AirbnbCSVImporter:
    """
    Classe responsável por importar dados do Airbnb via CSV.
    Pode ser usada tanto via comando quanto via interface web.
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
        try:
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except (ValueError, TypeError):
            return None
    
    def parse_decimal(self, value_str: str) -> Decimal:
        """Converte string de valor para Decimal."""
        try:
            return Decimal(value_str.replace(',', '.'))
        except (ValueError, TypeError, AttributeError):
            return Decimal('0')
    
    def process_pending_reservation(self, row: Dict) -> None:
        """Processa uma linha do CSV de reservas pendentes."""
        try:
            with transaction.atomic():
                # Cria ou obtém a pessoa
                pessoa, _ = Pessoa.objects.get_or_create(
                    nome=row['Hóspede']
                )
                
                # Verifica se a reserva já existe
                codigo = row['Código de Confirmação']
                if Reserva.objects.filter(codigo_confirmacao=codigo).exists():
                    self.erros.append(f'Reserva {codigo} já existe no sistema')
                    return
                
                # Cria a reserva
                Reserva.objects.create(
                    hospede_principal=pessoa,
                    plataforma=self.plataforma,
                    codigo_confirmacao=codigo,
                    data_reserva=self.parse_date(row['Data da reserva']),
                    data_entrada=self.parse_date(row['Data de início']),
                    data_saida=self.parse_date(row['Data de término']),
                    noites=int(row['Noites']),
                    valor_bruto=Money(self.parse_decimal(row['Valor']), 'BRL'),
                    taxa_servico=Money(self.parse_decimal(row['Taxa de serviço']), 'BRL'),
                    taxa_limpeza=Money(self.parse_decimal(row['Taxa de limpeza']), 'BRL'),
                    ganhos_brutos=Money(self.parse_decimal(row['Ganhos brutos']), 'BRL'),
                    impostos=Money(self.parse_decimal(row['Impostos de ocupação']), 'BRL'),
                    status='PENDENTE'
                )
                self.sucessos.append(f'Reserva {codigo} criada com sucesso')
                
        except Exception as e:
            self.erros.append(f'Erro ao processar reserva: {str(e)}')
    
    def process_complete_reservation(self, row: Dict) -> None:
        """Processa uma linha do CSV completo."""
        try:
            # Ignora linhas de Payout
            if row['Tipo'] != 'Reserva':
                return
                
            with transaction.atomic():
                codigo = row['Código de Confirmação']
                reserva = Reserva.objects.filter(codigo_confirmacao=codigo).first()
                
                if not reserva:
                    # Se não existe, cria nova reserva
                    pessoa, _ = Pessoa.objects.get_or_create(
                        nome=row['Hóspede']
                    )
                    
                    reserva = Reserva.objects.create(
                        hospede_principal=pessoa,
                        plataforma=self.plataforma,
                        codigo_confirmacao=codigo,
                        data_reserva=self.parse_date(row['Data da reserva']),
                        data_entrada=self.parse_date(row['Data de início']),
                        data_saida=self.parse_date(row['Data de término']),
                        noites=int(row['Noites']),
                        valor_bruto=Money(self.parse_decimal(row['Valor']), 'BRL'),
                        taxa_servico=Money(self.parse_decimal(row['Taxa de serviço']), 'BRL'),
                        taxa_limpeza=Money(self.parse_decimal(row['Taxa de limpeza']), 'BRL'),
                        ganhos_brutos=Money(self.parse_decimal(row['Ganhos brutos']), 'BRL'),
                        impostos=Money(self.parse_decimal(row['Impostos de ocupação']), 'BRL'),
                        status='CONFIRMADA'
                    )
                    self.sucessos.append(f'Reserva {codigo} criada com sucesso')
                else:
                    # Atualiza a reserva existente
                    reserva.valor_bruto = Money(self.parse_decimal(row['Valor']), 'BRL')
                    reserva.taxa_servico = Money(self.parse_decimal(row['Taxa de serviço']), 'BRL')
                    reserva.taxa_limpeza = Money(self.parse_decimal(row['Taxa de limpeza']), 'BRL')
                    reserva.ganhos_brutos = Money(self.parse_decimal(row['Ganhos brutos']), 'BRL')
                    reserva.impostos = Money(self.parse_decimal(row['Impostos de ocupação']), 'BRL')
                    reserva.status = 'CONFIRMADA'
                    reserva.save()
                    self.sucessos.append(f'Reserva {codigo} atualizada com sucesso')
                    
        except Exception as e:
            self.erros.append(f'Erro ao processar reserva: {str(e)}')
    
    def import_pending_csv(self, file_path: str) -> Dict:
        """Importa CSV de reservas pendentes."""
        try:
            with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    self.process_pending_reservation(row)
        except Exception as e:
            self.erros.append(f'Erro ao ler arquivo: {str(e)}')
        
        return {
            'sucessos': self.sucessos,
            'erros': self.erros
        }
    
    def import_complete_csv(self, file_path: str) -> Dict:
        """Importa CSV completo."""
        try:
            with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    self.process_complete_reservation(row)
        except Exception as e:
            self.erros.append(f'Erro ao ler arquivo: {str(e)}')
        
        return {
            'sucessos': self.sucessos,
            'erros': self.erros
        }
