# 📁 Guia de Arquivos de Configuração

Este guia explica claramente quais arquivos você deve criar e quais deve manter intactos.

## 🎯 Resumo Rápido

```
✅ MANTER (templates)          →  📝 CRIAR (suas configurações)
.env.example                   →  .env
env-vars-template.yaml         →  env-vars.yaml
```

## 📂 Estrutura de Arquivos

```
ml_orchestrator/
│
├── .env.example               ✅ MANTER - Template com estrutura
├── .env                       📝 CRIAR - Suas URLs reais (git ignora)
│
├── .gitignore                 ✅ MANTER - Já configurado para ignorar .env
│
└── deployments/
    ├── env-vars-template.yaml ✅ MANTER - Template YAML
    └── env-vars.yaml          📝 CRIAR - Suas URLs reais (git ignora)
```

## 🔄 Fluxo de Trabalho

### 1️⃣ Para Desenvolvimento Local (.env)

```bash
# PASSO 1: Copiar template
cp .env.example .env

# PASSO 2: Editar com suas URLs
code .env  # ou nano, vim, etc.

# PASSO 3: Verificar se está ignorado
git status  # .env NÃO deve aparecer
```

### 2️⃣ Para Deploy no Cloud Run (YAML)

```bash
# PASSO 1: Copiar template
cp deployments/env-vars-template.yaml deployments/env-vars.yaml

# PASSO 2: Editar com suas URLs
code deployments/env-vars.yaml

# PASSO 3: Verificar se está ignorado
git status  # env-vars.yaml NÃO deve aparecer
```

## ⚠️ O Que NÃO Fazer

```bash
# ❌ ERRADO - Não renomeie templates
mv .env.example .env                           # NÃO!
mv env-vars-template.yaml env-vars.yaml       # NÃO!

# ❌ ERRADO - Não edite templates diretamente
nano .env.example                              # NÃO!
code deployments/env-vars-template.yaml        # NÃO!

# ❌ ERRADO - Não faça commit de arquivos com credenciais
git add .env                                   # NÃO!
git add deployments/env-vars.yaml             # NÃO!
```

## ✅ O Que Fazer

```bash
# ✅ CORRETO - Copie templates
cp .env.example .env
cp deployments/env-vars-template.yaml deployments/env-vars.yaml

# ✅ CORRETO - Edite apenas os copiados
nano .env
nano deployments/env-vars.yaml

# ✅ CORRETO - Verifique antes de commitar
git status | grep -E "\.env$|env-vars\.yaml"  # Não deve retornar nada
```

## 🔍 Verificação de Segurança

### Confirme que os arquivos estão no .gitignore:

```bash
# Deve mostrar as linhas:
cat .gitignore | grep -E "^\.env$|env-vars\.yaml"
```

### Se acidentalmente adicionou ao git:

```bash
# Remover do staging
git rm --cached .env
git rm --cached deployments/env-vars.yaml

# Confirmar que foram removidos
git status
```

## 📋 Checklist Final

Antes de fazer push para o repositório:

- [ ] `.env.example` existe e está intacto
- [ ] `env-vars-template.yaml` existe e está intacto
- [ ] `.env` foi criado mas NÃO aparece no `git status`
- [ ] `env-vars.yaml` foi criado mas NÃO aparece no `git status`
- [ ] Suas URLs reais estão apenas nos arquivos `.env` e `env-vars.yaml`
- [ ] Os templates contêm apenas placeholders genéricos

## 💡 Por Que Essa Separação?

1. **Segurança**: Suas credenciais nunca vão para o repositório
2. **Colaboração**: Outros desenvolvedores sabem o que configurar
3. **Manutenção**: Fácil atualizar templates sem expor segredos
4. **CI/CD**: Deploy automatizado usa arquivos locais seguros

---

**Lembre-se**: Templates são para compartilhar estrutura, não valores reais! 🔒