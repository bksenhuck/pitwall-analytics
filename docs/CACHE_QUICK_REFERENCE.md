# Cache Layer - Quick Reference

> **⚠️ OBSOLETE DOCUMENTATION**
> 
> This document describes the old TTL-based cache system which has been replaced.
> 
> **Please refer to:**
> - [CACHE_V2_GUIDE.md](../docs/CACHE_V2_GUIDE.md) - Complete guide to the normalized cache system
> - [CACHE_V2_SUMMARY.md](../CACHE_V2_SUMMARY.md) - Quick summary and usage

---

## 🚀 Current System Quick Start

### 1. Install dependencies
```powershell
pip install -r requirements.txt
```

### 2. Populate cache with data
```powershell
python scripts/populate_cache.py --season 2024
```

### 3. Start backend
```powershell
python main.py
```

The database will be automatically created at: `data/pitwall_cache.db`

---

## 📡 Current API Endpoints

```bash
# Get available cached data
GET /api/data/available

# Get session data (laps, results, weather)
GET /api/data/session?season=2024&event=Bahrain&session_type=Race

# Get drivers for a session
GET /api/data/session/drivers?season=2024&event=Bahrain&session_type=Race
```

---

## 🗂️ File Structure

```
backend/
├── db/
│   └── session.py                # SQLite connection
├── modCurrent File Structure

```
backend/
├── db/
│   └── session.py                # SQLite schema (8 normalized tables)
├── repositories/
│   └── data_repository.py        # Database operations (CRUD)
├── services/
│   └── f1_data_service.py        # Business logic (cache-only)
└── api/
    └── data.py                   # API endpoints

scripts/
└── populate_cache.py             # Load FastF1 data into cache
```
User Request
    ↓
Cache Service (TTL check)
    ↓urrent Cache Flow

```
1. Offline: populate_cache.py → FastF1 → SQLite (normalized tables)
2. Runtime: Frontend → API → F1DataService → DataRepository → SQLite
                                                                ↓
                                                          Return cached data
```

**Key difference:** Backend NEVER calls FastF1 directly. All data must be pre-loaded.

---

## 💻 Code Examples

### Using cached data in your code

```python
from backend.services.f1_data_service import F1DataService

service = F1DataService()

# Get available data
available = service.get_available_data()
# Returns: {'2024': {'Bahrain': {'Race': ['VER', 'HAM', ...]}}}

# Get session data
session_data = service.get_session_data(
    season=2024,
    event='Bahrain',
    session_type='Race',
    driver_filter='VER'  # optional
)
# Returns: {'laps': [...], 'results': [...], 'weather': [...]}
```

### Populating cache (run offline)

```python
# Command line
python scripts/populate_cache.py --season 2024

# Or with specific events
python scripts/populate_cache.py --season 2024 --event Bahrain

# Or programmatically
from scripts.populate_cache import populate_season
populate_season(2024, events=['Bahrain', 'Saudi Arabia'])
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
```Database Location

The SQLite database is created at: `data/pitwall_cache.db`

### Schema

8 normalized tables:
- `seasons` - F1 seasons
- `events` - Grand Prix events
- `sessions` - Practice, Qualifying, Race sessions
- `laps` - Lap timing data
- `results` - Session results (finishing positions)
- `weather` - Weather conditions
- `race_control_messages` - Flags, penalties
- `session_status` - Track status (green, yellow, red)

For complete schema details, see [CACHE_V2_GUIDE.md](../docs/CACHE_V2_GUIDE.md). Second request (hit - fast)
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
pip install -r requirements.txt
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
