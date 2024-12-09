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
    
    def __init__(self, is_pending: bool = False):
        self.plataforma, _ = Plataforma.objects.get_or_create(
            nome='Airbnb',
            defaults={'ativo': True}
        )
        self.erros: List[str] = []
        self.sucessos: List[str] = []
        self.is_pending = is_pending
        self._codigo_counter = 1
        
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Converte string de data do CSV para objeto datetime."""
        if not date_str:
            return None
            
        try:
            # Tenta primeiro o formato MM/DD/YYYY
            return datetime.strptime(date_str.strip(), '%m/%d/%Y').date()
        except (ValueError, TypeError):
            try:
                # Se falhar, tenta o formato DD/MM/YYYY
                return datetime.strptime(date_str.strip(), '%d/%m/%Y').date()
            except (ValueError, TypeError):
                return None
    
    def parse_decimal(self, value_str: str) -> Decimal:
        """Converte string de valor para Decimal."""
        try:
            return Decimal(value_str.replace(',', '.'))
        except (ValueError, TypeError, AttributeError):
            return Decimal('0')
    
    def generate_confirmation_code(self) -> str:
        """Gera um código de confirmação único."""
        while True:
            codigo = f'AUTO{str(self._codigo_counter).zfill(6)}'
            self._codigo_counter += 1
            if not Reserva.objects.filter(codigo_confirmacao=codigo).exists():
                return codigo

    def determine_status(self, data_entrada: datetime, data_saida: datetime) -> str:
        """Determina o status da reserva baseado nas datas."""
        hoje = datetime.now().date()
        dias_para_entrada = (data_entrada - hoje).days
        dias_para_saida = (data_saida - hoje).days

        if dias_para_saida < 0:
            return 'FINALIZADA'
        elif dias_para_entrada <= 0:
            return 'CHECKIN'
        else:
            return 'CONFIRMADA'

    def process_reservation(self, row: Dict, is_complete: bool = False) -> None:
        """Processa uma linha do CSV."""
        try:
            with transaction.atomic():
                # Verifica campos obrigatórios
                required_fields = ['Data da reserva', 'Data de início', 'Data de término', 'Hóspede']
                for field in required_fields:
                    if not row.get(field):
                        self.erros.append(f'Campo obrigatório não encontrado: {field}')
                        return

                # Cria ou obtém a pessoa
                pessoa, _ = Pessoa.objects.get_or_create(
                    nome=row['Hóspede'].strip()
                )
                
                # Pega ou gera o código de confirmação
                codigo = row.get('Código de Confirmação', '').strip() or self.generate_confirmation_code()
                    
                # Processa as datas
                data_reserva = self.parse_date(row['Data da reserva'])
                data_entrada = self.parse_date(row['Data de início'])
                data_saida = self.parse_date(row['Data de término'])
                
                if not all([data_reserva, data_entrada, data_saida]):
                    self.erros.append(f'Data inválida para reserva {codigo}')
                    return

                # Determina o status baseado nas datas
                status = self.determine_status(data_entrada, data_saida)
                if is_complete and status not in ['CHECKOUT', 'CHECKIN']:
                    status = 'FINALIZADA'

                # Processa valores financeiros
                valor_bruto = Money(self.parse_decimal(row.get('Valor', '0')), 'BRL')
                
                # Se não houver ganhos brutos especificados, usa o valor bruto
                ganhos_brutos = Money(
                    self.parse_decimal(row.get('Ganhos brutos', str(valor_bruto.amount))), 
                    'BRL'
                )
                
                # Cria ou atualiza a reserva
                reserva = Reserva.objects.filter(codigo_confirmacao=codigo).first()
                
                if not reserva:
                    # Se não existe, cria nova reserva
                    reserva = Reserva.objects.create(
                        hospede_principal=pessoa,
                        plataforma=self.plataforma,
                        codigo_confirmacao=codigo,
                        data_reserva=data_reserva,
                        data_entrada=data_entrada,
                        data_saida=data_saida,
                        noites=int(row.get('Noites', 0) or 0),
                        valor_bruto=valor_bruto,
                        ganhos_brutos=ganhos_brutos,
                        status=status
                    )
                    self.sucessos.append(f'Reserva {codigo} criada com sucesso')
                else:
                    # Atualiza a reserva existente
                    reserva.valor_bruto = valor_bruto
                    reserva.ganhos_brutos = ganhos_brutos
                    reserva.status = status
                    reserva.save()
                    self.sucessos.append(f'Reserva {codigo} atualizada com sucesso')
                    
        except Exception as e:
            self.erros.append(f'Erro ao processar reserva: {str(e)}')

    def process_pending_reservation(self, row: Dict) -> None:
        """Processa uma linha do CSV de reservas pendentes."""
        self.process_reservation(row, is_complete=False)
    
    def process_complete_reservation(self, row: Dict) -> None:
        """Processa uma linha do CSV completo."""
        if row.get('Tipo', '').strip() == 'Payout':
            return
        self.process_reservation(row, is_complete=True)

    def get_result(self) -> Dict:
        """Retorna o resultado da importação."""
        return {
            'success': len(self.erros) == 0,
            'imported': len(self.sucessos),
            'errors': self.erros
        }

    def import_csv(self, file_path: str) -> Dict:
        """Importa CSV de reservas."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if self.is_pending:
                        self.process_pending_reservation(row)
                    else:
                        self.process_complete_reservation(row)
        except Exception as e:
            self.erros.append(str(e))
        
        return self.get_result()
