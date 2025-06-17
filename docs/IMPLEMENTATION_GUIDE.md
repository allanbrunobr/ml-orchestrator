# Guia de Implementação - ML Orchestrator no Google Cloud Run

Este guia detalha o processo completo para implantar o ML Orchestrator no Google Cloud Run, desde a preparação do ambiente até o deploy em produção.

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Pré-requisitos](#pré-requisitos)
3. [Preparação do Ambiente](#preparação-do-ambiente)
4. [Configuração](#configuração)
5. [Teste Local](#teste-local)
6. [Deploy no Cloud Run](#deploy-no-cloud-run)
7. [Validação e Monitoramento](#validação-e-monitoramento)
8. [Troubleshooting](#troubleshooting)
9. [Manutenção](#manutenção)

---

## 🎯 Visão Geral

O ML Orchestrator é um serviço de orquestração que coordena chamadas para múltiplas funções de Machine Learning, substituindo uma Cloud Function monolítica por uma arquitetura modular e escalável no Cloud Run.

### Arquitetura

```
Cliente → Cloud Run (Orquestrador) → Cloud Functions/Cloud Run (Funções ML)
                                   ↘ Webhook (Opcional)
```

### Benefícios
- ✅ Código modular e manutenível
- ✅ Logs estruturados para melhor observabilidade
- ✅ Paralelismo otimizado
- ✅ Configuração flexível
- ✅ Melhor escalabilidade

---

## 🔧 Pré-requisitos

### 1. Ferramentas Necessárias

```bash
# Google Cloud SDK
gcloud --version  # >= 400.0.0

# Docker
docker --version  # >= 20.10.0

# Python (para desenvolvimento local)
python --version  # >= 3.11

# Git
git --version
```

### 2. Instalação do Google Cloud SDK

```bash
# macOS
brew install google-cloud-sdk

# Linux/WSL
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Inicializar
gcloud init
```

### 3. Permissões Necessárias no GCP

O usuário ou service account precisa das seguintes permissões:
- `Cloud Run Admin`
- `Cloud Build Editor`
- `Storage Admin` (para armazenar imagens)
- `Service Account User`

---

## 🚀 Preparação do Ambiente

### 1. Clone o Repositório

```bash
# Clone o repositório (substitua pela URL real)
git clone <REPOSITORY_URL>
cd ml_orchestrator
```

### 2. Estrutura do Projeto

```
ml_orchestrator/
├── config/                 # Configurações e definições de fluxos
├── core/                   # Lógica de orquestração
├── handlers/               # Handlers de requisições
├── utils/                  # Utilitários (logger, http client)
├── scripts/                # Scripts de deploy e teste
├── deployments/            # Arquivos de configuração para deploy
├── main.py                 # Entry point FastAPI
├── Dockerfile              # Configuração do container
├── requirements.txt        # Dependências Python
└── .env.example           # Template de variáveis de ambiente
```

### 3. Configure o Projeto GCP

```bash
# Defina o projeto
export PROJECT_ID="seu-projeto-id"
gcloud config set project $PROJECT_ID

# Habilite as APIs necessárias
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com
```

---

## ⚙️ Configuração

### 1. Variáveis de Ambiente

O sistema precisa das URLs das funções ML. Há duas opções de configuração:

#### 📁 Estrutura dos Arquivos de Configuração

```
ml_orchestrator/
├── .env.example                    # ✅ TEMPLATE - NÃO RENOMEAR, apenas referência
├── .env                           # 📝 VOCÊ CRIA este arquivo (já está no .gitignore)
└── deployments/
    ├── env-vars-template.yaml     # ✅ TEMPLATE - NÃO RENOMEAR, apenas referência
    └── env-vars.yaml             # 📝 VOCÊ CRIA este arquivo (já está no .gitignore)
```

#### ⚠️ IMPORTANTE: Entenda os Arquivos

| Arquivo | O que fazer | Descrição |
|---------|-------------|-----------|
| `.env.example` | ✅ **NÃO RENOMEAR** | Template de exemplo com estrutura das variáveis |
| `.env` | 📝 **CRIAR copiando .env.example** | Suas URLs reais (NÃO fazer commit) |
| `env-vars-template.yaml` | ✅ **NÃO RENOMEAR** | Template YAML com placeholders |
| `env-vars.yaml` | 📝 **CRIAR copiando o template** | Suas URLs reais (NÃO fazer commit) |

#### Opção A: Usando arquivo .env (RECOMENDADO)

```bash
# PASSO 1: Copie o template para criar SEU arquivo .env
cp .env.example .env

# PASSO 2: Edite o arquivo .env com SUAS URLs reais
nano .env   # ou use seu editor preferido: code .env

# ⚠️ LEMBRE-SE: O arquivo .env está no .gitignore - NUNCA faça commit dele!
```

**Como ficará seu `.env` após edição:**
```env
# Substitua estas URLs pelas suas URLs reais
DEFAULT_CREATE_USER_EMBEDDINGS_URL=https://us-east1-prj-dev-cce-cni1.cloudfunctions.net/func-dev-cce-create-user-embeddings
DEFAULT_MATCH_CANDIDATO_URL=https://func-dev-cce-vcc-match-candidato-838414025421.us-east1.run.app
DEFAULT_MATCH_ANALYSIS_USER_VACANCY_URL=https://us-east1-prj-dev-cce-cni1.cloudfunctions.net/func-dev-cce-senai-match-analysis-user-vacancy
# ... todas as outras URLs ...
```

#### Opção B: Usando arquivo YAML

```bash
# PASSO 1: Copie o template para criar SEU arquivo env-vars.yaml
cp deployments/env-vars-template.yaml deployments/env-vars.yaml

# PASSO 2: Edite com suas URLs reais
nano deployments/env-vars.yaml

# ⚠️ LEMBRE-SE: O arquivo env-vars.yaml está no .gitignore - NUNCA faça commit dele!
```

#### 🎯 Fluxo Correto de Configuração

1. **MANTENHA** os arquivos template intactos (`.env.example` e `env-vars-template.yaml`)
2. **COPIE** o template apropriado para criar seu arquivo de configuração
3. **EDITE** apenas o arquivo copiado com suas URLs reais
4. **VERIFIQUE** antes de commitar:

```bash
# Este comando não deve mostrar nada (arquivos estão ignorados)
git status | grep -E "\.env$|env-vars\.yaml"

# Se aparecer algum desses arquivos, NÃO faça commit!
# Adicione ao .gitignore se necessário:
echo ".env" >> .gitignore
echo "deployments/env-vars.yaml" >> .gitignore
```

#### 💡 Dica de Segurança

```bash
# Para garantir que nunca comitará credenciais acidentalmente:
git config --local core.excludesfile .gitignore

# Verifique sempre antes de push:
git diff --staged --name-only | grep -E "\.env|env-vars\.yaml"
```

### 2. Validação das URLs

Verifique se todas as funções ML estão acessíveis:

```bash
# Teste uma URL
curl -X POST https://sua-funcao.cloudfunctions.net/health \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

---

## 🧪 Teste Local

### 1. Com Docker (Recomendado)

```bash
# Build e execute localmente
./scripts/build-local.sh

# Em outro terminal, teste o serviço
./scripts/test-local.sh
```

### 2. Com Python Direto

```bash
# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt

# Execute
python main.py

# Acesse: http://localhost:8080/docs
```

### 3. Teste de Requisição

```bash
# Crie um payload de teste
cat > test_payload.json << EOF
{
  "user_id": "test_user_123",
  "session_id": "test_session_456",
  "create_user_embedding": false,
  "process_profession_orchestrator": true,
  "process_vacancy_orchestrator": true
}
EOF

# Teste o endpoint
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d @test_payload.json | jq .
```

---

## ☁️ Deploy no Cloud Run

### 1. Deploy Automático (Recomendado)

```bash
# Usando .env
./scripts/deploy-with-env.sh $PROJECT_ID us-east1 ml-orchestrator

# Ou usando env-vars.yaml
./scripts/deploy.sh $PROJECT_ID us-east1 ml-orchestrator
```

### 2. Deploy Manual Passo a Passo

#### Passo 1: Build da Imagem

```bash
# Build local e push
docker build -t gcr.io/$PROJECT_ID/ml-orchestrator .
docker push gcr.io/$PROJECT_ID/ml-orchestrator

# Ou use Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/ml-orchestrator
```

#### Passo 2: Deploy no Cloud Run

```bash
# Deploy com arquivo de variáveis
gcloud run deploy ml-orchestrator \
    --image gcr.io/$PROJECT_ID/ml-orchestrator \
    --platform managed \
    --region us-east1 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 540 \
    --max-instances 100 \
    --min-instances 1 \
    --allow-unauthenticated \
    --env-vars-file deployments/env-vars.yaml \
    --port 8080
```

### 3. Configurações Importantes

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `--memory` | 2Gi | Memória suficiente para processamento paralelo |
| `--cpu` | 2 | CPUs para melhor performance |
| `--timeout` | 540 | 9 minutos (máximo para orquestração) |
| `--min-instances` | 1 | Evita cold start |
| `--max-instances` | 100 | Escala conforme demanda |

---

## ✅ Validação e Monitoramento

### 1. Validação do Deploy

```bash
# Obtenha a URL do serviço
SERVICE_URL=$(gcloud run services describe ml-orchestrator \
    --region us-east1 \
    --format 'value(status.url)')

# Teste o health check
curl $SERVICE_URL/health | jq .

# Teste uma requisição completa
curl -X POST $SERVICE_URL/orchestrate \
    -H "Content-Type: application/json" \
    -d @test_payload.json | jq .
```

### 2. Monitoramento

#### Logs em Tempo Real

```bash
# Stream de logs
gcloud run services logs tail ml-orchestrator --region us-east1

# Últimos 50 logs
gcloud run services logs read ml-orchestrator --region us-east1 --limit 50
```

#### Métricas no Console

1. Acesse: https://console.cloud.google.com/run
2. Selecione seu serviço
3. Visualize:
   - Requisições por segundo
   - Latência
   - Taxa de erro
   - Uso de CPU/Memória

### 3. Alertas Recomendados

```bash
# Criar alerta para taxa de erro > 5%
gcloud alpha monitoring policies create \
    --notification-channels=SEU_CHANNEL_ID \
    --display-name="ML Orchestrator - High Error Rate" \
    --condition="rate(logging.googleapis.com/user/ml-orchestrator-errors[1m]) > 0.05"
```

---

## 🔍 Troubleshooting

### Problema 1: Health Check Falhando

**Sintomas**: Deploy bem-sucedido mas health check retorna erro

**Soluções**:
```bash
# Verifique os logs
gcloud run services logs read ml-orchestrator --region us-east1

# Verifique variáveis de ambiente
gcloud run services describe ml-orchestrator --region us-east1 --format="value(spec.template.spec.containers[0].env[*])"

# Teste localmente
./scripts/build-local.sh
```

### Problema 2: Timeout nas Requisições

**Sintomas**: Requisições retornam 504 Gateway Timeout

**Soluções**:
1. Verifique o timeout do Cloud Run (deve ser 540s)
2. Verifique se as funções ML estão respondendo
3. Monitore logs para identificar gargalos

### Problema 3: Erros de Autenticação

**Sintomas**: 401/403 ao chamar funções ML

**Soluções**:
```bash
# Verifique se os tokens estão configurados
grep -E "token|TOKEN" .env

# Teste autenticação diretamente
curl -H "Authorization: Bearer SEU_TOKEN" https://sua-funcao-url/
```

### Logs Estruturados

Os logs são em formato JSON. Para filtrar:

```bash
# Apenas erros
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit 50

# Por execution_id específico
gcloud logging read 'jsonPayload.execution_id="uuid-aqui"' --limit 100
```

---

## 🔧 Manutenção

### 1. Atualização do Serviço

```bash
# Após mudanças no código
git pull origin main
./scripts/deploy-with-env.sh $PROJECT_ID us-east1
```

### 2. Rollback

```bash
# Listar revisões
gcloud run revisions list --service ml-orchestrator --region us-east1

# Rollback para revisão anterior
gcloud run services update-traffic ml-orchestrator \
    --to-revisions ml-orchestrator-00002-abc=100 \
    --region us-east1
```

### 3. Backup de Configuração

```bash
# Salvar configuração atual
gcloud run services export ml-orchestrator \
    --region us-east1 \
    --format export > backup-config.yaml

# Restaurar se necessário
gcloud run services replace backup-config.yaml --region us-east1
```

### 4. Monitoramento de Custos

```bash
# Ver custos do Cloud Run
gcloud billing projects describe $PROJECT_ID

# Configurar orçamento
gcloud billing budgets create \
    --billing-account=SEU_BILLING_ACCOUNT \
    --display-name="ML Orchestrator Budget" \
    --budget-amount=100 \
    --threshold-rule=percent=90
```

---

## 📚 Recursos Adicionais

### Documentação
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/tips)

### Scripts Úteis

Todos os scripts estão em `scripts/`:
- `deploy-with-env.sh` - Deploy principal
- `build-local.sh` - Build e teste local
- `test-local.sh` - Suite de testes
- `env-to-cloudrun.sh` - Conversor de .env para YAML

### Suporte

Para problemas:
1. Verifique os logs detalhados
2. Consulte a seção de Troubleshooting
3. Abra uma issue no repositório

---

## 🎉 Conclusão

Com este guia, você deve conseguir implantar o ML Orchestrator no Cloud Run com sucesso. O sistema oferece melhor manutenibilidade, observabilidade e escalabilidade comparado à solução anterior.

**Lembre-se**: 
- Sempre teste localmente antes do deploy
- Monitore os logs após o deploy
- Mantenha as variáveis de ambiente atualizadas
- Faça backups antes de grandes mudanças

Boa sorte com a implementação! 🚀