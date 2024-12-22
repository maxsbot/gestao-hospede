#!/bin/bash

# Configurações
PROJECT_DIR="$(pwd)"
GUNICORN_PID_FILE="$HOME/app_logs/gunicorn.pid"
GUNICORN_LOG_FILE="$HOME/app_logs/gunicorn.log"
NGINX_LOG_FILE="$HOME/nginx_logs/error.log"
VENV_PATH="$PROJECT_DIR/.venv"

# Função para verificar erros
check_error() {
    if [ $? -ne 0 ]; then
        echo "Erro: $1"
        exit 1
    fi
}

# Verifica se o ambiente virtual existe
check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        echo "Erro: Ambiente virtual não encontrado em $VENV_PATH"
        echo "Execute ./termux_setup.sh primeiro"
        exit 1
    fi
}

start_services() {
    echo "Iniciando serviços..."
    
    # Verificar ambiente virtual
    check_venv
    
    # Ativar ambiente virtual
    source "$VENV_PATH/bin/activate"
    check_error "Falha ao ativar ambiente virtual"
    
    # Matar processos anteriores se existirem
    stop_services quiet
    
    # Criar diretórios de log se não existirem
    mkdir -p "$(dirname "$GUNICORN_LOG_FILE")" "$(dirname "$NGINX_LOG_FILE")"
    
    # Iniciar Gunicorn com socket Unix
    echo "Iniciando Gunicorn..."
    gunicorn core.wsgi:application \
        --bind unix:/data/data/com.termux/files/home/app_logs/gunicorn.sock \
        --pid "$GUNICORN_PID_FILE" \
        --log-file "$GUNICORN_LOG_FILE" \
        --log-level debug \
        --daemon
    check_error "Falha ao iniciar Gunicorn"
    
    # Iniciar Nginx
    echo "Iniciando Nginx..."
    nginx
    check_error "Falha ao iniciar Nginx"
    
    echo "Serviços iniciados com sucesso!"
    echo "Acesse: http://localhost:8083"
    
    # Mostrar status inicial
    sleep 2
    check_status
}

stop_services() {
    local quiet=$1
    
    [ "$quiet" != "quiet" ] && echo "Parando serviços..."
    
    # Parar Nginx de forma mais agressiva
    pkill -9 -f nginx
    rm -f ~/nginx_logs/nginx.pid
    
    # Parar Gunicorn
    if [ -f "$GUNICORN_PID_FILE" ]; then
        kill -9 $(cat "$GUNICORN_PID_FILE") 2>/dev/null
        rm -f "$GUNICORN_PID_FILE"
    fi
    pkill -9 -f gunicorn
    
    # Garantir que as portas estejam livres
    sleep 2
    
    [ "$quiet" != "quiet" ] && echo "Serviços parados!"
}

restart_services() {
    echo "Reiniciando serviços..."
    stop_services quiet
    sleep 2
    start_services
}

check_status() {
    echo "=== Status dos Serviços ==="
    
    # Verificar Nginx
    if pgrep -x "nginx" > /dev/null; then
        echo "Nginx: ✅ Rodando"
    else
        echo "Nginx: ❌ Parado"
    fi
    
    # Verificar Gunicorn
    if [ -f "$GUNICORN_PID_FILE" ] && kill -0 $(cat "$GUNICORN_PID_FILE") 2>/dev/null; then
        echo "Gunicorn: ✅ Rodando (PID: $(cat "$GUNICORN_PID_FILE"))"
    else
        echo "Gunicorn: ❌ Parado"
    fi
    
    # Mostrar portas em uso
    echo -e "\nPortas em uso:"
    netstat -tulnp | grep -E '8082|8001' || echo "Nenhuma porta relevante em uso"
    
    # Mostrar últimas linhas dos logs se existirem
    if [ -f "$NGINX_LOG_FILE" ]; then
        echo -e "\nÚltimas linhas do log do Nginx:"
        tail -n 5 "$NGINX_LOG_FILE"
    fi
    
    if [ -f "$GUNICORN_LOG_FILE" ]; then
        echo -e "\nÚltimas linhas do log do Gunicorn:"
        tail -n 5 "$GUNICORN_LOG_FILE"
    fi
}

case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        check_status
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0
