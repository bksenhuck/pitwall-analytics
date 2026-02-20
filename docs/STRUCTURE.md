# 📁 Estrutura do Projeto - Pitwall Analytics

Estrutura atualizada do projeto com organização de pastas seguindo melhores práticas.

## 📂 Estrutura de Diretórios

```
pitwall-analytics/
├── 📄 README.md                      # Documentação principal
├── 📄 pyproject.toml                 # Configuração do projeto
├── 📄 requirements.txt               # Dependências Python
├── 📄 render.yaml                    # Configuração Render.com
├── 📄 Procfile                       # Configuração Heroku
├── 📄 start.ps1                      # Script de início (PowerShell)
├── 📄 start-production.ps1           # Script de produção
├── 📄 run.py                         # Entry point alternativo
├── 📄 main.py                        # Entry point principal
├── 📄 app.py                         # Aplicação Dash legada
│
├── 📁 docs/                          # 📚 Toda a documentação
│   ├── README.md                     # Índice da documentação
│   ├── AUTO_CACHE_GUIDE.md          # ⭐ Guia de cache automático
│   ├── MANUAL_CACHE_CONTROL.md      # Controle manual do cache
│   ├── ARCHITECTURE.md              # Arquitetura do sistema
│   ├── CACHING_LAYER_GUIDE.md       # Guia da camada de caching
│   ├── CACHE_QUICK_REFERENCE.md     # Referência rápida
│   ├── BACKEND_COMPARISON.md        # Flask vs FastAPI
│   ├── FASTAPI_BACKEND_REFERENCE.md # Referência FastAPI
│   ├── FLASK_TO_FASTAPI_MIGRATION.md# Migração
│   ├── DEPLOY.md                    # Deploy para produção
│   ├── QUICKSTART.md                # Início rápido
│   ├── COMO_EXECUTAR.md             # Como executar (PT)
│   ├── MODOS_EXECUCAO.md            # Modos de execução (PT)
│   ├── LEIA-ME.md                   # README em português
│   └── README-NEW.md                # README alternativo
│
├── 📁 scripts/                       # 🛠️ Ferramentas CLI
│   ├── __init__.py
│   ├── README.md                     # Documentação dos scripts
│   ├── auto_populate_cache.py       # ⭐ Auto-população
│   ├── populate_cache.py            # População manual
│   └── example_data_access.py       # Exemplos de acesso
│
├── 📁 backend/                       # 🔧 Backend API
│   ├── __init__.py
│   ├── app.py                        # Aplicação FastAPI/Flask
│   ├── config.py                     # Configurações
│   ├── api/                          # Endpoints da API
│   │   ├── __init__.py
│   │   ├── data.py
│   │   └── health.py
│   ├── db/                           # Camada de banco de dados
│   │   ├── __init__.py
│   │   └── session.py               # Gerenciamento SQLite
│   ├── models/                       # Modelos de dados
│   │   ├── __init__.py
│   │   └── data_model.py
│   ├── repositories/                 # Camada de dados
│   │   ├── __init__.py
│   │   └── data_repository.py
│   ├── routes/                       # Rotas HTTP
│   │   ├── __init__.py
│   │   └── data.py
│   └── services/                     # Lógica de negócio
│       ├── __init__.py
│       ├── external_api.py          # Interface FastF1
│       ├── f1_data_service.py       # Serviço de dados F1 (cache-only)
│       ├── cache_service.py         # FastF1 cache
│       └── async_api_client.py
│
├── 📁 frontend/                      # 🎨 Frontend Dash
│   ├── __init__.py
│   ├── app.py                        # Aplicação Dash
│   ├── config.py                     # Configurações
│   ├── assets/                       # CSS, JS, imagens
│   │   └── style.css
│   ├── callbacks/                    # Callbacks Dash
│   │   └── __init__.py
│   ├── components/                   # Componentes reutilizáveis
│   │   ├── __init__.py
│   │   ├── charts.py
│   │   └── navigation.py
│   └── pages/                        # Páginas da aplicação
│       ├── __init__.py
│       ├── home.py
│       ├── analytics.py
│       └── live.py
│
├── 📁 shared/                        # 📦 Código compartilhado
│   ├── __init__.py
│   └── utils.py
│
├── 📁 data/                          # 💾 Dados e cache
│   └── pitwall_cache.db             # Cache SQLite
│
├── 📁 static/                        # 🖼️ Arquivos estáticos
│   ├── __init__.py
│   └── images/
│       ├── __init__.py
│       └── 2026/
│
├── 📁 pages/                         # 📄 Páginas legadas (Dash)
│   ├── __init__.py
│   ├── home.py
│   ├── analytics.py
│   └── live.py
│
├── 📁 assets/                        # 🎨 Assets legados
│   └── style.css
│
└── 📁 venv_pitwall_analytics/       # 🐍 Ambiente virtual Python
    └── ...
```

## 📋 Convenções

### Nomenclatura

#### Arquivos Python
- **lowercase_with_underscores.py** - Módulos Python padrão
- **__init__.py** - Inicializadores de pacotes

#### Documentação
- **UPPERCASE.md** - Documentos principais (em `docs/`)
- **README.md** - Índices e documentação de pasta

#### Scripts
- **verbo_substantivo.py** - Scripts CLI (em `scripts/`)
- Exemplo: `auto_populate_cache.py`, `example_data_access.py`

### Organização de Pastas

#### 🔵 Backend (`backend/`)
Camadas separadas seguindo **Clean Architecture**:
- `api/` - Controllers/Endpoints
- `services/` - Lógica de negócio
- `repositories/` - Acesso a dados
- `models/` - Estruturas de dados
- `db/` - Configuração de banco

#### 🟢 Frontend (`frontend/`)
Estrutura modular Dash:
- `pages/` - Páginas da aplicação
- `components/` - Componentes reutilizáveis
- `callbacks/` - Interatividade
- `assets/` - CSS, JS, imagens

#### 🟡 Scripts (`scripts/`)
Ferramentas CLI independentes:
- Cada script é autocontido
- Ajusta `sys.path` para importar `backend/`
- Documentação em `scripts/README.md`

#### 🟣 Docs (`docs/`)
Toda a documentação centralizada:
- Índice em `docs/README.md`
- Markdown com emojis para clareza
- Links relativos entre documentos

## 🚀 Fluxo de Dados

```
┌─────────────────────────────────────────────────┐
│  Scripts CLI (scripts/)                         │
│  - Populam cache                                │
│  - Ferramentas de admin                         │
└──────────────┬──────────────────────────────────┘
               ↓
        ┌──────────────┐
        │   FastF1     │
        │   API        │
        └──────┬───────┘
               ↓
┌───────────────────────────────────────────────┐
│  Backend (backend/)                           │
│  ┌─────────────────────────────────────────┐  │
│  │ services/     → Lógica de negócio       │  │
│  │ repositories/ → Acesso SQLite           │  │
│  │ api/         → Endpoints REST           │  │
│  └─────────────────────────────────────────┘  │
└──────────────┬────────────────────────────────┘
               ↓
        ┌──────────────┐
        │  SQLite DB   │
        │  (data/)     │
        └──────┬───────┘
               ↑
┌──────────────┴────────────────────────────────┐
│  Frontend (frontend/)                         │
│  ┌─────────────────────────────────────────┐  │
│  │ pages/      → Páginas Dash              │  │
│  │ components/ → Gráficos e UI             │  │
│  │ callbacks/  → Interatividade            │  │
│  └─────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘
               ↓
        [Usuário Final]
```

## 📦 Dependências por Camada

### Backend
- **FastAPI/Flask** - Framework web
- **SQLite3** - Banco de dados
- **FastF1** - Dados de F1
- **Pandas** - Manipulação de dados
- **httpx** - Cliente HTTP assíncrono

### Frontend
- **Dash** - Framework web
- **Plotly** - Visualizações
- **Pandas** - Processamento de dados

### Scripts
- **asyncio** - Operações assíncronas
- **argparse** - CLI arguments
- Importam de `backend/` conforme necessário

## 🎯 Pontos de Entrada

### Desenvolvimento
```bash
# Executar tudo (backend + frontend)
python main.py
# ou
.\start.ps1

# Apenas backend
python -m backend.app

# Apenas frontend
python -m frontend.app
```

### Produção
```bash
# Render.com / Heroku
# Usa Procfile automaticamente

# Manual
.\start-production.ps1
```

### Scripts
```bash
# Auto-população de cache
python scripts/auto_populate_cache.py --season 2024

# População manual
python scripts/populate_cache.py f1_seasons

# Exemplos
python scripts/example_data_access.py
```

## 📊 Tamanhos Aproximados

| Componente | Tamanho | Observações |
|------------|---------|-------------|
| **Cache SQLite** | ~500MB-1GB/temporada | Cresce com dados |
| **Código fonte** | ~5MB | Sem dependências |
| **Documentação** | ~500KB | Markdown |
| **Dependências** | ~500MB | venv completo |

## 🔍 Navegação Rápida

| Preciso... | Vá para... |
|------------|------------|
| **Entender arquitetura** | [docs/ARCHITECTURE.md](ARCHITECTURE.md) |
| **Carregar dados** | [scripts/auto_populate_cache.py](../scripts/auto_populate_cache.py) |
| **Modificar backend** | [backend/](../backend/) |
| **Modificar frontend** | [frontend/](../frontend/) |
| **Ver documentação** | [docs/](.) |
| **Criar script novo** | [scripts/](../scripts/) |

## 🤝 Contribuindo

Ao adicionar novos componentes:

1. **Backend**: Siga padrão de camadas (api → service → repository)
2. **Frontend**: Crie componentes reutilizáveis em `components/`
3. **Scripts**: Adicione em `scripts/` com documentação
4. **Docs**: Adicione em `docs/` e atualize índice

## 💡 Boas Práticas

### Imports
```python
# Correto - Absoluto
from backend.services.external_api import ExternalAPIService

# Evitar - Relativo demais
from ...services.external_api import ExternalAPIService
```

### Estrutura de Arquivos
- 1 classe/função principal por arquivo
- `__init__.py` para tornar pastas em pacotes
- Nomes descritivos e consistentes

### Documentação
- Docstrings em todas as funções públicas
- README.md em cada pasta importante
- Exemplos de uso quando relevante

---

Última atualização: Fevereiro 2026
