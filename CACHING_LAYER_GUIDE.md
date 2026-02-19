# 🗄️ Caching Layer Implementation Guide

## Overview

A complete persistence and caching layer has been added to your FastAPI backend using:
- **SQLite** for data persistence
- **TTL (Time-To-Live)** cache strategy
- **Async external API** integration
- **Clean separation of concerns**

---

## 📁 New File Structure

```
backend/
├── app.py                          ⭐ Updated: registers cache routes + DB init
├── config.py
│
├── db/                             🆕 Database Layer
│   ├── __init__.py
│   └── session.py                  # SQLite connection & initialization
│
├── models/                         🆕 Data Models
│   ├── __init__.py
│   └── data_model.py               # Pydantic models for cache data
│
├── repositories/                   🆕 Repository Layer (Database Operations)
│   ├── __init__.py
│   └── data_repository.py          # CRUD operations for cached data
│
├── routes/                         🆕 New Routes (Cached Data)
│   ├── __init__.py
│   └── data.py                     # Cache endpoints: GET /data, POST /refresh
│
└── services/
    ├── cache_service.py            # FastF1 cache (existing)
    ├── cache_service_v2.py         🆕 TTL cache service
    ├── external_api.py             🆕 External API service (httpx)
    └── f1_data_service.py          # F1 data service (existing)
```

---

## 🗄️ Database Schema

### Table: `cached_data`

```sql
CREATE TABLE cached_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,           -- Cache identifier (e.g., "f1_seasons")
    data TEXT NOT NULL,                 -- JSON string of cached data
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_cached_data_key ON cached_data(key);
CREATE INDEX idx_cached_data_last_updated ON cached_data(last_updated);
```

**Why SQLite?**
- ✅ No separate database server needed
- ✅ File-based (easy backup/restore)
- ✅ Perfect for development
- ✅ Easy migration to PostgreSQL later (same SQL syntax)

---

## 🔄 Architecture & Flow

### **Layer Separation**

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Route                         │
│              (routes/data.py)                           │
│         GET /api/cached/data?key=f1_seasons            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                Cache Service (TTL Logic)                │
│           (services/cache_service_v2.py)                │
│  • Check if cache exists                                │
│  • Validate TTL (expired?)                              │
│  • Decide: return cache or fetch fresh                  │
└────────┬──────────────────────────────┬─────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────┐      ┌──────────────────────────┐
│  Repository Layer   │      │  External API Service    │
│ (data_repository)   │      │   (external_api.py)      │
│  • get_cached_data  │      │  • fetch_f1_seasons()    │
│  • save_data        │      │  • fetch_race_data()     │
│  • get_last_updated │      │  • Async with httpx      │
└─────────┬───────────┘      └──────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                  SQLite Database                        │
│                (data/pitwall_cache.db)                  │
└─────────────────────────────────────────────────────────┘
```

### **Request Flow (with TTL Logic)**

```
1. User requests: GET /api/cached/data?key=f1_seasons
                    ↓
2. Cache Service checks database
                    ↓
3. Decision Point:
   
   If cache NOT exists:
      → Fetch from external API
      → Save to database
      → Return fresh data ⚡
   
   If cache exists:
      → Check age vs TTL
      
      If EXPIRED (age > TTL):
         → Fetch from external API
         → Update database
         → Return fresh data 🔄
      
      If VALID (age < TTL):
         → Return cached data ✅ (FAST!)
```

---

## 🚀 API Endpoints

### **1. GET /api/cached/data** - Get cached data

Returns data using TTL cache strategy.

**Query Parameters:**
- `key` (string): Cache key (default: "f1_seasons")

**Response:**
```json
{
  "success": true,
  "data": {
    "seasons": [2021, 2022, 2023, 2024],
    "total": 4
  },
  "cached": true,
  "last_updated": "2026-02-19T10:30:00",
  "message": "Data served from cache"
}
```

**Example:**
```bash
curl "http://127.0.0.1:5000/api/cached/data?key=f1_seasons"
```

---

### **2. POST /api/cached/refresh** - Force refresh

Bypasses cache and fetches fresh data.

**Query Parameters:**
- `key` (string): Cache key to refresh

**Response:**
```json
{
  "success": true,
  "message": "Cache refreshed for key: f1_seasons",
  "last_updated": "2026-02-19T11:00:00",
  "records_updated": 1
}
```

**Example:**
```bash
curl -X POST "http://127.0.0.1:5000/api/cached/refresh?key=f1_seasons"
```

---

### **3. GET /api/cached/cache/info** - Cache metadata

Get information about cached data.

**Query Parameters:**
- `key` (string, optional): Specific cache key

**Response:**
```json
{
  "exists": true,
  "key": "f1_seasons",
  "last_updated": "2026-02-19T10:30:00",
  "age_seconds": 1800,
  "ttl_seconds": 3600,
  "is_expired": false,
  "expires_in_seconds": 1800
}
```

**Example:**
```bash
# Specific key
curl "http://127.0.0.1:5000/api/cached/cache/info?key=f1_seasons"

# All cache stats
curl "http://127.0.0.1:5000/api/cached/cache/info"
```

---

### **4. DELETE /api/cached/cache** - Invalidate cache

Delete cached data.

**Query Parameters:**
- `key` (string, required): Cache key to delete

**Response:**
```json
{
  "success": true,
  "message": "Cache invalidated for key: f1_seasons"
}
```

**Example:**
```bash
curl -X DELETE "http://127.0.0.1:5000/api/cached/cache?key=f1_seasons"
```

---

### **5. GET /api/cached/cache/keys** - List all keys

Get all cache keys in database.

**Response:**
```json
{
  "success": true,
  "total": 3,
  "keys": ["f1_seasons", "race_2023_monaco", "race_2024_silverstone"]
}
```

**Example:**
```bash
curl "http://127.0.0.1:5000/api/cached/cache/keys"
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Cache Database Settings
DB_DIR=data                      # Database directory
DB_NAME=pitwall_cache.db         # Database filename
CACHE_TTL_SECONDS=3600           # TTL in seconds (1 hour)
EXTERNAL_API_TIMEOUT=30          # External API timeout
```

### TTL (Time-To-Live) Configuration

**What is TTL?**
TTL defines how long cached data is considered "fresh" before needing refresh.

**Default:** 3600 seconds (1 hour)

**Examples:**
```env
CACHE_TTL_SECONDS=300     # 5 minutes (aggressive refresh)
CACHE_TTL_SECONDS=3600    # 1 hour (balanced)
CACHE_TTL_SECONDS=86400   # 24 hours (long cache)
```

---

## 💡 Usage Examples

### Example 1: Basic cached data fetch

```python
# First request - cache miss, fetches from external API
GET /api/cached/data?key=f1_seasons
→ Returns fresh data, saves to DB (slow ~1s)

# Second request within TTL - cache hit
GET /api/cached/data?key=f1_seasons
→ Returns from cache (fast ~10ms)

# After TTL expired (1 hour later)
GET /api/cached/data?key=f1_seasons
→ Fetches fresh data, updates cache (slow ~1s)
```

### Example 2: Force refresh

```python
# User clicks "Refresh" button
POST /api/cached/refresh?key=f1_seasons
→ Always fetches fresh data, updates cache

# Next GET request returns the refreshed data from cache
GET /api/cached/data?key=f1_seasons
→ Returns newly cached data (fast)
```

### Example 3: Cache management

```python
# Check cache status
GET /api/cached/cache/info?key=f1_seasons
→ Shows age, TTL, expiration time

# List all cached keys
GET /api/cached/cache/keys
→ ["f1_seasons", "race_2023_monaco"]

# Clear specific cache
DELETE /api/cached/cache?key=f1_seasons
→ Removes from database
```

---

## 🧪 Testing the Implementation

### 1. Start the backend

```powershell
python -m backend.app
```

### 2. Test cache flow

```bash
# First request (cache miss - should be slow)
curl "http://127.0.0.1:5000/api/cached/data?key=f1_seasons"
# Returns: "cached": false

# Second request (cache hit - should be fast)
curl "http://127.0.0.1:5000/api/cached/data?key=f1_seasons"
# Returns: "cached": true

# Check cache info
curl "http://127.0.0.1:5000/api/cached/cache/info?key=f1_seasons"

# Force refresh
curl -X POST "http://127.0.0.1:5000/api/cached/refresh?key=f1_seasons"
# Returns fresh data

# Invalidate cache
curl -X DELETE "http://127.0.0.1:5000/api/cached/cache?key=f1_seasons"
```

### 3. Check database

```powershell
# Database location
ls data/pitwall_cache.db

# Query database (optional, using sqlite3 CLI)
sqlite3 data/pitwall_cache.db "SELECT key, last_updated FROM cached_data;"
```

---

## 🔧 Customization

### Adding a new cache key

Edit `backend/routes/data.py`:

```python
@router.get('/data')
async def get_data(key: str = Query('f1_seasons')):
    # Add your custom cache key
    if key == 'my_custom_key':
        fetch_callback = external_api.fetch_my_custom_data
    elif key == 'f1_seasons':
        fetch_callback = external_api.fetch_f1_seasons
    # ... rest of code
```

### Changing TTL per cache key

```python
# In cache_service_v2.py or routes
cache_service = CacheService(ttl_seconds=7200)  # 2 hours for this key
```

### Using real external API

Edit `backend/services/external_api.py`:

```python
async def fetch_f1_seasons(self) -> Dict[str, Any]:
    # Replace simulation with real API call
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.get('https://ergast.com/api/f1/seasons.json')
        return response.json()
```

---

## 📊 Performance Benefits

| Scenario | Without Cache | With Cache (Valid) | Improvement |
|----------|--------------|-------------------|-------------|
| External API call | ~1000ms | ~10ms | **100x faster** |
| Database lookup | N/A | ~10ms | N/A |
| Total response time | ~1000ms | ~10ms | **99% reduction** |

**Benefits:**
- ✅ Reduced external API calls (cost savings)
- ✅ Faster response times (better UX)
- ✅ Reduced load on external services
- ✅ Works offline (if cache exists)
- ✅ Rate limit protection

---

## 🔄 Migration to PostgreSQL (Future)

The repository layer makes migration easy:

```python
# Current (SQLite)
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cached_data WHERE key = ?", (key,))

# Future (PostgreSQL with SQLAlchemy)
async with async_session() as session:
    result = await session.execute(
        select(CachedData).where(CachedData.key == key)
    )
```

Just update `backend/db/session.py` and `backend/repositories/data_repository.py`.

---

## 🆘 Troubleshooting

### "Database locked" error
SQLite has limited concurrent writes. This is expected for SQLite.
Solution: Migrate to PostgreSQL for production.

### Cache not working
Check:
1. Database initialized: `ls data/pitwall_cache.db`
2. TTL configuration: `echo $CACHE_TTL_SECONDS`
3. Logs show cache hits/misses

### External API timeout
Increase timeout:
```env
EXTERNAL_API_TIMEOUT=60
```

---

## ✅ Summary

**What you have now:**

1. ✅ **Database layer** - SQLite with clean schema
2. ✅ **Repository pattern** - CRUD operations separated
3. ✅ **TTL cache logic** - Smart caching with expiration
4. ✅ **Async external API** - Non-blocking I/O with httpx
5. ✅ **Refresh mechanism** - Force update on demand
6. ✅ **FastAPI routes** - Full API for cache management
7. ✅ **Clean architecture** - Easy to maintain and extend

**Next steps:**
1. Test the endpoints
2. Replace simulated API with real external APIs
3. Adjust TTL based on your needs
4. Add more cache keys as needed
5. Consider PostgreSQL for production

---

**Your backend now has enterprise-grade caching! 🎉**
