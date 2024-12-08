from django.db import models
from django.core.validators import MinValueValidator
from djmoney.models.fields import MoneyField
from django.core.exceptions import ValidationError
import re

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
        ('CHECKIN', 'Check-in Realizado'),
        ('CHECKOUT', 'Check-out Realizado'),
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
    
    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-data_entrada']
    
    def __str__(self):
        return f'{self.codigo_confirmacao} - {self.hospede_principal.nome}'
    
    def clean(self):
        if self.data_entrada and self.data_saida:
            if self.data_entrada >= self.data_saida:
                raise ValidationError('Data de entrada deve ser anterior à data de saída')
            
            # Atualiza número de noites
            delta = self.data_saida - self.data_entrada
            self.noites = delta.days

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
