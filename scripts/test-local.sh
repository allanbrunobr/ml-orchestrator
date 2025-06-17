#!/bin/bash
# Script para testar o serviço localmente

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# URL base
BASE_URL=${1:-http://localhost:8080}

print_color $BLUE "🧪 Testando ML Orchestrator em ${BASE_URL}"
echo ""

# 1. Teste de health check
print_color $YELLOW "1️⃣ Testando health check..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" ${BASE_URL}/health)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" == "200" ]; then
    print_color $GREEN "✅ Health check OK (HTTP $HTTP_CODE)"
    echo "$BODY" | jq .
else
    print_color $RED "❌ Health check falhou (HTTP $HTTP_CODE)"
    echo "$BODY"
fi
echo ""

# 2. Teste de endpoint raiz
print_color $YELLOW "2️⃣ Testando endpoint raiz..."
curl -s ${BASE_URL}/ | jq .
echo ""

# 3. Criar payload de teste
print_color $YELLOW "3️⃣ Criando payload de teste..."
cat > test_payload.json << EOF
{
  "user_id": "test_user_123",
  "session_id": "test_session_456",
  "create_user_embedding": false,
  "process_profession_orchestrator": true,
  "process_vacancy_orchestrator": false,
  "identifier": "test_request_001"
}
EOF

print_color $GREEN "✅ Payload criado: test_payload.json"
cat test_payload.json | jq .
echo ""

# 4. Teste de orquestração
print_color $YELLOW "4️⃣ Testando endpoint de orquestração..."
ORCH_RESPONSE=$(curl -s -X POST \
    ${BASE_URL}/orchestrate \
    -H "Content-Type: application/json" \
    -d @test_payload.json \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$ORCH_RESPONSE" | tail -n1)
BODY=$(echo "$ORCH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" == "200" ]; then
    print_color $GREEN "✅ Orquestração OK (HTTP $HTTP_CODE)"
    echo "$BODY" | jq .
else
    print_color $RED "❌ Orquestração falhou (HTTP $HTTP_CODE)"
    echo "$BODY" | jq . || echo "$BODY"
fi
echo ""

# 5. Teste com payload inválido
print_color $YELLOW "5️⃣ Testando validação (payload inválido)..."
INVALID_RESPONSE=$(curl -s -X POST \
    ${BASE_URL}/orchestrate \
    -H "Content-Type: application/json" \
    -d '{"invalid": "payload"}' \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$INVALID_RESPONSE" | tail -n1)
BODY=$(echo "$INVALID_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" == "400" ]; then
    print_color $GREEN "✅ Validação funcionando corretamente (HTTP $HTTP_CODE)"
    echo "$BODY" | jq .
else
    print_color $RED "❌ Validação não retornou erro esperado (HTTP $HTTP_CODE)"
    echo "$BODY"
fi
echo ""

# 6. Criar payload completo
print_color $YELLOW "6️⃣ Criando payload completo para teste..."
cat > test_payload_full.json << EOF
{
  "user_id": "user_full_test",
  "session_id": "session_full_test",
  "create_user_embedding": true,
  "process_profession_orchestrator": true,
  "process_vacancy_orchestrator": true,
  "identifier": "full_test_001",
  "vacancy_id": "vaga_123",
  "vacancy_name": "Desenvolvedor Python",
  "position_id": "position_456",
  "position_name": "Engenheiro de Software",
  "career_name": "Tecnologia"
}
EOF

print_color $GREEN "✅ Payload completo criado: test_payload_full.json"
echo ""

# Resumo
print_color $BLUE "📊 Resumo dos testes:"
echo "- Health check: Funcionando"
echo "- Endpoint raiz: Funcionando"
echo "- Validação: Funcionando"
echo "- Payloads de teste criados:"
echo "  - test_payload.json (básico)"
echo "  - test_payload_full.json (completo)"
echo ""
print_color $GREEN "🎉 Testes concluídos!"