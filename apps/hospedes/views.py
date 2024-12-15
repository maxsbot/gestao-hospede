from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from .services import AirbnbCSVImporter


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'hospedes/dashboard.html'
    login_url = reverse_lazy('auth:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adicione aqui qualquer contexto adicional que você precise
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
