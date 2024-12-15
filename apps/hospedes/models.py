from django.db import models
from django.core.validators import MinValueValidator
from djmoney.models.fields import MoneyField
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, time, timedelta
import re
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

def validate_cpf(value):
    if value:
        cpf = re.sub(r'[^0-9]', '', value)
        if len(cpf) != 11:
            raise ValidationError('CPF deve conter 11 dígitos.')

class BaseModel(models.Model):
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    class Meta:
        abstract = True

class Pessoa(BaseModel):
    nome = models.CharField('Nome', max_length=200)
    cpf = models.CharField('CPF', max_length=14, validators=[validate_cpf], blank=True, null=True, unique=True)
    rg = models.CharField('RG', max_length=20, blank=True, null=True)
    orgao_emissor = models.CharField('Órgão Emissor', max_length=20, blank=True, null=True)
    endereco = models.TextField('Endereço', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Pessoa'
        verbose_name_plural = 'Pessoas'
        ordering = ['nome']
    
    def __str__(self):
        return self.nome

class Contato(BaseModel):
    TIPO_CHOICES = [
        ('TELEFONE', 'Telefone'),
        ('EMAIL', 'E-mail'),
        ('WHATSAPP', 'WhatsApp'),
        ('OUTRO', 'Outro'),
    ]
    
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='contatos')
    tipo = models.CharField('Tipo', max_length=10, choices=TIPO_CHOICES)
    valor = models.CharField('Valor', max_length=100)
    principal = models.BooleanField('Principal', default=False)
    observacoes = models.TextField('Observações', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Contato'
        verbose_name_plural = 'Contatos'
        ordering = ['-principal', 'tipo']
    
    def __str__(self):
        return f'{self.get_tipo_display()}: {self.valor}'

class RelacionamentoPessoas(BaseModel):
    TIPO_CHOICES = [
        ('INDICOU', 'Indicou'),
        ('RESPONSAVEL_RESERVA', 'Responsável pela Reserva'),
        ('FAMILIAR', 'Familiar'),
        ('OUTRO', 'Outro'),
    ]
    
    pessoa_origem = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='relacionamentos_origem')
    pessoa_destino = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='relacionamentos_destino')
    tipo_relacionamento = models.CharField('Tipo de Relacionamento', max_length=20, choices=TIPO_CHOICES)
    data_relacionamento = models.DateField('Data do Relacionamento', auto_now_add=True)
    observacoes = models.TextField('Observações', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Relacionamento'
        verbose_name_plural = 'Relacionamentos'
        ordering = ['-data_relacionamento']
    
    def __str__(self):
        return f'{self.pessoa_origem} → {self.pessoa_destino} ({self.get_tipo_relacionamento_display()})'

class Plataforma(BaseModel):
    nome = models.CharField('Nome', max_length=50, unique=True)
    ativo = models.BooleanField('Ativo', default=True)
    
    class Meta:
        verbose_name = 'Plataforma'
        verbose_name_plural = 'Plataformas'
        ordering = ['nome']
    
    def __str__(self):
        return self.nome

class Reserva(BaseModel):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('CONFIRMADA', 'Confirmada'),
        ('CHECKIN', 'Check-in'),
        ('CHECKOUT', 'Check-out'),
        ('CANCELADA', 'Cancelada'),
        ('FINALIZADA', 'Finalizada'),
    ]
    
    hospede_principal = models.ForeignKey(Pessoa, on_delete=models.PROTECT, related_name='reservas')
    plataforma = models.ForeignKey(Plataforma, on_delete=models.PROTECT)
    codigo_confirmacao = models.CharField('Código de Confirmação', max_length=50, unique=True, blank=True, null=True)
    data_reserva = models.DateField('Data da Reserva')
    data_entrada = models.DateField('Data de Entrada')
    data_saida = models.DateField('Data de Saída')
    noites = models.IntegerField('Noites', default=0)
    num_adultos = models.IntegerField('Número de Adultos', default=1)
    num_criancas = models.IntegerField('Número de Crianças', default=0, validators=[MinValueValidator(0)])
    
    # Campos financeiros
    valor_bruto = MoneyField('Valor Bruto', max_digits=10, decimal_places=2, default_currency='BRL')
    taxa_servico = MoneyField('Taxa de Serviço', max_digits=10, decimal_places=2, default_currency='BRL', default=0)
    taxa_limpeza = MoneyField('Taxa de Limpeza', max_digits=10, decimal_places=2, default_currency='BRL', default=0)
    ganhos_brutos = MoneyField('Ganhos Brutos', max_digits=10, decimal_places=2, default_currency='BRL')
    impostos = MoneyField('Impostos', max_digits=10, decimal_places=2, default_currency='BRL', default=0)
    
    status = models.CharField('Status', max_length=15, choices=STATUS_CHOICES, default='CONFIRMADA')
    observacoes = models.TextField('Observações', blank=True, null=True)
    
    # Campos de controle de estadia
    data_checkin = models.DateTimeField('Data/Hora do Check-in', null=True, blank=True)
    data_checkout = models.DateTimeField('Data/Hora do Check-out', null=True, blank=True)
    checkin_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='checkins_realizados'
    )
    checkout_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='checkouts_realizados'
    )
    observacoes_checkin = models.TextField('Observações do Check-in', blank=True, null=True)
    observacoes_checkout = models.TextField('Observações do Check-out', blank=True, null=True)
    
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-data_entrada']

    def __str__(self):
        return f'{self.codigo_confirmacao} - {self.hospede_principal.nome}'

    @property
    def calcular_status(self):
        """Calcula o status da reserva baseado nas datas de check-in e check-out"""
        hoje = timezone.now().date()
        proximos_7_dias = hoje + timedelta(days=7)
        
        # 1. Verificar check-in próximo
        if hoje <= self.data_entrada <= proximos_7_dias:
            if self.data_entrada == hoje:
                return {
                    'texto': 'Check-in hoje',
                    'classe': 'bg-danger',
                    'prioridade': 1
                }
            return {
                'texto': 'Check-in próximo',
                'classe': 'bg-warning',
                'prioridade': 2
            }
            
        # 2. Verificar status baseado no check-in passado
        if self.data_entrada < hoje:
            if hoje <= self.data_saida <= proximos_7_dias:
                if self.data_saida == hoje:
                    return {
                        'texto': 'Check-out hoje',
                        'classe': 'bg-danger',
                        'prioridade': 1
                    }
                return {
                    'texto': 'Check-out próximo',
                    'classe': 'bg-warning',
                    'prioridade': 2
                }
            
            if self.data_saida > hoje:
                return {
                    'texto': 'Em andamento',
                    'classe': 'bg-primary',
                    'prioridade': 3
                }
            
            if self.data_saida <= hoje:
                return {
                    'texto': 'Concluído',
                    'classe': 'bg-success',
                    'prioridade': 4
                }
        
        # 3. Reservas futuras
        if self.data_entrada > proximos_7_dias:
            return {
                'texto': 'Confirmada',
                'classe': 'bg-secondary',
                'prioridade': 5
            }
        
        # 4. Status padrão para casos não cobertos
        return {
            'texto': 'Status indefinido',
            'classe': 'bg-secondary',
            'prioridade': 6
        }

    @property
    def horario_checkin_padrao(self):
        """Retorna o horário padrão de check-in (15:00)"""
        return time(hour=15, minute=0)
        
    @property
    def horario_checkout_padrao(self):
        """Retorna o horário padrão de check-out (12:00)"""
        return time(hour=12, minute=0)

    def realizar_checkin(self, user, observacoes=None):
        """Realiza o check-in da reserva."""
        hoje = timezone.now().date()
        
        # Só permite check-in se estiver confirmada
        if self.status != 'CONFIRMADA':
            raise ValidationError('Só é possível realizar check-in em reservas confirmadas.')
            
        # Não permite check-in muito antecipado
        if (self.data_entrada - hoje).days > 1:
            raise ValidationError('Não é possível realizar check-in com mais de 1 dia de antecedência.')
            
        # Se for hoje, usa hora atual, senão usa hora padrão
        if hoje == self.data_entrada:
            self.data_checkin = timezone.now()
        else:
            self.data_checkin = datetime.combine(
                self.data_entrada,
                self.horario_checkin_padrao
            ).replace(tzinfo=timezone.get_current_timezone())
            
        self.checkin_por = user
        self.observacoes_checkin = observacoes
        self.status = 'CHECKIN'
        self.save()
        
    def realizar_checkout(self, user, observacoes=None):
        """Realiza o check-out da reserva."""
        hoje = timezone.now().date()
        
        # Só permite checkout se já fez checkin
        if self.status != 'CHECKIN':
            raise ValidationError('Só é possível realizar check-out após o check-in.')
            
        # Se for hoje, usa hora atual, senão usa hora padrão
        if hoje == self.data_saida:
            self.data_checkout = timezone.now()
        else:
            self.data_checkout = datetime.combine(
                self.data_saida,
                self.horario_checkout_padrao
            ).replace(tzinfo=timezone.get_current_timezone())
            
        self.checkout_por = user
        self.observacoes_checkout = observacoes
        self.status = 'CHECKOUT'
        self.save()

    @property
    def status_atual(self):
        """Retorna o status atual baseado nas datas."""
        hoje = timezone.now().date()
        
        # Se foi cancelada, mantém cancelada
        if self.status == 'CANCELADA':
            return 'CANCELADA'
            
        # Se está pendente e é do Airbnb, muda para confirmada
        if self.status == 'PENDENTE' and self.plataforma.nome == 'Airbnb':
            return 'CONFIRMADA'
            
        # Se já passou da data de saída e teve checkout
        if hoje > self.data_saida and self.status == 'CHECKOUT':
            return 'FINALIZADA'
            
        return self.status

    def save(self, *args, **kwargs):
        """Sobrescreve o método save para atualizar o status automaticamente."""
        if not self.codigo_confirmacao and self.plataforma.nome == 'Airbnb':
            self.status = 'CONFIRMADA'
        
        # Atualiza o status baseado nas datas
        novo_status = self.status_atual
        if novo_status != self.status:
            self.status = novo_status
            
        # Calcula as noites
        if self.data_entrada and self.data_saida:
            delta = self.data_saida - self.data_entrada
            self.noites = delta.days
            
        super().save(*args, **kwargs)

    def clean(self):
        """Valida os dados antes de salvar."""
        if self.data_entrada and self.data_saida:
            if self.data_entrada > self.data_saida:
                raise ValidationError('A data de entrada não pode ser posterior à data de saída.')
                
            if self.data_entrada < self.data_reserva:
                raise ValidationError('A data de entrada não pode ser anterior à data da reserva.')

class DocumentoReserva(BaseModel):
    TIPO_CHOICES = [
        ('RG', 'RG'),
        ('CPF', 'CPF'),
        ('COMP_RESIDENCIA', 'Comprovante de Residência'),
        ('OUTRO', 'Outro'),
    ]
    
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='documentos')
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='documentos')
    tipo_documento = models.CharField('Tipo de Documento', max_length=20, choices=TIPO_CHOICES)
    arquivo = models.FileField('Arquivo', upload_to='documentos/%Y/%m/')
    observacoes = models.TextField('Observações', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['tipo_documento']
    
    def __str__(self):
        return f'{self.get_tipo_documento_display()} - {self.pessoa.nome}'

class PessoaReserva(BaseModel):
    TIPO_CHOICES = [
        ('HOSPEDE_PRINCIPAL', 'Hóspede Principal'),
        ('RESPONSAVEL_PAGAMENTO', 'Responsável pelo Pagamento'),
        ('CONTATO_EMERGENCIA', 'Contato de Emergência'),
        ('HOSPEDE_ADICIONAL', 'Hóspede Adicional'),
        ('OUTRO', 'Outro'),
    ]
    
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='pessoas')
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='reservas_envolvidas')
    tipo_envolvimento = models.CharField('Tipo de Envolvimento', max_length=25, choices=TIPO_CHOICES)
    observacoes = models.TextField('Observações', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Pessoa na Reserva'
        verbose_name_plural = 'Pessoas na Reserva'
        unique_together = ['reserva', 'pessoa', 'tipo_envolvimento']
        ordering = ['tipo_envolvimento']
    
    def __str__(self):
        return f'{self.pessoa.nome} - {self.get_tipo_envolvimento_display()}'
