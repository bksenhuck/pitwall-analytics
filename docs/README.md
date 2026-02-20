# 📚 Documentação - Pitwall Analytics

Documentação completa do projeto organizada por tópicos.

## 📖 Índice

### 🚀 Início Rápido
- **[QUICKSTART.md](QUICKSTART.md)** - Guia rápido de início
- **[COMO_EXECUTAR.md](COMO_EXECUTAR.md)** - Como executar o projeto
- **[MODOS_EXECUCAO.md](MODOS_EXECUCAO.md)** - Diferentes modos de execução
- **[LEIA-ME.md](LEIA-ME.md)** - README em português

### 🗄️ Sistema de Cache
- **[AUTO_CACHE_GUIDE.md](AUTO_CACHE_GUIDE.md)** - ⭐ Guia completo do sistema de auto-população
- **[MANUAL_CACHE_CONTROL.md](MANUAL_CACHE_CONTROL.md)** - Controle manual do cache SQLite
- **[CACHING_LAYER_GUIDE.md](CACHING_LAYER_GUIDE.md)** - Guia da camada de cache
- **[CACHE_QUICK_REFERENCE.md](CACHE_QUICK_REFERENCE.md)** - Referência rápida do cache

### 🏗️ Arquitetura
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitetura do sistema
- **[STRUCTURE.md](STRUCTURE.md)** - 📁 Estrutura de pastas detalhada
- **[BACKEND_COMPARISON.md](BACKEND_COMPARISON.md)** - Comparação Flask vs FastAPI
- **[FASTAPI_BACKEND_REFERENCE.md](FASTAPI_BACKEND_REFERENCE.md)** - Referência do backend FastAPI
- **[FLASK_TO_FASTAPI_MIGRATION.md](FLASK_TO_FASTAPI_MIGRATION.md)** - Guia de migração

### 🚢 Deploy
- **[DEPLOY.md](DEPLOY.md)** - Guia de deploy para produção

### 📝 Outros
- **[README-NEW.md](README-NEW.md)** - README alternativo
- **[CHANGELOG.md](CHANGELOG.md)** - Histórico de mudanças do projeto

---

## 🎯 Começando

### Primeira vez usando o projeto?

1. Leia o **[QUICKSTART.md](QUICKSTART.md)**
2. Configure o ambiente com **[COMO_EXECUTAR.md](COMO_EXECUTAR.md)**
3. Popule o cache com **[AUTO_CACHE_GUIDE.md](AUTO_CACHE_GUIDE.md)**

### Desenvolvendo?

1. Entenda a **[ARCHITECTURE.md](ARCHITECTURE.md)** e **[STRUCTURE.md](STRUCTURE.md)**
2. Use **[MANUAL_CACHE_CONTROL.md](MANUAL_CACHE_CONTROL.md)** para gerenciar dados
3. Veja **[../scripts/README.md](../scripts/README.md)** para ferramentas CLI

### Deploy para produção?

1. Leia **[DEPLOY.md](DEPLOY.md)**
2. Configure o cache conforme **[CACHING_LAYER_GUIDE.md](CACHING_LAYER_GUIDE.md)**

---

## 🗂️ Estrutura do Projeto

```
pitwall-analytics/
├── README.md                   # Documentação principal
├── docs/                       # 👈 Você está aqui
│   ├── README.md              # Este arquivo
│   ├── AUTO_CACHE_GUIDE.md    # Sistema automático de cache ⭐
│   ├── MANUAL_CACHE_CONTROL.md
│   ├── ARCHITECTURE.md
│   └── ...
├── scripts/                    # Scripts CLI e ferramentas
│   ├── README.md
│   ├── auto_populate_cache.py
│   └── ...
├── backend/                    # Backend API (Flask/FastAPI)
├── frontend/                   # Frontend (Dash)
├── data/                       # Cache SQLite
└── ...
```

---

## 🔍 Busca Rápida

### Como...

| Tarefa | Documento |
|--------|-----------|
| **Carregar dados de F1?** | [AUTO_CACHE_GUIDE.md](AUTO_CACHE_GUIDE.md) |
| **Executar o projeto?** | [COMO_EXECUTAR.md](COMO_EXECUTAR.md) |
| **Entender a arquitetura?** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Ver estrutura de pastas?** | [STRUCTURE.md](STRUCTURE.md) |
| **Fazer deploy?** | [DEPLOY.md](DEPLOY.md) |
| **Controlar o cache manualmente?** | [MANUAL_CACHE_CONTROL.md](MANUAL_CACHE_CONTROL.md) |
| **Migrar para FastAPI?** | [FLASK_TO_FASTAPI_MIGRATION.md](FLASK_TO_FASTAPI_MIGRATION.md) |
| **Ver referência rápida?** | [CACHE_QUICK_REFERENCE.md](CACHE_QUICK_REFERENCE.md) |

---

## 📱 Documentos por Idioma

- **Português**: [LEIA-ME.md](LEIA-ME.md), [COMO_EXECUTAR.md](COMO_EXECUTAR.md), [MODOS_EXECUCAO.md](MODOS_EXECUCAO.md)
- **English**: Most other documents

---

## 🤝 Contribuindo

Ao adicionar nova documentação:

1. Coloque em `docs/` com nome descritivo em UPPERCASE
2. Adicione ao índice acima
3. Use Markdown com emojis para seções
4. Inclua exemplos de código quando relevante
5. Mantenha links relativos funcionando

---

## 💡 Convenções

- **UPPERCASE.md** - Documentos principais
- **lowercase.md** - Documentos gerados/temporários
- Links internos sempre relativos
- Exemplos de código sempre testados

---

Última atualização: Fevereiro 2026
