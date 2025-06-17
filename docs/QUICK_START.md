# 🚀 Quick Start - ML Orchestrator

Guia rápido para subir o ML Orchestrator no Cloud Run em menos de 10 minutos.

## Pré-requisitos
- Google Cloud SDK instalado e configurado
- Docker instalado
- Acesso ao projeto GCP com permissões de Cloud Run

## 1️⃣ Clone e Configure (2 min)

```bash
# Clone o repositório
git clone <REPOSITORY_URL>
cd ml_orchestrator

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com as URLs das suas Cloud Functions
```

## 2️⃣ Teste Local (3 min)

```bash
# Build e execute com Docker
./scripts/build-local.sh

# Em outro terminal, teste
curl http://localhost:8080/health
```

## 3️⃣ Deploy no Cloud Run (5 min)

```bash
# Substitua com seu projeto e região
PROJECT_ID="seu-projeto-id"
REGION="us-east1"

# Deploy automático
./scripts/deploy-with-env.sh $PROJECT_ID $REGION
```

## ✅ Pronto!

O script retornará a URL do serviço. Teste com:

```bash
# Substitua pela URL retornada
SERVICE_URL="https://ml-orchestrator-xxxxx-uc.a.run.app"

# Teste
curl $SERVICE_URL/health
```

## 📝 Payload de Exemplo

```json
{
  "user_id": "user123",
  "session_id": "session456",
  "create_user_embedding": false,
  "process_profession_orchestrator": true,
  "process_vacancy_orchestrator": true
}
```

## 🆘 Problemas?

1. **Erro de autenticação**: `gcloud auth login`
2. **Projeto não configurado**: `gcloud config set project $PROJECT_ID`
3. **APIs não habilitadas**: O script tentará habilitar automaticamente
4. **Logs**: `gcloud run services logs read ml-orchestrator --region $REGION`

Para guia completo, veja [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)