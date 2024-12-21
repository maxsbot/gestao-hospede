from django.urls import path
from . import views

app_name = 'hospedes'

urlpatterns = [
    # URLs serão implementadas posteriormente
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('importar-csv/', views.importar_csv, name='importar_csv'),
    path('reservas/criar/', views.CriarReservaView.as_view(), name='criar_reserva'),
]
