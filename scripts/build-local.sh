#!/bin/bash
# Script para build e teste local com Docker

set -e

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Nome da imagem
IMAGE_NAME="ml-orchestrator:local"
CONTAINER_NAME="ml-orchestrator-local"

print_color $YELLOW "🔨 Construindo imagem Docker local..."

# Build da imagem
docker build -t ${IMAGE_NAME} .

if [ $? -ne 0 ]; then
    print_color $RED "❌ Falha no build da imagem"
    exit 1
fi

print_color $GREEN "✅ Imagem construída com sucesso!"

# Parar container anterior se existir
if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
    print_color $YELLOW "🛑 Parando container anterior..."
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
fi

# Verificar se .env existe
if [ ! -f ".env" ]; then
    print_color $YELLOW "📝 Criando arquivo .env a partir do template..."
    cp .env.example .env
    print_color $RED "⚠️  Por favor, edite .env com as URLs corretas!"
fi

print_color $YELLOW "🚀 Iniciando container..."

# Executar container
docker run -d \
    --name ${CONTAINER_NAME} \
    -p 8080:8080 \
    --env-file .env \
    -e LOG_LEVEL=INFO \
    ${IMAGE_NAME}

if [ $? -ne 0 ]; then
    print_color $RED "❌ Falha ao iniciar container"
    exit 1
fi

print_color $GREEN "✅ Container iniciado!"

# Aguardar container ficar pronto
print_color $YELLOW "⏳ Aguardando serviço ficar pronto..."
sleep 5

# Testar health check
print_color $YELLOW "🏥 Testando health check..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health | grep -q "200"; then
    print_color $GREEN "✅ Health check OK!"
    curl -s http://localhost:8080/health | jq .
else
    print_color $RED "❌ Health check falhou"
    print_color $YELLOW "Verificando logs..."
    docker logs ${CONTAINER_NAME} --tail 20
fi

echo ""
print_color $GREEN "🎉 Serviço rodando em http://localhost:8080"
echo ""
echo "Comandos úteis:"
echo "  Ver logs: docker logs -f ${CONTAINER_NAME}"
echo "  Parar: docker stop ${CONTAINER_NAME}"
echo "  Remover: docker rm ${CONTAINER_NAME}"
echo "  Testar: curl -X POST http://localhost:8080/orchestrate -H 'Content-Type: application/json' -d @test_payload.json"
echo "  Docs: http://localhost:8080/docs"