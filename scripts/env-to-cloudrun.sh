#!/bin/bash
# Script para converter arquivo .env para formato Cloud Run

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Verificar parâmetros
if [ $# -lt 1 ]; then
    print_color $YELLOW "Uso: $0 <arquivo.env> [arquivo-saida.yaml]"
    echo "Exemplo: $0 .env deployments/env-vars.yaml"
    echo ""
    echo "Converte arquivo .env para formato YAML do Cloud Run"
    exit 1
fi

INPUT_FILE=$1
OUTPUT_FILE=${2:-"deployments/env-vars.yaml"}

# Verificar se arquivo existe
if [ ! -f "$INPUT_FILE" ]; then
    print_color $RED "❌ Arquivo $INPUT_FILE não encontrado!"
    exit 1
fi

print_color $YELLOW "📋 Convertendo $INPUT_FILE para $OUTPUT_FILE..."

# Criar cabeçalho
cat > "$OUTPUT_FILE" << EOF
# Variáveis de ambiente geradas automaticamente de $INPUT_FILE
# Gerado em: $(date)
# NÃO edite este arquivo diretamente se foi gerado automaticamente

EOF

# Converter .env para YAML
while IFS= read -r line; do
    # Ignorar linhas vazias e comentários
    if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    # Processar linha válida
    if [[ "$line" =~ ^([A-Z_]+)=(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        
        # Remover aspas se existirem
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"
        
        # Escrever no formato YAML
        echo "${key}: \"${value}\"" >> "$OUTPUT_FILE"
    fi
done < "$INPUT_FILE"

print_color $GREEN "✅ Conversão concluída!"
print_color $YELLOW "📄 Arquivo gerado: $OUTPUT_FILE"

# Mostrar preview
echo ""
print_color $YELLOW "Preview das primeiras 10 linhas:"
head -n 15 "$OUTPUT_FILE"