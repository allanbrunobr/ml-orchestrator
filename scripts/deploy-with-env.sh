#!/bin/bash
# Script aprimorado de deploy que suporta .env diretamente

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_color $BLUE "🚀 Deploy do ML Orchestrator com suporte a .env"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Autenticação
print_color $YELLOW "📋 Verificando autenticação..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_color $RED "❌ Não autenticado. Execute: gcloud auth login"
    exit 1
fi

gcloud config set project ${PROJECT_ID}

# Gerenciar variáveis de ambiente
print_color $YELLOW "🔍 Procurando arquivo de variáveis..."

DEPLOY_ENV_VARS=""

# Opção 1: Usar .env se existir
if [ -f ".env" ]; then
    print_color $GREEN "✅ Arquivo .env encontrado"
    
    # Converter .env para YAML temporário
    TEMP_YAML="/tmp/cloudrun-env-$$.yaml"
    ./scripts/env-to-cloudrun.sh .env "$TEMP_YAML"
    
    DEPLOY_ENV_VARS="--env-vars-file $TEMP_YAML"
    
# Opção 2: Usar env-vars.yaml se existir
elif [ -f "deployments/env-vars.yaml" ]; then
    print_color $GREEN "✅ Arquivo deployments/env-vars.yaml encontrado"
    DEPLOY_ENV_VARS="--env-vars-file deployments/env-vars.yaml"
    
# Opção 3: Erro se nenhum arquivo encontrado
else
    print_color $RED "❌ Nenhum arquivo de variáveis encontrado!"
    print_color $YELLOW ""
    print_color $YELLOW "Opções:"
    print_color $YELLOW "1. Crie um arquivo .env com suas variáveis"
    print_color $YELLOW "   cp .env.example .env"
    print_color $YELLOW ""
    print_color $YELLOW "2. Ou crie deployments/env-vars.yaml"
    print_color $YELLOW "   cp deployments/env-vars-template.yaml deployments/env-vars.yaml"
    exit 1
fi

# Build
print_color $YELLOW "🔨 Construindo imagem Docker..."
gcloud builds submit --tag ${IMAGE_NAME} .

if [ $? -ne 0 ]; then
    print_color $RED "❌ Falha no build"
    exit 1
fi

print_color $GREEN "✅ Build concluído!"

# Deploy
print_color $YELLOW "☁️  Fazendo deploy no Cloud Run..."

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
    ${DEPLOY_ENV_VARS} \
    --port 8080

# Limpar arquivo temporário se existir
if [ -f "$TEMP_YAML" ]; then
    rm -f "$TEMP_YAML"
fi

if [ $? -ne 0 ]; then
    print_color $RED "❌ Falha no deploy"
    exit 1
fi

# Obter URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

print_color $GREEN "✅ Deploy concluído!"
print_color $GREEN "🌐 URL: ${SERVICE_URL}"

# Health check
print_color $YELLOW "🏥 Testando health check..."
sleep 5

if curl -s -o /dev/null -w "%{http_code}" ${SERVICE_URL}/health | grep -q "200"; then
    print_color $GREEN "✅ Serviço está saudável!"
else
    print_color $RED "⚠️  Health check falhou"
fi

echo ""
print_color $BLUE "📝 Resumo:"
echo "- Serviço: ${SERVICE_NAME}"
echo "- URL: ${SERVICE_URL}"
echo "- Região: ${REGION}"
echo "- Projeto: ${PROJECT_ID}"
echo ""
echo "Comandos úteis:"
echo "  Logs: gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"
echo "  Testar: curl -X POST ${SERVICE_URL}/orchestrate -H 'Content-Type: application/json' -d @test_payload_example.json"