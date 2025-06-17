# ✅ Checklist de Deploy - ML Orchestrator

Use este checklist para garantir que o deploy foi realizado corretamente.

## 📋 Pré-Deploy

- [ ] Todas as URLs das Cloud Functions estão configuradas no `.env`
- [ ] Teste local executado com sucesso (`./scripts/build-local.sh`)
- [ ] Health check local respondendo (`curl http://localhost:8080/health`)
- [ ] Projeto GCP configurado (`gcloud config get-value project`)
- [ ] APIs necessárias habilitadas no GCP
- [ ] Permissões adequadas no GCP

## 🚀 Durante o Deploy

- [ ] Build da imagem Docker concluído sem erros
- [ ] Imagem enviada para o Container Registry
- [ ] Deploy no Cloud Run sem erros
- [ ] URL do serviço retornada

## ✅ Pós-Deploy

### 1. Validação Básica

- [ ] Health check respondendo:
  ```bash
  curl https://SEU-SERVICO.run.app/health
  ```

- [ ] Endpoint raiz respondendo:
  ```bash
  curl https://SEU-SERVICO.run.app/
  ```

- [ ] Documentação acessível:
  ```bash
  # Abra no navegador
  https://SEU-SERVICO.run.app/docs
  ```

### 2. Teste Funcional

- [ ] Requisição de teste bem-sucedida:
  ```bash
  curl -X POST https://SEU-SERVICO.run.app/orchestrate \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "test_user",
      "session_id": "test_session",
      "create_user_embedding": false
    }'
  ```

- [ ] Logs estruturados aparecendo:
  ```bash
  gcloud run services logs read ml-orchestrator --limit 10
  ```

### 3. Verificação de Configuração

- [ ] Variáveis de ambiente configuradas:
  ```bash
  gcloud run services describe ml-orchestrator \
    --region us-east1 \
    --format="value(spec.template.spec.containers[0].env[*].name)"
  ```

- [ ] Recursos adequados (CPU/Memória):
  ```bash
  gcloud run services describe ml-orchestrator \
    --region us-east1 \
    --format="yaml(spec.template.spec.containers[0].resources)"
  ```

- [ ] Timeout configurado (540s):
  ```bash
  gcloud run services describe ml-orchestrator \
    --region us-east1 \
    --format="value(spec.template.spec.timeoutSeconds)"
  ```

### 4. Monitoramento

- [ ] Métricas visíveis no Console do Cloud Run
- [ ] Logs sem erros críticos nas últimas execuções
- [ ] Latência dentro do esperado (< 30s para fluxos completos)
- [ ] Taxa de erro < 5%

### 5. Segurança

- [ ] Serviço acessível publicamente (se desejado)
- [ ] Tokens de autenticação não expostos nos logs
- [ ] Container rodando com usuário não-root

## 🔍 Comandos de Verificação Rápida

```bash
# Status geral do serviço
gcloud run services list --region us-east1

# Detalhes do serviço
gcloud run services describe ml-orchestrator --region us-east1

# Últimas revisões
gcloud run revisions list --service ml-orchestrator --region us-east1

# Tráfego atual
gcloud run services describe ml-orchestrator \
  --region us-east1 \
  --format="value(status.traffic[*].revisionName,status.traffic[*].percent)"
```

## 📊 Métricas de Sucesso

Após 1 hora de operação, verifique:

- [ ] Nenhum restart inesperado do container
- [ ] Uso de memória < 80% do limite
- [ ] Tempo de resposta P95 < 20 segundos
- [ ] Disponibilidade > 99%

## 🚨 Red Flags

Se encontrar algum destes problemas, investigue imediatamente:

- ❌ Health check falhando intermitentemente
- ❌ Logs com muitos erros 5xx
- ❌ Uso de memória constantemente > 90%
- ❌ Timeouts frequentes
- ❌ Container reiniciando repetidamente

## 📝 Documentação do Deploy

Registre as seguintes informações:

```yaml
Deploy Information:
  Date: _______________
  Version/Commit: _______________
  Deployed by: _______________
  Project ID: _______________
  Region: _______________
  Service URL: _______________
  
Configuration:
  Memory: _______________
  CPU: _______________
  Min Instances: _______________
  Max Instances: _______________
  
Validation:
  Health Check: [ ] Pass [ ] Fail
  Test Request: [ ] Pass [ ] Fail
  Performance: [ ] Acceptable [ ] Needs Tuning
```

---

💡 **Dica**: Salve este checklist preenchido para cada deploy importante!