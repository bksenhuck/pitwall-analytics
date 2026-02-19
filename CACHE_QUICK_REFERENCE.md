# Cache Layer - Quick Reference

## 🚀 Quick Start

### 1. Install dependencies (already done)
```powershell
pip install -r requirements-new.txt
```

### 2. Configure TTL (optional)
```env
# .env
CACHE_TTL_SECONDS=3600  # 1 hour
```

### 3. Start backend
```powershell
python -m backend.app
```

The database will be automatically created at: `data/pitwall_cache.db`

---

## 📡 API Endpoints Quick Reference

```bash
# Get cached data (with TTL logic)
GET /api/cached/data?key=f1_seasons

# Force refresh (bypass cache)
POST /api/cached/refresh?key=f1_seasons

# Cache metadata
GET /api/cached/cache/info?key=f1_seasons

# List all cache keys
GET /api/cached/cache/keys

# Delete cache entry
DELETE /api/cached/cache?key=f1_seasons
```

---

## 🗂️ File Structure

```
backend/
├── db/
│   └── session.py                # SQLite connection
├── models/
│   └── data_model.py             # Pydantic models
├── repositories/
│   └── data_repository.py        # Database operations (CRUD)
├── routes/
│   └── data.py                   # Cache API endpoints
└── services/
    ├── cache_service_v2.py       # TTL cache logic
    └── external_api.py           # External API calls
```

---

## 🔄 Cache Flow

```
User Request
    ↓
Cache Service (TTL check)
    ↓
┌─────────────────────────┐
│ Cache exists & valid?   │
├─────────────────────────┤
│ YES → Return from DB ✅ │ (Fast: ~10ms)
│ NO  → Fetch from API ⚡ │ (Slow: ~1s, then cache)
└─────────────────────────┘
```

---

## 💻 Code Examples

### Using cache in your routes

```python
from backend.services.cache_service_v2 import CacheService
from backend.services.external_api import ExternalAPIService

cache_service = CacheService()
external_api = ExternalAPIService()

@router.get('/seasons')
async def get_seasons():
    data, is_cached = await cache_service.get_data_with_cache(
        cache_key="f1_seasons",
        fetch_callback=external_api.fetch_f1_seasons
    )
    return {
        'data': data,
        'from_cache': is_cached
    }
```

### Force refresh

```python
@router.post('/refresh-seasons')
async def refresh_seasons():
    fresh_data = await cache_service.refresh_data(
        cache_key="f1_seasons",
        fetch_callback=external_api.fetch_f1_seasons
    )
    return {'data': fresh_data}
```

### Check cache status

```python
cache_info = cache_service.get_cache_info("f1_seasons")
print(cache_info)
# {
#   'exists': True,
#   'age_seconds': 1800,
#   'ttl_seconds': 3600,
#   'is_expired': False,
#   'expires_in_seconds': 1800
# }
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_DIR` | `data` | Database directory |
| `DB_NAME` | `pitwall_cache.db` | Database file name |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL (1 hour) |
| `EXTERNAL_API_TIMEOUT` | `30` | API timeout (seconds) |

### TTL Examples

```env
CACHE_TTL_SECONDS=300     # 5 minutes
CACHE_TTL_SECONDS=1800    # 30 minutes
CACHE_TTL_SECONDS=3600    # 1 hour (default)
CACHE_TTL_SECONDS=86400   # 24 hours
```

---

## 🧪 Testing

### Test cache miss → hit flow

```bash
# 1. Clear cache
curl -X DELETE "http://127.0.0.1:5000/api/cached/cache?key=f1_seasons"

# 2. First request (miss - slow)
curl "http://127.0.0.1:5000/api/cached/data?key=f1_seasons"
# Response: "cached": false

# 3. Second request (hit - fast)
curl "http://127.0.0.1:5000/api/cached/data?key=f1_seasons"
# Response: "cached": true
```

### Check cache info

```bash
curl "http://127.0.0.1:5000/api/cached/cache/info?key=f1_seasons"
```

---

## 📊 Database

### Location
```
data/pitwall_cache.db
```

### Schema
```sql
cached_data
├── id (INTEGER PRIMARY KEY)
├── key (TEXT UNIQUE)
├── data (TEXT)
├── last_updated (TIMESTAMP)
└── created_at (TIMESTAMP)
```

### Query manually (optional)
```powershell
sqlite3 data/pitwall_cache.db "SELECT * FROM cached_data;"
```

---

## 🎯 Adding Custom Cache Keys

### 1. Add fetch function in `external_api.py`

```python
async def fetch_my_data(self) -> Dict[str, Any]:
    # Your external API call here
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com/data')
        return response.json()
```

### 2. Add route mapping in `routes/data.py`

```python
@router.get('/data')
async def get_data(key: str = Query('f1_seasons')):
    if key == 'my_data':
        fetch_callback = external_api.fetch_my_data
    elif key == 'f1_seasons':
        fetch_callback = external_api.fetch_f1_seasons
    # ...
```

---

## 🔧 Common Operations

### Get data with cache
```python
data, cached = await cache_service.get_data_with_cache(
    cache_key="my_key",
    fetch_callback=my_fetch_function
)
```

### Force refresh
```python
fresh_data = await cache_service.refresh_data(
    cache_key="my_key",
    fetch_callback=my_fetch_function
)
```

### Invalidate cache
```python
cache_service.invalidate_cache("my_key")
```

### Get all keys
```python
keys = cache_service.get_all_cache_keys()
```

---

## 🆘 Troubleshooting

### Database not created
Check startup logs: Should see "✅ SQLite cache database initialized"

### Cache always misses
Check TTL: `curl http://127.0.0.1:5000/api/cached/cache/info`

### "Module not found" errors
```powershell
pip install -r requirements-new.txt
```

---

## 📚 Full Documentation

See [CACHING_LAYER_GUIDE.md](CACHING_LAYER_GUIDE.md) for complete guide.

---

**Quick command reference:**
```bash
# Start backend
python -m backend.app

# Test cache endpoint
curl http://127.0.0.1:5000/api/cached/data?key=f1_seasons

# Force refresh
curl -X POST http://127.0.0.1:5000/api/cached/refresh?key=f1_seasons

# API docs (interactive)
http://127.0.0.1:5000/docs
```
