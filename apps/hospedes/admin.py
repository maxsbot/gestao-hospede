from django.contrib import admin
from django.utils.html import format_html
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
    list_display = [
        'codigo_confirmacao', 'hospede_principal', 'plataforma',
        'data_entrada', 'data_saida', 'noites', 'status',
        'ganhos_brutos'
    ]
    list_filter = ['status', 'plataforma', 'data_entrada', 'data_saida']
    search_fields = [
        'codigo_confirmacao', 'hospede_principal__nome',
        'hospede_principal__cpf'
    ]
    readonly_fields = ['noites', 'created_at', 'updated_at']
    inlines = [PessoaReservaInline, DocumentoReservaInline]
    
    fieldsets = (
        ('Informações Principais', {
            'fields': (
                'hospede_principal', 'plataforma', 'codigo_confirmacao',
                'status'
            )
        }),
        ('Datas', {
            'fields': (
                'data_reserva', 'data_entrada', 'data_saida', 'noites'
            )
        }),
        ('Hóspedes', {
            'fields': (
                'num_adultos', 'num_criancas'
            )
        }),
        ('Valores', {
            'fields': (
                'valor_bruto', 'taxa_servico', 'taxa_limpeza',
                'ganhos_brutos', 'impostos'
            )
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Metadados', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        })
    )

@admin.register(DocumentoReserva)
class DocumentoReservaAdmin(admin.ModelAdmin):
    list_display = ['reserva', 'pessoa', 'tipo_documento', 'get_arquivo']
    list_filter = ['tipo_documento']
    search_fields = ['reserva__codigo_confirmacao', 'pessoa__nome']
    
    def get_arquivo(self, obj):
        if obj.arquivo:
            return format_html('<a href="{}" target="_blank">Ver arquivo</a>', obj.arquivo.url)
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
