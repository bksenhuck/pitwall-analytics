# 🏁 Pitwall Analytics - Guia Rápido

Sistema de análise de dados de Fórmula 1 com backend FastAPI e frontend Dash.

---

## 🚀 Iniciar o Sistema

### Opção 1: Script Automático (Mais Fácil)

```powershell
.\start.ps1
```

Isso abrirá 2 janelas:
- **Backend** (porta 5000)
- **Frontend** (porta 8050)

### Opção 2: Manual (Recomendado para desenvolvimento)

**Terminal 1 - Backend:**
```powershell
python -m backend.app
```

**Terminal 2 - Frontend:**
```powershell
python app.py
```

---

## 🌐 Acessar o Sistema

Após iniciar, acesse:

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **Frontend** | http://127.0.0.1:8050 | Interface principal |
| **Backend API** | http://127.0.0.1:5000 | API REST |
| **API Docs** | http://127.0.0.1:5000/docs | Documentação interativa |

---

## 📁 Estrutura do Projeto

```
pitwall-analytics/
│
├── backend/                 # Backend FastAPI
│   ├── app.py              # Aplicação principal
│   ├── api/                # Endpoints da API
│   ├── db/                 # Conexão SQLite
│   ├── models/             # Models Pydantic
│   ├── repositories/       # Camada de dados
│   ├── routes/             # Rotas de cache
│   └── services/           # Lógica de negócio
│
├── frontend/               # Frontend Dash (futuro)
│
├── pages/                  # Páginas Dash (atual)
│   ├── home.py
│   ├── analytics.py
│   └── live.py
│
├── app.py                  # Frontend Dash principal
├── data_loader.py          # Carregamento de dados F1
├── charts.py               # Gráficos Plotly
│
├── .env                    # Configurações (portas, cache, etc)
├── requirements-new.txt    # Dependências Python
│
├── COMO_EXECUTAR.md       # Guia detalhado (este arquivo)
├── start.ps1               # Script de inicialização
│
└── data/                   # Banco de dados SQLite (gerado automaticamente)
    └── pitwall_cache.db
```

---

## 🔧 Configuração

### Arquivo `.env`

```env
# Backend
API_HOST=127.0.0.1
API_PORT=5000
DEBUG=True

# Cache SQLite
CACHE_TTL_SECONDS=3600      # 1 hora
DB_DIR=data
DB_NAME=pitwall_cache.db
```

---

## 📊 Funcionalidades

### Backend (FastAPI)

✅ API REST com documentação automática  
✅ Cache SQLite com TTL (Time-To-Live)  
✅ Integração com FastF1  
✅ Suporte assíncrono (async/await)  
✅ CORS configurado para o frontend  

**Principais Endpoints:**

```bash
GET  /api/health                    # Status da API
GET  /api/data/seasons              # Temporadas F1
GET  /api/cached/data?key=X         # Dados com cache
POST /api/cached/refresh?key=X      # Atualizar cache
GET  /api/cached/cache/info?key=X   # Info do cache
```

### Frontend (Dash)

✅ Interface web responsiva  
✅ Visualizações interativas (Plotly)  
✅ Múltiplas páginas (Home, Analytics, Live)  
✅ Integração com backend via HTTP  

---

## 🧪 Testar o Sistema

### 1. Backend Health Check

```powershell
curl http://127.0.0.1:5000/api/health
```

### 2. API Docs (Navegador)

http://127.0.0.1:5000/docs

### 3. Frontend (Navegador)

http://127.0.0.1:8050

---

## 🛑 Parar o Sistema

- **Script automático**: Feche as janelas do PowerShell
- **Manual**: Pressione `Ctrl + C` em cada terminal

---

## 📚 Documentação Adicional

- **[COMO_EXECUTAR.md](COMO_EXECUTAR.md)** - Guia completo de execução
- **[CACHING_LAYER_GUIDE.md](CACHING_LAYER_GUIDE.md)** - Sistema de cache
- **[CACHE_QUICK_REFERENCE.md](CACHE_QUICK_REFERENCE.md)** - Referência rápida

---

## 🐛 Problemas Comuns

### "Address already in use"

```powershell
# Ver processos nas portas
netstat -ano | findstr :5000
netstat -ano | findstr :8050

# Matar processo
taskkill /PID <PID> /F
```

### "Module not found"

```powershell
pip install -r requirements-new.txt
```

### Backend não conecta

1. Verificar se está rodando: http://127.0.0.1:5000/docs
2. Verificar `.env` (CORS_ORIGINS)
3. Ver logs no terminal

---

## 💡 Dicas

- **Hot Reload**: Mudanças no código recarregam automaticamente (em modo debug)
- **Logs**: Acompanhe os terminais para ver requests e erros
- **Cache**: Primeiro acesso é lento (carrega dados), depois é rápido (usa cache)
- **API Docs**: Use http://127.0.0.1:5000/docs para testar endpoints

---

## 🎯 Próximos Passos

1. ✅ Rodar o sistema (`.\start.ps1`)
2. ✅ Acessar frontend (http://127.0.0.1:8050)
3. ✅ Testar API docs (http://127.0.0.1:5000/docs)
4. 🔧 Integrar frontend com endpoints de cache
5. 🔧 Adicionar mais análises F1
6. 🚀 Deploy em produção (VPS/Cloud)

---

**Desenvolvido com:**
- FastAPI (Backend)
- Dash/Plotly (Frontend)
- FastF1 (Dados F1)
- SQLite (Cache)
