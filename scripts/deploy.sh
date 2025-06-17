#!/bin/bash
# Script de deploy para Cloud Run

set -e  # Exit on error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para imprimir com cor
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Verificar parâmetros
if [ $# -lt 1 ]; then
    print_color $RED "Uso: $0 <PROJECT_ID> [REGION] [SERVICE_NAME]"
    echo "Exemplo: $0 meu-projeto us-central1 ml-orchestrator"
    exit 1
fi

# Configurações
PROJECT_ID=$1
REGION=${2:-us-central1}
SERVICE_NAME=${3:-ml-orchestrator}
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

print_color $YELLOW "🚀 Iniciando deploy do ML Orchestrator"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Image: ${IMAGE_NAME}"
echo ""

# Verificar se está autenticado
print_color $YELLOW "📋 Verificando autenticação..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_color $RED "❌ Não autenticado no gcloud. Execute: gcloud auth login"
    exit 1
fi

# Configurar projeto
print_color $YELLOW "🔧 Configurando projeto..."
gcloud config set project ${PROJECT_ID}

# Verificar qual arquivo de variáveis usar
if [ -f ".env" ]; then
    print_color $YELLOW "📋 Usando arquivo .env encontrado"
    ENV_SOURCE=".env"
    ENV_FLAG="--set-env-vars"
    # Converter .env para formato do Cloud Run
    ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | sed 's/^/^/' | tr '\n' ',' | sed 's/,$//')
elif [ -f "deployments/env-vars.yaml" ]; then
    print_color $YELLOW "📋 Usando arquivo deployments/env-vars.yaml"
    ENV_SOURCE="deployments/env-vars.yaml"
    ENV_FLAG="--env-vars-file"
    ENV_VARS="$ENV_SOURCE"
else
    print_color $RED "❌ Nenhum arquivo de variáveis encontrado!"
    print_color $YELLOW "💡 Crie um arquivo .env ou deployments/env-vars.yaml"
    print_color $YELLOW "📝 Exemplo: cp .env.example .env"
    exit 1
fi

# Build da imagem
print_color $YELLOW "🔨 Construindo imagem Docker..."
gcloud builds submit --tag ${IMAGE_NAME} .

if [ $? -ne 0 ]; then
    print_color $RED "❌ Falha no build da imagem"
    exit 1
fi

print_color $GREEN "✅ Imagem construída com sucesso!"

# Deploy no Cloud Run
print_color $YELLOW "☁️  Fazendo deploy no Cloud Run..."

# Comando de deploy
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --memory 2Gi \
    --cpu 2 \
    --timeout 540 \
    --max-instances 100 \
    --min-instances 1 \
    --allow-unauthenticated \
    ${ENV_FLAG} "${ENV_VARS}" \
    --port 8080

if [ $? -ne 0 ]; then
    print_color $RED "❌ Falha no deploy"
    exit 1
fi

# Obter URL do serviço
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

print_color $GREEN "✅ Deploy concluído com sucesso!"
print_color $GREEN "🌐 URL do serviço: ${SERVICE_URL}"
echo ""

# Testar health check
print_color $YELLOW "🏥 Testando health check..."
HEALTH_URL="${SERVICE_URL}/health"

sleep 5  # Aguardar serviço estabilizar

if curl -s -o /dev/null -w "%{http_code}" ${HEALTH_URL} | grep -q "200"; then
    print_color $GREEN "✅ Health check OK!"
    curl -s ${HEALTH_URL} | jq .
else
    print_color $RED "❌ Health check falhou"
    print_color $YELLOW "Verifique os logs com: gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"
fi

echo ""
print_color $GREEN "🎉 Deploy finalizado!"
echo ""
echo "Comandos úteis:"
echo "  Ver logs: gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"
echo "  Descrever serviço: gcloud run services describe ${SERVICE_NAME} --region ${REGION}"
echo "  Testar: curl -X POST ${SERVICE_URL}/orchestrate -H 'Content-Type: application/json' -d @test_payload.json"