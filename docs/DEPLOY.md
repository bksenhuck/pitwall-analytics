# 🚀 Deploy - Pitwall Analytics

Guia de deploy para diferentes plataformas com backend e frontend unificados.

---

## 📦 Arquitetura de Deploy

### Modo Desenvolvimento (Local)
```
Terminal 1: python -m backend.app    # Backend (porta 5000)
Terminal 2: python app.py             # Frontend (porta 8050)
```
**2 processos separados** ❌ Não funciona em deploy gratuito

### Modo Produção (Deploy)
```
Único comando: python main.py
ou: uvicorn main:app --host 0.0.0.0 --port $PORT
```
**1 processo único** ✅ Funciona em qualquer plataforma

**Estrutura de rotas:**
- `/` - Frontend Dash
- `/api/*` - Backend FastAPI
- `/api/docs` - Documentação da API

---

## 🌐 Render.com (Recomendado)

### Opção 1: Deploy Automático via Blueprint

1. **Fazer push do código para GitHub**

2. **Conectar repositório no Render:**
   - Ir em https://dashboard.render.com
   - New → Blueprint
   - Conectar seu repositório
   - Render detectará automaticamente o `render.yaml`

3. **Aplicação rodando!**
   - URL: `https://pitwall-analytics-XXXX.onrender.com`
   - API: `https://pitwall-analytics-XXXX.onrender.com/api/docs`

### Opção 2: Deploy Manual

1. **Criar Web Service no Render:**
   - New → Web Service
   - Conectar repositório

2. **Configurar:**
   ```
   Name: pitwall-analytics
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

3. **Environment Variables:**
   ```env
   PYTHON_VERSION=3.11.0
   DEBUG=False
   CACHE_ENABLED=True
   CACHE_TTL_SECONDS=3600
   ```

4. **Deploy!**

### ⚡ Manter Ativo (Plano Gratuito)

No plano gratuito do Render, o serviço **dorme após 15min de inatividade**.

**Soluções:**

**A) UptimeRobot (Grátis):**
- Cadastrar em https://uptimerobot.com
- Adicionar monitor HTTP
- URL: `https://seu-app.onrender.com/api/health`
- Intervalo: 5 minutos
- Mantém o app acordado 24/7

**B) Cron-Job.org:**
- https://cron-job.org
- Criar job que chama `/api/health` a cada 5 minutos

**C) Upgrade para Paid Plan:**
- $7/mês - sempre ativo + mais recursos

---

## 🐳 Railway.app

```bash
# Instalar CLI
npm i -g @railway/cli

# Login
railway login

# Deploy
railway init
railway up
```

**Variáveis de ambiente:**
```env
PORT=${{PORT}}  # Railway injeta automaticamente
DEBUG=False
```

**URL:** `https://seu-app.railway.app`

---

## 📦 Heroku

```bash
# Login
heroku login

# Criar app
heroku create pitwall-analytics

# Deploy
git push heroku main

# Configurar
heroku config:set DEBUG=False
heroku config:set CACHE_ENABLED=True

# Abrir
heroku open
```

**Arquivo necessário:** `Procfile` (já criado)

---

## ☁️ Google Cloud Run

```bash
# Build Docker image
docker build -t pitwall-analytics .

# Tag
docker tag pitwall-analytics gcr.io/SEU-PROJECT/pitwall-analytics

# Push
docker push gcr.io/SEU-PROJECT/pitwall-analytics

# Deploy
gcloud run deploy pitwall-analytics \
  --image gcr.io/SEU-PROJECT/pitwall-analytics \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 🐳 Docker (Qualquer VPS)

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Porta
EXPOSE 8000

# Executar
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build e Run

```bash
# Build
docker build -t pitwall-analytics .

# Run
docker run -p 8000:8000 \
  -e DEBUG=False \
  -e CACHE_ENABLED=True \
  pitwall-analytics
```

### Docker Compose

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - CACHE_ENABLED=True
      - CACHE_TTL_SECONDS=3600
    volumes:
      - ./data:/app/data
      - ./.ff1cache:/app/.ff1cache
```

---

## 🔧 Variáveis de Ambiente (Produção)

```env
# Aplicação
DEBUG=False
API_HOST=0.0.0.0
API_PORT=10000  # Ou usar $PORT da plataforma

# Cache FastF1
CACHE_DIR=.ff1cache
CACHE_ENABLED=True

# Cache SQLite
DB_DIR=data
DB_NAME=pitwall_cache.db
CACHE_TTL_SECONDS=3600
EXTERNAL_API_TIMEOUT=30

# CORS (opcional)
CORS_ORIGINS=["*"]
```

---

## ✅ Checklist de Deploy

### Antes do Deploy

- [ ] Código no GitHub/GitLab
- [ ] `requirements.txt` atualizado
- [ ] `main.py` criado (servidor unificado)
- [ ] `Procfile` criado
- [ ] `render.yaml` criado (opcional)
- [ ] Testar localmente: `python main.py`

### Configurar na Plataforma

- [ ] Build command: `pip install -r requirements.txt`
- [ ] Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- [ ] Variáveis de ambiente configuradas
- [ ] Health check: `/api/health`

### Após Deploy

- [ ] Testar URL principal (frontend)
- [ ] Testar `/api/docs` (backend)
- [ ] Testar cache: `/api/cached/data?key=f1_seasons`
- [ ] Configurar monitor (UptimeRobot)
- [ ] Configurar domínio customizado (opcional)

---

## 🎯 Estrutura de URLs em Produção

Supondo deploy em: `https://pitwall-analytics.onrender.com`

```
https://pitwall-analytics.onrender.com/              → Frontend (Home)
https://pitwall-analytics.onrender.com/analytics     → Página Analytics
https://pitwall-analytics.onrender.com/live          → Página Live
https://pitwall-analytics.onrender.com/api/health    → Health check
https://pitwall-analytics.onrender.com/api/docs      → API Docs (Swagger)
https://pitwall-analytics.onrender.com/api/cached/data?key=f1_seasons → Cache
```

---

## 🐛 Troubleshooting

### App fica desativando no Render

**Causa:** Plano gratuito dorme após 15min de inatividade

**Solução:** UptimeRobot pingando `/api/health` a cada 5min

### Erro 502 Bad Gateway

**Causa:** App não está respondendo na porta correta

**Solução:** Usar `--port $PORT` (variável da plataforma)

### Cache SQLite não persiste

**Causa:** Render/DigitalOcean usar filesystem efêmero

**Soluções:**
1. Usar volume persistente (Render Disks, $)
2. Migrar para PostgreSQL (Render PostgreSQL grátis)
3. Usar Redis para cache

### Dependências não instalam

**Causa:** `requirements.txt` com erro ou versões incompatíveis

**Solução:**
```bash
pip freeze > requirements.txt  # Gerar novamente
```

---

## 📊 Comparação de Plataformas

| Plataforma | Grátis? | Sempre Ativo? | Domínio | Facilidade |
|------------|---------|---------------|---------|------------|
| **Render** | ✅ 750h/mês | ❌ (dorme) | ✅ SSL | ⭐⭐⭐⭐⭐ |
| **Railway** | ✅ $5 crédito | ✅ | ✅ SSL | ⭐⭐⭐⭐⭐ |
| **Heroku** | ❌ (desde 2022) | - | ✅ SSL | ⭐⭐⭐⭐ |
| **Fly.io** | ✅ Limitado | ✅ | ✅ SSL | ⭐⭐⭐ |
| **Vercel** | ✅ | ✅ | ✅ SSL | ⭐⭐⭐ (Node only) |
| **Google Cloud Run** | ✅ Cotas | ❌ (escala zero) | ✅ SSL | ⭐⭐ |

**Recomendação:** **Render.com** (melhor custo-benefício + fácil)

---

## 🚀 Deploy Rápido (Render)

```bash
# 1. Criar repositório no GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/SEU-USUARIO/pitwall-analytics.git
git push -u origin main

# 2. Ir em https://dashboard.render.com
# 3. New → Blueprint
# 4. Conectar repositório
# 5. Deploy automático!
```

**URL gerada:** `https://pitwall-analytics-XXXX.onrender.com`

**Pronto! 🎉**

---

## 📚 Próximos Passos

1. ✅ Deploy inicial
2. ⚙️ Configurar UptimeRobot (manter ativo)
3. 🌐 Configurar domínio customizado
4. 📊 Adicionar analytics (Google Analytics, Plausible)
5. 🔒 Adicionar autenticação (se necessário)
6. 🗄️ Migrar cache para PostgreSQL (produção)
7. 📈 Monitoramento (Sentry, New Relic)

---

**Links Úteis:**
- Render Docs: https://render.com/docs
- Railway Docs: https://docs.railway.app
- UptimeRobot: https://uptimerobot.com
- FastAPI Deploy: https://fastapi.tiangolo.com/deployment/
