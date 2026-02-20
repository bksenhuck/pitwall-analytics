# 🎮 Controle Manual do Cache SQLite

> **📍 Localização**: Este documento está em `docs/MANUAL_CACHE_CONTROL.md`  
> **🔗 Veja também**: [AUTO_CACHE_GUIDE.md](AUTO_CACHE_GUIDE.md) | [../scripts/README.md](../scripts/README.md)

## 🎯 Nova Arquitetura

Agora VOCÊ controla quando o cache é atualizado. **Sem TTL automático, sem fallback para API externa.**

### Separação de Responsabilidades

```
┌─────────────────────────────────────────┐
│         FRONTEND (Dash)                 │
│  Apenas LÊ do SQLite                    │
│  GET /api/cached/read                   │
└──────────────┬──────────────────────────┘
               │
               ↓
        ┌──────────────┐
        │    SQLite    │
        │    Cache     │
        └──────┬───────┘
               ↑
               │
┌──────────────┴──────────────────────────┐
│         VOCÊ (Admin/Terminal)           │
│  Controla quando POPULAR o cache        │
│  POST /api/cached/populate              │
│  OU: python scripts/populate_cache.py   │
└─────────────────────────────────────────┘
```

---

## 🚀 Como Usar

### Opção 1: Script CLI (Recomendado)

```powershell
# Popular cache para temporadas F1
python scripts/populate_cache.py f1_seasons

# Popular calendário de corridas para 2024
python scripts/populate_cache.py races_2024

# Popular cache para uma corrida específica
python scripts/populate_cache.py race_2024_bahrain

# Popular múltiplas corridas
python scripts/populate_cache.py race_2024_monaco
python scripts/populate_cache.py race_2024_silverstone
python scripts/populate_cache.py race_2024_monza

# Listar todos os cache keys
python scripts/populate_cache.py --list

# Ver informações de um cache key
python scripts/populate_cache.py --info f1_seasons
python scripts/populate_cache.py --info races_2024

# Deletar um cache key
python scripts/populate_cache.py --delete f1_seasons

# Ajuda
python scripts/populate_cache.py --help
```

### Opção 2: API Endpoints

```powershell
# Popular cache via API
curl -X POST "http://127.0.0.1:5000/api/cached/populate?key=f1_seasons"

# Ver cache keys disponíveis
curl "http://127.0.0.1:5000/api/cached/cache/keys"

# Ver informações de um cache
curl "http://127.0.0.1:5000/api/cached/cache/info?key=f1_seasons"

# Deletar cache
curl -X DELETE "http://127.0.0.1:5000/api/cached/cache?key=f1_seasons"
```

---

## 📡 Endpoints da API

### 1. GET /api/cached/read (Read-Only)

**Função:** Ler APENAS do SQLite (sem fallback para API externa)

```bash
curl "http://127.0.0.1:5000/api/cached/read?key=f1_seasons"
```

**Resposta (sucesso):**
```json
{
  "success": true,
  "data": {...},
  "cached": true,
  "last_updated": "2026-02-19T...",
  "message": "Data read from cache (last updated: ...)"
}
```

**Resposta (cache não existe):**
```json
{
  "detail": "Cache key 'f1_seasons' not found. Use POST /populate to fetch and cache data first."
}
```
Status: 404

**Uso:** Frontend chama este endpoint para consumir dados

---

### 2. POST /api/cached/populate (Manual Update)

**Função:** Buscar da API externa e salvar no SQLite

```bash
curl -X POST "http://127.0.0.1:5000/api/cached/populate?key=f1_seasons"
```

**Resposta:**
```json
{
  "success": true,
  "message": "Cache populated successfully for key: f1_seasons",
  "last_updated": "2026-02-19T22:30:00",
  "records_updated": 1
}
```

**Uso:** Você chama quando quiser atualizar o cache

---

### 3. GET /api/cached/cache/info

**Função:** Ver metadados do cache

```bash
# Informação de um cache key específico
curl "http://127.0.0.1:5000/api/cached/cache/info?key=f1_seasons"

# Informação geral (todos os keys)
curl "http://127.0.0.1:5000/api/cached/cache/info"
```

---

### 4. GET /api/cached/cache/keys

**Função:** Listar todos os cache keys

```bash
curl "http://127.0.0.1:5000/api/cached/cache/keys"
```

**Resposta:**
```json
{
  "success": true,
  "total": 3,
  "keys": ["f1_seasons", "race_2024_bahrain", "race_2024_monaco"]
}
```

---

### 5. DELETE /api/cached/cache

**Função:** Deletar cache específico

```bash
curl -X DELETE "http://127.0.0.1:5000/api/cached/cache?key=f1_seasons"
```

---s_2024
python scripts/populate_cache.py race_2024_bahrain
python scripts/populate_cache.py race_2024_jeddah

# 2. Verificar o que foi populado
python scripts/populate_cache.py --list

# 3. Iniciar backend
python -m backend.app

# 4. Frontend agora pode ler do cache
# GET /api/cached/read?key=f1_seasons → ✅ Sucesso
# GET /api/cached/read?key=races_2024 → ✅ Sucesso
# GET /api/cached/read?key=race_2024_bahrainhrain

# 2. Verificar o que foi populado
python scripts/populate_cache.py --list

# 3. Iniciar backend
python -m backend.app

# 4. Frontend agora pode ler do cache
# GET /api/cached/read?key=f1_seasons → ✅ Sucesso
```

---

### Atualização de Dados

```powershell
# Quando nova temporada F1 começar ou dados mudarem:

# 1. Atualizar cache manualmente
python scripts/populate_cache.py f1_seasons

# 2. Frontend automaticamente verá dados novos na próxima leitura
```

---

### Debug / Manutenção

```powershell
# Ver informações de um cache
python scripts/populate_cache.py --info f1_seasons

# Deletar cache corrompido
python scripts/populate_cache.py --delete f1_seasons

# Repopular
python scripts/populate_cache.py f1_seasons
```

---

## 📋 Cache Keys Suportados

| Key Pattern | Exemplo | Descrição |
|-------------|---------|-----------|
| `f1_seasons` | `f1_seasons` | Lista de todas as temporadas F1 disponíveis |
| `races_YEAR` | `races_2024` | Calendário de corridas para uma temporada específica |
| `race_YEAR_EVENT` | `race_2024_bahrain` | Dados completos de uma corrida (laps, drivers, etc.) |
| `race_YEAR_EVENT` | `race_2024_monaco` | Outra corrida da mesma temporada |
| `race_YEAR_EVENT` | `race_2024_Bahrain_Grand_Prix` | Suporta nomes com underscores |

### Formatos de Cache Key

1. **`f1_seasons`** - Lista de temporadas
   ```powershell
   python scripts/populate_cache.py f1_seasons
   ```
   
2. **`races_YEAR`** - Calendário de corridas para uma temporada
   ```powershell
   python scripts/populate_cache.py races_2024
   python scripts/populate_cache.py races_2023
   ```
   
3. **`race_YEAR_EVENT`** - Dados completos de uma corrida
   ```powershell
   # Nome curto
   python scripts/populate_cache.py race_2024_bahrain
   
   # Nome completo (underscores substituem espaços)
   python scripts/populate_cache.py race_2024_Bahrain_Grand_Prix
   python scripts/populate_cache.py race_2024_monaco
   ```

---

## 🎯 Vantagens desta Abordagem

### ✅ Controle Total
- **Você** decide quando buscar da API externa
- Sem surpresas de requisições automáticas
- Sem TTL automático

### ✅ Previsibilidade
- Frontend **sempre** lê do SQLite
- Se cache não existe → erro 404 claro
- Você sabe exatamente de onde vem cada dado

### ✅ Performance
- Frontend **nunca** espera por API externa
- Todas as leituras são rápidas (SQLite local)
- API externa só é chamada quando você mandar

### ✅ Economia
- Controla chamadas à API externa
- Pode ter rate limits/quotas na API
- Evita chamadas desnecessárias

---

## 🛠️ Integração no Frontend

### Antes (com TTL automático)
```python
# Frontend não sabia se viria do cache ou API
response = requests.get('/api/cached/data?key=f1_seasons')
# Podia demorar 1s se cache expirado
```

### Agora (read-only)
```python
# Frontend SEMPRE lê do SQLite (rápido)
response = requests.get('/api/cached/read?key=f1_seasons')
# Sempre ~10ms

# Se 404 → cache não foi populado ainda
if response.status_code == 404:
    print("Cache não populado. Admin precisa popular primeiro.")
```

---

## 📊 Comandos Rápidos temporadas
python scripts/populate_cache.py races_2024           # Popular calendário 2024
python scripts/populate_cache.py race_2024_bahrain    # Popular corrida específica
python scripts/populate_cache.py --list               # Verificar
python -m backend.app                         # Iniciar backend
curl http://127.0.0.1:5000/api/cached/read?key=f1_seasons  # Testar

# Atualização
python scripts/populate_cache.py f1_seasons           # Atualizar quando necessário
python scripts/populate_cache.py races_2024           # Atualizar calendário

# Manutenção
python scripts/populate_cache.py --info f1_seasons    # Ver info
python scripts/populate_cache.py --info races_2024    # Ver info de calendári
python scripts/populate_cache.py f1_seasons           # Atualizar quando necessário

# Manutenção
python scripts/populate_cache.py --info f1_seasons    # Ver info
python scripts/populate_cache.py --delete f1_seasons  # Limpar
```

---

## 🎓 Exemplo Prático

### Cenário: Nova temporada F1 2025 começou

```powershell
# 1. Você percebe que tem dados novos na API externa
# 2. Decide atualizar o cache
python scripts/populate_cache.py f1_seasons

# Output:
# 📡 Fetching data from external API for key: f1_seasons
# 💾 Saving data to SQLite cache...
# ✅ Cache populated successfully!
#    Key: f1_seasons
#    Last Updated: 2026-02-19 22:45:00
#    Records: 75  (era 74, agora tem 2025!)

# 3. Frontend automaticamente verá temporada 2025 na próxima request
# GET /api/cached/read?key=f1_seasons → inclui 2025 ✅
```

---

## 🚨 Tratamento de Erros

### Frontend tenta ler cache que não existe

```bash
GET /api/cached/read?key=race_2024_miami
# → 404: Cache key 'race_2024_miami' not found
```

**Solução:** Popular o cache primeiro
```bash
python scripts/populate_cache.py race_2024_miami
```

---

## 🔐 Segurança

### Quem pode popular o cache?

**Desenvolvimento:** Qualquer um com acesso ao terminal ou API

**Produção:** Considere:
- Proteger endpoint `/populate` com autenticação
- Criar scheduled job para atualização automática (ex: cron)
- Limitar acesso ao script CLI apenas para admins

---

## 📚 Resumo

| Ação | Como | Quem |
|------|------|------|
| **Ler dados** | `GET /read` | Frontend |
| **Popular cache** | `POST /populate` ou `python scripts/populate_cache.py` | Você (Admin) |
| **Ver cache** | `GET /cache/keys` | Qualquer um |
| **Deletar cache** | `DELETE /cache` | Você (Admin) |

**Regra de Ouro:** Frontend lê, você escreve. Simples assim! 🎯

