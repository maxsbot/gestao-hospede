from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Sum
from .models import Reserva
from .services import AirbnbCSVImporter
from datetime import datetime, timedelta

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
        context['reservas_hoje'] = Reserva.objects.filter(
            data_entrada=hoje
        ).count()
        context['checkout_hoje'] = Reserva.objects.filter(
            data_saida=hoje
        ).count()
        
        # Dados para a tabela de reservas
        reservas = Reserva.objects.select_related(
            'hospede_principal', 'plataforma'
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
        reservas = sorted(reservas, key=lambda r: (r.calcular_status['prioridade'], r.data_entrada))
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
