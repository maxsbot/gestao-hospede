from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse
from .models import (
    Pessoa, Contato, RelacionamentoPessoas, Plataforma,
    Reserva, DocumentoReserva, PessoaReserva
)

class ContatoInline(admin.TabularInline):
    model = Contato
    extra = 1

class DocumentoReservaInline(admin.TabularInline):
    model = DocumentoReserva
    extra = 1

class PessoaReservaInline(admin.TabularInline):
    model = PessoaReserva
    extra = 1

@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'rg', 'get_contatos']
    search_fields = ['nome', 'cpf', 'rg']
    inlines = [ContatoInline]
    
    def get_contatos(self, obj):
        contatos = obj.contatos.filter(principal=True)
        return ', '.join([f'{c.get_tipo_display()}: {c.valor}' for c in contatos])
    get_contatos.short_description = 'Contatos Principais'

@admin.register(RelacionamentoPessoas)
class RelacionamentoPessoasAdmin(admin.ModelAdmin):
    list_display = ['pessoa_origem', 'tipo_relacionamento', 'pessoa_destino', 'data_relacionamento']
    list_filter = ['tipo_relacionamento', 'data_relacionamento']
    search_fields = ['pessoa_origem__nome', 'pessoa_destino__nome']
    date_hierarchy = 'data_relacionamento'

@admin.register(Plataforma)
class PlataformaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome']

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['codigo_confirmacao', 'hospede_principal', 'plataforma', 
                   'data_entrada', 'data_saida', 'noites', 'status', 'ganhos_brutos']
    list_filter = ['status', 'plataforma']
    search_fields = ['codigo_confirmacao', 'hospede_principal__nome']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [DocumentoReservaInline, PessoaReservaInline]
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj and obj.status in ['CHECKIN', 'CHECKOUT', 'FINALIZADA']:
            readonly_fields.extend(['data_entrada', 'data_saida'])
        return readonly_fields
    
    def save_model(self, request, obj, form, change):
        if not obj.codigo_confirmacao:
            # Gera um código de confirmação único
            prefix = 'HM'  # Hotel Manager
            import uuid
            while True:
                new_code = f"{prefix}{uuid.uuid4().hex[:8].upper()}"
                if not type(obj).objects.filter(codigo_confirmacao=new_code).exists():
                    obj.codigo_confirmacao = new_code
                    break
        super().save_model(request, obj, form, change)

@admin.register(DocumentoReserva)
class DocumentoReservaAdmin(admin.ModelAdmin):
    list_display = ['reserva', 'pessoa', 'tipo_documento', 'get_arquivo']
    list_filter = ['tipo_documento']
    search_fields = ['reserva__codigo_confirmacao', 'pessoa__nome']
    
    def get_arquivo(self, obj):
        if obj.arquivo:
            return format_html('<a href="{}" target="_blank">Visualizar</a>', obj.arquivo.url)
        return '-'
    get_arquivo.short_description = 'Arquivo'

@admin.register(PessoaReserva)
class PessoaReservaAdmin(admin.ModelAdmin):
    list_display = ['reserva', 'pessoa', 'tipo_envolvimento']
    list_filter = ['tipo_envolvimento']
    search_fields = [
        'reserva__codigo_confirmacao',
        'pessoa__nome',
        'pessoa__cpf'
    ]
