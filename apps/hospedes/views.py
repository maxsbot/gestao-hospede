from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Sum, F
from .models import Reserva
from .services import AirbnbCSVImporter
from datetime import datetime, timedelta
import csv
import tempfile
import os

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'hospedes/dashboard.html'
    login_url = reverse_lazy('auth:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.localtime().date()
        
        # Pegar o status do filtro da URL
        filtro_status = self.request.GET.get('status')
        context['filtro_status'] = filtro_status
        
        # Filtros básicos
        reservas_programadas = Reserva.objects.filter(status='CONFIRMADA')
        reservas_em_andamento = Reserva.objects.filter(
            data_entrada__lte=hoje,
            data_saida__gte=hoje
        )
        reservas_concluidas = Reserva.objects.filter(
            data_saida__lt=hoje
        ).exclude(status='CANCELADA')
        reservas_canceladas = Reserva.objects.filter(status='CANCELADA')
        
        # Estatísticas para os cards
        context['total_reservas'] = Reserva.objects.count()
        
        # Reservas programadas e suas receitas
        reservas_programadas = Reserva.objects.filter(
            status='CONFIRMADA',
            data_entrada__gte=hoje
        )
        context['reservas_programadas'] = reservas_programadas.count()
        
        # Calcula o total somando valor_bruto + taxa_servico + taxa_limpeza - impostos
        context['receitas_programadas'] = reservas_programadas.aggregate(
            total=Sum(F('valor_bruto') + F('taxa_servico') + F('taxa_limpeza') - F('impostos'))
        )['total'] or 0
        
        context['reservas_hoje'] = Reserva.objects.filter(
            data_entrada=hoje
        ).count()
        context['checkout_hoje'] = Reserva.objects.filter(
            data_saida=hoje
        ).count()
        
        # Dados para a tabela de reservas
        reservas = Reserva.objects.select_related(
            'hospede_principal', 'plataforma'
        ).prefetch_related(
            'hospede_principal__contatos'
        )
        
        # Aplicar filtro baseado no status selecionado
        if filtro_status == 'em_andamento':
            reservas = reservas_em_andamento
        elif filtro_status == 'concluidas':
            reservas = reservas_concluidas
        elif filtro_status == 'canceladas':
            reservas = reservas_canceladas
        else:  # programadas (default)
            reservas = reservas.filter(
                data_saida__gte=hoje
            ).exclude(status='CANCELADA')
        
        # Ordenar reservas por prioridade do status calculado e data de check-in
        if filtro_status == 'concluidas':
            # Para concluídas, ordenar por data de check-in decrescente (mais recente primeiro)
            reservas = sorted(reservas, key=lambda r: (r.calcular_status['prioridade'], -r.data_entrada.toordinal()))
        else:
            # Para as demais, manter ordem crescente de data
            reservas = sorted(reservas, key=lambda r: (r.calcular_status['prioridade'], r.data_entrada))
            
        # Preparar os dados de contato para cada reserva
        for reserva in reservas:
            whatsapp = reserva.hospede_principal.contatos.filter(tipo='WHATSAPP').first()
            if whatsapp:
                # Remove todos os caracteres não numéricos do telefone
                telefone_limpo = ''.join(filter(str.isdigit, whatsapp.valor))
                # Adiciona o código do país se não estiver presente
                if not telefone_limpo.startswith('55'):
                    telefone_limpo = '55' + telefone_limpo
                reserva.whatsapp_link = f"https://wa.me/{telefone_limpo}?text=Oi,%20{reserva.hospede_principal.nome.split()[0]}"
            else:
                reserva.whatsapp_link = None
                
        context['reservas'] = reservas
        
        # Contadores para as abas
        context['count_programadas'] = reservas_programadas.count()
        context['count_em_andamento'] = reservas_em_andamento.count()
        context['count_concluidas'] = reservas_concluidas.count()
        context['count_canceladas'] = reservas_canceladas.count()
        
        return context


class ImportarCSVAirbnbView(LoginRequiredMixin, View):
    template_name = 'hospedes/importar_csv.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo CSV')
            return redirect('importar_csv')
        
        csv_file = request.FILES['csv_file']
        tipo_importacao = request.POST.get('tipo_importacao')
        
        # Salva o arquivo temporariamente
        with open(f'/tmp/{csv_file.name}', 'wb+') as destination:
            for chunk in csv_file.chunks():
                destination.write(chunk)
        
        # Processa o arquivo
        importer = AirbnbCSVImporter()
        if tipo_importacao == 'pendente':
            resultado = importer.import_pending_csv(f'/tmp/{csv_file.name}')
        else:
            resultado = importer.import_complete_csv(f'/tmp/{csv_file.name}')
        
        # Adiciona mensagens de feedback
        for sucesso in resultado['sucessos']:
            messages.success(request, sucesso)
        
        for erro in resultado['erros']:
            messages.error(request, erro)
        
        return redirect('importar_csv')


def importar_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        try:
            csv_file = request.FILES['csv_file']
            
            # Salva o arquivo temporariamente
            temp_file_path = os.path.join(tempfile.gettempdir(), csv_file.name)
            with open(temp_file_path, 'wb+') as destination:
                for chunk in csv_file.chunks():
                    destination.write(chunk)
            
            # Processa o arquivo
            importer = AirbnbCSVImporter()
            resultado = importer.import_csv(temp_file_path)
            
            # Remove o arquivo temporário
            os.remove(temp_file_path)
            
            # Se houver erros, retorna eles
            if resultado['errors']:
                return JsonResponse({
                    'success': False,
                    'error': f"Erro ao importar: {resultado['errors'][0]}. {resultado['imported']} reservas foram importadas com sucesso."
                })
            
            # Se tudo deu certo
            return JsonResponse({
                'success': True,
                'message': f"{resultado['imported']} reservas foram importadas."
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"Erro inesperado: {str(e)}"
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Nenhum arquivo foi enviado. Por favor, selecione um arquivo CSV.'
    })

class CriarReservaView(LoginRequiredMixin, TemplateView):
    template_name = 'hospedes/criar_reserva.html'
    login_url = reverse_lazy('auth:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
