# ML Orchestrator

Sistema de orquestração modular para funções de Machine Learning, projetado para executar em Google Cloud Run.

## 🎯 Por Que Esta Solução Foi Criada

### Problemas do Sistema Atual

O sistema anterior possui uma função orquestradora em Python (`main.py` com 823 linhas) que gerencia múltiplos fluxos de ML com problemas significativos:

#### 1. **Código Monolítico**
- Arquivo único com 823 linhas misturando múltiplas responsabilidades
- Difícil de manter, testar e debugar
- Alto acoplamento entre componentes

#### 2. **Duplicação Massiva**
- 12+ funções quase idênticas para vagas e profissões
- Copy/paste de lógica por todo o código
- Alterações precisam ser replicadas em múltiplos lugares

#### 3. **Gerenciamento de Paralelismo Problemático**
```python
# Código atual - ThreadPoolExecutor sem controle adequado
with ThreadPoolExecutor(max_workers=2) as executor:
    # Sem tratamento de erros adequado
    # Sem agrupamento inteligente de tarefas
```

#### 4. **Complexidade de Flags**
- Múltiplas flags booleanas confusas controlando o fluxo
- Difícil entender qual combinação ativa qual comportamento
- Propenso a erros de configuração

#### 5. **Observabilidade Limitada**
```python
# Atual - prints simples sem estrutura
print(f"Orchestration: Executing {step_name}...")
```

#### 6. **Tratamento de Erro Fragmentado**
- Try/except espalhados sem padrão
- Difícil rastrear falhas em produção
- Sem contexto adequado nos erros

### ✅ Como Esta Solução Resolve

#### 1. **Arquitetura Modular**
- Separação clara de responsabilidades
- Cada módulo com ~100 linhas focado em uma tarefa
- Fácil de entender, testar e manter

#### 2. **Configuração Centralizada**
- Todos os fluxos definidos em um único lugar
- Adicionar novos fluxos sem modificar código
- Reutilização inteligente de componentes

#### 3. **Paralelismo Otimizado**
- Agrupamento automático de tarefas paralelas
- Tratamento robusto de erros
- Performance melhorada

#### 4. **Logs Estruturados**
```python
# Novo - logs JSON estruturados com contexto
logger.info("step_execution", 
    step_name=step_name, 
    execution_id=id,
    duration=time,
    user_id=user_id
)
```

#### 5. **Benefícios Técnicos**
- **Testabilidade**: Cada componente pode ser testado isoladamente
- **Escalabilidade**: Cloud Run escala melhor que Cloud Functions
- **Manutenibilidade**: Código organizado e documentado
- **Monitoramento**: Métricas detalhadas por step e execução

### 📊 Comparação de Métricas

| Aspecto | Sistema Anterior | Sistema Novo |
|---------|------------------|--------------|
| Linhas de código | ~800 (monolítico) | ~400 (modular) |
| Arquivos | 1 | 12+ especializados |
| Testabilidade | Baixa | Alta |
| Duplicação | Alta | Mínima |
| Observabilidade | Prints básicos | Logs estruturados |
| Manutenção | Difícil | Fácil |
| Escalabilidade | Limitada | Otimizada |

### 🚀 Benefícios para o Negócio

1. **Redução de Bugs** - Código mais limpo e testável
2. **Desenvolvimento Mais Rápido** - Novos fluxos em minutos, não horas
3. **Melhor Performance** - Paralelismo inteligente reduz latência
4. **Economia de Custos** - Cloud Run pode ser mais barato que Cloud Functions
5. **Maior Confiabilidade** - Tratamento de erros robusto e rastreabilidade completa

## Estrutura do Projeto

```
ml_orchestrator/
│
├── config/                 # Configurações e definições de fluxos
│   └── settings.py        # Definições centralizadas dos fluxos ML
│
├── core/                  # Lógica principal de orquestração
│   ├── flow_router.py     # Roteamento de fluxos baseado em parâmetros
│   ├── flow_executor.py   # Execução de fluxos com paralelismo
│   └── step_executor.py   # Execução individual de steps
│
├── handlers/              # Handlers de requisições
│   └── orchestrator_handler.py  # Handler principal
│
├── utils/                 # Utilitários
│   ├── http_client.py     # Cliente HTTP reutilizável
│   └── logger.py          # Sistema de logging estruturado
│
├── tests/                 # Testes unitários e de integração
│
├── deployments/           # Arquivos de deployment
│   └── env-vars.yaml      # Variáveis de ambiente para Cloud Run
│
├── main.py               # Entry point FastAPI
├── Dockerfile            # Containerização
├── requirements.txt      # Dependências Python
└── .gitignore           # Arquivos ignorados pelo Git
```

## Arquitetura

O sistema segue princípios SOLID e clean architecture:

- **Single Responsibility**: Cada módulo tem uma responsabilidade específica
- **Open/Closed**: Extensível para novos fluxos sem modificar código existente
- **Dependency Inversion**: Abstrações não dependem de detalhes
- **Observabilidade**: Logs estruturados e tracing distribuído

## Fluxos Suportados

1. **Update Profile**: Fluxo completo com criação de embeddings
2. **First Login**: Fluxo sem criação de embeddings
3. **Course to Profession**: Apenas sugestão de cursos para profissão
4. **Analysis to Profession**: Análise de skills para profissão
5. **Course to Vacancy**: Apenas sugestão de cursos para vaga
6. **Analysis to Vacancy**: Análise de skills para vaga

## Instalação

```bash
# Clonar o repositório
git clone <repository-url>
cd ml_orchestrator

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## Configuração

1. Copiar o arquivo de exemplo de variáveis de ambiente:
```bash
cp .env.example .env
```

2. Editar `.env` com as URLs das funções ML:
```
DEFAULT_CREATE_USER_EMBEDDINGS_URL=https://...
DEFAULT_MATCH_CANDIDATO_URL=https://...
# ... outras URLs
```

## Execução Local

```bash
# Modo desenvolvimento
uvicorn main:app --reload --port 8080

# Modo produção
gunicorn --bind :8080 --workers 4 --worker-class uvicorn.workers.UvicornWorker main:app
```

## Deploy no Cloud Run

```bash
# Build da imagem
gcloud builds submit --tag gcr.io/[PROJECT-ID]/ml-orchestrator

# Deploy
gcloud run deploy ml-orchestrator \
  --image gcr.io/[PROJECT-ID]/ml-orchestrator \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --timeout 540
```

## Testes

```bash
# Executar todos os testes
pytest

# Testes com cobertura
pytest --cov=ml_orchestrator

# Testes específicos
pytest tests/test_flow_router.py
```

## API

### POST /

Endpoint principal para execução de fluxos.

**Request Body:**
```json
{
  "user_id": "string",
  "session_id": "string",
  "create_user_embedding": boolean,
  "process_profession_orchestrator": boolean,
  "process_vacancy_orchestrator": boolean,
  // ... outros parâmetros
}
```

**Response:**
```json
{
  "execution_id": "uuid",
  "flow_name": "string",
  "user_id": "string",
  "session_id": "string",
  "duration": float,
  "results": [
    {
      "step_name": "string",
      "status": "success|failed|skipped",
      "duration": float,
      "error": "string|null"
    }
  ]
}
```

### GET /health

Health check endpoint.

## Monitoramento

O sistema gera logs estruturados em formato JSON para facilitar análise e monitoramento:

- Eventos de início/fim de execução
- Duração de cada step
- Erros e exceções com stack trace
- IDs de execução únicos para rastreamento

## Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## License

Este projeto está sob a licença MIT.