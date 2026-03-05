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

### Arquitetura GCP

```
GitHub push (main)
    |
    v
GitHub Actions
    |-- docker build + push --> Artifact Registry
    |
    v
Cloud Run (pitwall-analytics)
    |-- download DB --> Google Cloud Storage (GCS)
    |-- serve app   --> usuários
```

### Pré-requisitos

1. **gcloud CLI instalado e autenticado:**
   ```bash
   gcloud auth login
   gcloud config set project SEU-PROJETO
   ```

2. **Artifact Registry criado:**
   ```bash
   gcloud artifacts repositories create pitwall-repo \
     --repository-format=docker \
     --location=us-central1
   ```

3. **Bucket GCS criado:**
   ```bash
   gsutil mb -l us-central1 gs://pitwall-analytics-data
   ```

4. **Service Account com permissões:**
   ```bash
   gcloud iam service-accounts create pitwall-sa \
     --display-name="Pitwall Analytics SA"

   # Storage object viewer (para Cloud Run ler o DB)
   gcloud projects add-iam-policy-binding SEU-PROJETO \
     --member="serviceAccount:pitwall-sa@SEU-PROJETO.iam.gserviceaccount.com" \
     --role="roles/storage.objectViewer"

   # Storage object creator (para upload do DB via pipeline)
   gcloud projects add-iam-policy-binding SEU-PROJETO \
     --member="serviceAccount:pitwall-sa@SEU-PROJETO.iam.gserviceaccount.com" \
     --role="roles/storage.objectCreator"
   ```

### Configurar .env

Preencha as variaveis GCP no `.env`:
```env
GCS_BUCKET_NAME=pitwall-analytics-data
GCS_DB_BLOB_PATH=db/pitwall_cache.db
GCP_PROJECT=meu-projeto-gcp
GCP_REGION=us-central1
AR_REPOSITORY=pitwall-repo
CLOUDRUN_SERVICE=pitwall-analytics
IMAGE_NAME=pitwall-analytics
```

### Subir dados para o GCS

```bash
# Upload do banco SQLite para o GCS
python -m backend.pipelines.deploy.upload_to_gcs

# Upload de uma temporada especifica
python -m backend.pipelines.deploy.upload_to_gcs --season 2025

# Upload + acionar redeploy
python -m backend.pipelines.deploy.upload_to_gcs --deploy
```

Ou via script antigo (mais simples):
```bash
python -m backend.services.gcs_service upload
python -m backend.services.gcs_service upload --season 2025
```

### Build e Deploy manual

```bash
# Build Docker + deploy no Cloud Run
python -m backend.pipelines.deploy.build_and_deploy

# Apenas build
python -m backend.pipelines.deploy.build_and_deploy --build-only

# Apenas redeploy (imagem ja existente)
python -m backend.pipelines.deploy.build_and_deploy --deploy-only

# Com tag especifica
python -m backend.pipelines.deploy.build_and_deploy --tag v1.2.0
```

### Deploy via GitHub Actions (CI/CD)

O workflow `.github/workflows/deploy.yml` faz build + deploy automaticamente no push para `main`.

**Secrets necessarios no GitHub** (Settings → Secrets → Actions):

| Secret | Valor |
|--------|-------|
| `GCP_SA_KEY` | JSON da service account (para autenticar) |
| `GCP_PROJECT` | ID do projeto GCP |
| `GCP_REGION` | Regiao (ex: `us-central1`) |
| `AR_REPOSITORY` | Nome do repositorio Artifact Registry |
| `CLOUDRUN_SERVICE` | Nome do servico Cloud Run |
| `GCS_BUCKET_NAME` | Nome do bucket GCS |
| `GCS_DB_BLOB_PATH` | Caminho do DB no bucket |

**Gerar chave da service account:**
```bash
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=pitwall-sa@SEU-PROJETO.iam.gserviceaccount.com
# Copie o conteudo de sa-key.json para o secret GCP_SA_KEY
```

### Download do DB no startup (producao)

O app pode baixar o DB do GCS automaticamente ao iniciar:
```bash
python -m backend.services.gcs_service download
```

Para integrar no startup do Cloud Run, adicione ao entrypoint ou ao evento `startup` do FastAPI em `main.py`.

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
