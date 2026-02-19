# 🚀 Como Executar o Pitwall Analytics

Guia rápido para rodar o backend FastAPI e o frontend Dash após todas as mudanças.

---

## 📋 Pré-requisitos

### 1. Ativar o ambiente virtual

```powershell
# Se ainda não estiver ativado
cd C:\Users\ksenh\Documents\projects\pitwall-analytics
.\venv_pitwall_analytics\Scripts\Activate.ps1
```

### 2. Instalar/Atualizar dependências

```powershell
cd pitwall-analytics
pip install -r requirements-new.txt
```

---

## 🎯 Opção 1: Executar Backend e Frontend Separadamente (Recomendado)

### Terminal 1 - Backend FastAPI

```powershell
# Ativar ambiente virtual
.\venv_pitwall_analytics\Scripts\Activate.ps1

# Entrar no diretório do projeto
cd pitwall-analytics

# Executar o backend
python -m backend.app
```

**Backend rodando em:**
- API: http://127.0.0.1:5000
- Documentação interativa: http://127.0.0.1:5000/docs
- ReDoc: http://127.0.0.1:5000/redoc

**Endpoints disponíveis:**
```
GET  /api/health                   - Health check
GET  /api/data/seasons              - Listar temporadas F1
GET  /api/cached/data               - Dados com cache (TTL)
POST /api/cached/refresh            - Forçar atualização do cache
GET  /api/cached/cache/info         - Informações do cache
```

### Terminal 2 - Frontend Dash

```powershell
# Ativar ambiente virtual (em outro terminal)
.\venv_pitwall_analytics\Scripts\Activate.ps1

# Entrar no diretório do projeto
cd pitwall-analytics

# Executar o frontend
python app.py
```

**Frontend rodando em:**
- Interface: http://127.0.0.1:8050

**Páginas disponíveis:**
- Home: http://127.0.0.1:8050/
- Analytics: http://127.0.0.1:8050/analytics
- Live: http://127.0.0.1:8050/live

---

## 🔧 Opção 2: Script de Inicialização (Ambos em Background)

### Windows PowerShell

```powershell
# Terminal 1 - Backend em background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\ksenh\Documents\projects\pitwall-analytics\pitwall-analytics'; .\venv_pitwall_analytics\Scripts\Activate.ps1; python -m backend.app"

# Terminal 2 - Frontend em background  
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\ksenh\Documents\projects\pitwall-analytics\pitwall-analytics'; .\venv_pitwall_analytics\Scripts\Activate.ps1; python app.py"
```

---

## ✅ Verificar se está funcionando

### 1. Testar Backend

```powershell
# Health check
curl http://127.0.0.1:5000/api/health

# Listar temporadas
curl http://127.0.0.1:5000/api/data/seasons

# Testar cache
curl "http://127.0.0.1:5000/api/cached/data?key=f1_seasons"
```

### 2. Testar Frontend

Abrir no navegador: http://127.0.0.1:8050

---

## 📦 Estrutura de Execução

```
┌─────────────────────────────────────────────────────┐
│                   USUÁRIO                           │
│                 (Navegador)                         │
└────────────────────┬────────────────────────────────┘
                     │
                     │ http://127.0.0.1:8050
                     ▼
┌─────────────────────────────────────────────────────┐
│            FRONTEND - Dash                          │
│              app.py (porta 8050)                    │
│                                                     │
│  - Interface gráfica (HTML/CSS)                    │
│  - Visualizações (Plotly)                          │
│  - Páginas: Home, Analytics, Live                  │
└────────────────────┬────────────────────────────────┘
                     │
                     │ HTTP Requests
                     │ http://127.0.0.1:5000/api/*
                     ▼
┌─────────────────────────────────────────────────────┐
│           BACKEND - FastAPI                         │
│         backend/app.py (porta 5000)                 │
│                                                     │
│  - API REST endpoints                              │
│  - Processamento FastF1                            │
│  - Cache SQLite + TTL                              │
│  - Lógica de negócio                               │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │  SQLite Cache  │
            │ data/*.db      │
            └────────────────┘
```

---

## 🛠️ Configuração (.env)

Certifique-se de que o arquivo `.env` existe:

```env
# Backend API
API_HOST=127.0.0.1
API_PORT=5000
DEBUG=True

# CORS (permitir frontend acessar backend)
CORS_ORIGINS=["http://127.0.0.1:8050", "http://localhost:8050"]

# FastF1 Cache
CACHE_DIR=.ff1cache
CACHE_ENABLED=True

# SQLite Cache Database
DB_DIR=data
DB_NAME=pitwall_cache.db
CACHE_TTL_SECONDS=3600
EXTERNAL_API_TIMEOUT=30
```

---

## 🐛 Troubleshooting

### Erro: "Address already in use"

```powershell
# Ver processos usando as portas
netstat -ano | findstr :5000
netstat -ano | findstr :8050

# Matar processo (substitua PID)
taskkill /PID <PID> /F
```

### Erro: "Module not found"

```powershell
# Reinstalar dependências
pip install -r requirements-new.txt
```

### Erro: "Cannot connect to backend"

1. Verificar se backend está rodando: http://127.0.0.1:5000/docs
2. Verificar CORS_ORIGINS no `.env`
3. Ver logs do backend no terminal

### Backend não inicializa o banco de dados

Criar diretório manualmente:
```powershell
mkdir data
```

---

## 📊 Monitoramento

### Logs do Backend
- Inicialização do FastF1 cache
- Inicialização do SQLite cache
- Requisições HTTP
- Erros de API

### Logs do Frontend
- Callbacks do Dash
- Erros de renderização
- Requests para o backend

---

## 🔥 Hot Reload (Development)

Ambos os servidores têm hot reload ativado em modo debug:

- **Backend**: Uvicorn detecta mudanças em arquivos `.py` e recarrega automaticamente
- **Frontend**: Dash detecta mudanças e recarrega a página

---

## 📚 Documentação Adicional

- **Backend API**: http://127.0.0.1:5000/docs (quando rodando)
- **Cache Layer**: [CACHING_LAYER_GUIDE.md](CACHING_LAYER_GUIDE.md)
- **Quick Reference**: [CACHE_QUICK_REFERENCE.md](CACHE_QUICK_REFERENCE.md)

---

## ⚡ Comandos Rápidos

```powershell
# Tudo em um comando (PowerShell)
# Terminal 1
python -m backend.app

# Terminal 2 (novo terminal)
python app.py
```

**Pronto! 🎉**
- Backend: http://127.0.0.1:5000/docs
- Frontend: http://127.0.0.1:8050
