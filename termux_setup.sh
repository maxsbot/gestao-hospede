#!/bin/bash

# Função para verificar erros
check_error() {
    if [ $? -ne 0 ]; then
        echo "Erro: $1"
        exit 1
    fi
}

echo "=== Iniciando setup do ambiente Termux ==="

# Obter caminho absoluto do projeto
PROJECT_DIR="$(pwd)"
echo "Diretório do projeto: $PROJECT_DIR"

# Atualizar repositórios e pacotes
echo "Atualizando pacotes..."
pkg update -y
check_error "Falha ao atualizar pacotes"
pkg upgrade -y
check_error "Falha ao fazer upgrade dos pacotes"

# Instalar dependências necessárias
echo "Instalando dependências..."
pkg install -y python nginx git nano net-tools
check_error "Falha ao instalar dependências"

# Criar estrutura de diretórios
echo "Configurando diretórios..."
mkdir -p ~/nginx_logs ~/app_logs
check_error "Falha ao criar diretórios de log"

# Configurar ambiente Python
echo "Configurando ambiente Python..."
python -m venv .venv
check_error "Falha ao criar ambiente virtual"
source .venv/bin/activate
check_error "Falha ao ativar ambiente virtual"

# Instalar dependências Python
echo "Instalando dependências Python..."
pip install --upgrade pip
check_error "Falha ao atualizar pip"
pip install gunicorn whitenoise tzdata
check_error "Falha ao instalar dependências base"
pip install -r requirements-dev.txt
check_error "Falha ao instalar requirements.txt"

# Configurar Nginx
echo "Configurando Nginx..."
cat > $PREFIX/etc/nginx/nginx.conf << EOL
worker_processes  1;
error_log  /data/data/com.termux/files/home/nginx_logs/error.log;
pid        /data/data/com.termux/files/home/nginx_logs/nginx.pid;

events {
    worker_connections  1024;
}

http {
    include       /data/data/com.termux/files/usr/etc/nginx/mime.types;
    default_type  application/octet-stream;
    access_log    /data/data/com.termux/files/home/nginx_logs/access.log;

    upstream django {
        server unix:/data/data/com.termux/files/home/app_logs/gunicorn.sock;
    }

    sendfile        on;
    keepalive_timeout  65;

    server {
        listen       8083;
        server_name  localhost;

        location / {
            proxy_pass http://django;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location /static/ {
            alias ${PROJECT_DIR}/static/;
        }

        location /media/ {
            alias ${PROJECT_DIR}/media/;
        }
    }
}
EOL
check_error "Falha ao criar configuração do Nginx"

# Configurar variáveis de ambiente
echo "Configurando variáveis de ambiente..."
if [ ! -f .env ]; then
    cat > .env << 'EOL'
DEBUG=True
SECRET_KEY=django-insecure-0k6wp0k#bj4n9v3@u9pq2x$_6mg&4zk0sz8y3x#q_5f4q=9pxm
ALLOWED_HOSTS=*
EOL
    check_error "Falha ao criar arquivo .env"
else
    echo "Arquivo .env já existe, mantendo configuração atual"
fi

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput
check_error "Falha ao coletar arquivos estáticos"

# Aplicar migrações
echo "Aplicando migrações do banco de dados..."
python manage.py migrate
check_error "Falha ao aplicar migrações"

echo "=== Setup concluído com sucesso! ==="
echo "Use './termux_manage.sh start' para iniciar a aplicação"
