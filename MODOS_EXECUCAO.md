# 🏁 Pitwall Analytics - Modos de Execução

Existem **2 modos** de executar este projeto:

---

## 🔧 Modo Desenvolvimento (Local)

**Use quando:** Desenvolvimento local, testes, debug

**Como executar:**

### Opção 1: Script Automático
```powershell
.\start.ps1
```
Abre 2 janelas (Backend + Frontend)

### Opção 2: Manual
```powershell
# Terminal 1 - Backend
python -m backend.app

# Terminal 2 - Frontend
python app.py
```

**URLs:**
- Frontend: http://127.0.0.1:8050
- Backend: http://127.0.0.1:5000
- API Docs: http://127.0.0.1:5000/docs

**Características:**
- ✅ Hot reload (mudanças no código recarregam automaticamente)
- ✅ Debug habilitado
- ✅ Logs detalhados
- ✅ Backend e frontend separados
- ❌ Não funciona para deploy

---

## 🚀 Modo Produção (Deploy)

**Use quando:** Deploy em Render, Railway, Heroku, VPS, etc.

**Como executar localmente:**
```powershell
.\start-production.ps1
```
ou
```powershell
python main.py
```

**URLs (tudo em uma porta):**
- Frontend: http://127.0.0.1:5000/
- Backend: http://127.0.0.1:5000/api
- API Docs: http://127.0.0.1:5000/api/docs

**Características:**
- ✅ Servidor único (FastAPI + Dash integrados)
- ✅ Funciona em qualquer plataforma de deploy
- ✅ Usa menos recursos
- ✅ Ideal para Render/Railway/Heroku
- ⚠️ Debug desabilitado em produção

---

## 📋 Comparação

| Aspecto | Desenvolvimento | Produção |
|---------|----------------|----------|
| **Comando** | `.\start.ps1` | `python main.py` |
| **Processos** | 2 (Backend + Frontend) | 1 (Unificado) |
| **Portas** | 5000 + 8050 | 1 porta (5000 ou $PORT) |
| **Hot Reload** | ✅ Sim | ❌ Não |
| **Debug** | ✅ Habilitado | ❌ Desabilitado |
| **Deploy** | ❌ Não funciona | ✅ Funciona |
| **Custo (Render)** | - | ✅ Grátis (1 serviço) |

---

## 🌐 Estrutura de Rotas

### Desenvolvimento
```
Frontend (porta 8050)
├── /                 → Home
├── /analytics        → Analytics
└── /live             → Live

Backend (porta 5000)
├── /api/health       → Health check
├── /api/data/*       → Data endpoints
├── /api/cached/*     → Cache endpoints
└── /docs             → API docs
```

### Produção (porta única)
```
Servidor Único (porta 5000 ou $PORT)
├── /                 → Frontend (Dash)
│   ├── /analytics
│   └── /live
├── /api/             → Backend (FastAPI)
│   ├── /api/health
│   ├── /api/data/*
│   └── /api/cached/*
└── /api/docs         → API docs
```

---

## 🎯 Quando Usar Cada Modo?

### Use Desenvolvimento quando:
- 🔧 Desenvolvendo novas features
- 🐛 Debugando erros
- 🧪 Testando mudanças
- 📝 Editando código frequentemente

### Use Produção quando:
- 🚀 Fazendo deploy (Render, Railway, etc.)
- 🎭 Testando comportamento de produção localmente
- 💰 Quer usar apenas 1 serviço (economizar)
- ⚡ Precisa app sempre ativo

---

## 📦 Deploy Rápido

1. **Testar produção localmente:**
   ```powershell
   .\start-production.ps1
   ```

2. **Fazer deploy no Render:**
   ```bash
   # Push para GitHub
   git add .
   git commit -m "Deploy"
   git push

   # No Render Dashboard:
   # - New → Blueprint
   # - Conectar repositório
   # - Deploy automático!
   ```

3. **Acessar:**
   ```
   https://seu-app.onrender.com/
   https://seu-app.onrender.com/api/docs
   ```

---

## 🛠️ Arquivos de Configuração

| Arquivo | Propósito |
|---------|-----------|
| `backend/app.py` | Backend FastAPI (desenvolvimento) |
| `app.py` | Frontend Dash (desenvolvimento) |
| `main.py` | **Servidor unificado (produção)** |
| `start.ps1` | Script de desenvolvimento |
| `start-production.ps1` | Script de produção (teste local) |
| `Procfile` | Configuração Render/Heroku |
| `render.yaml` | Blueprint Render (deploy automático) |

---

## 📚 Documentação Adicional

- **[COMO_EXECUTAR.md](COMO_EXECUTAR.md)** - Guia completo de execução
- **[DEPLOY.md](DEPLOY.md)** - Guia de deploy (Render, Railway, etc.)
- **[CACHING_LAYER_GUIDE.md](CACHING_LAYER_GUIDE.md)** - Sistema de cache

---

## ⚡ Comandos Rápidos

### Desenvolvimento
```powershell
.\start.ps1                    # Iniciar tudo
# Backend: http://127.0.0.1:5000
# Frontend: http://127.0.0.1:8050
```

### Produção (Teste Local)
```powershell
.\start-production.ps1         # Testar modo produção
# Tudo em: http://127.0.0.1:5000
```

### Deploy (Render)
```bash
git push                       # Render faz deploy automático
```

---

**⚠️ IMPORTANTE para Deploy:**

Sempre use **`main.py`** (modo produção) em plataformas de deploy!

```bash
# ✅ CORRETO (produção)
uvicorn main:app --host 0.0.0.0 --port $PORT

# ❌ ERRADO (desenvolvimento - 2 processos)
python -m backend.app  # Só backend, frontend não funciona
python app.py          # Só frontend, backend não funciona
```
