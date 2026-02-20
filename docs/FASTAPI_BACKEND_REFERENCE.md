# FastAPI Backend - Quick Reference

## 🗂️ Updated Backend Structure

```
backend/
├── __init__.py
├── app.py                          # ⭐ FastAPI application (migrated from Flask)
├── config.py                       # Updated for FastAPI compatibility
│
├── api/                            # API Routes (APIRouters)
│   ├── __init__.py
│   ├── health.py                   # ⭐ Health endpoints (async)
│   └── data.py                     # ⭐ Data endpoints (async)
│
└── services/                       # Business Logic (unchanged)
    ├── __init__.py
    ├── cache_service.py            # FastF1 cache management
    ├── f1_data_service.py          # F1 data processing
    └── async_api_client.py         # ⭐ NEW: Async HTTP client example
```

---

## 🔑 Key Files Changed

### 1. `backend/app.py` - FastAPI Application

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

def create_app() -> FastAPI:
    app = FastAPI(
        title="Pitwall Analytics API",
        version="2.0.0",
        docs_url="/docs"  # 📚 Auto-generated API docs
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Register routers
    app.include_router(health_router, prefix="/api", tags=["Health"])
    app.include_router(data_router, prefix="/api", tags=["Data"])
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        init_cache(config.CACHE_DIR, config.CACHE_ENABLED)
    
    return app

app = create_app()

if __name__ == '__main__':
    uvicorn.run("backend.app:app", reload=True)
```

**Key Features:**
- ✅ ASGI instead of WSGI
- ✅ Automatic API documentation at `/docs`
- ✅ Type hints and validation
- ✅ Async/await support

---

### 2. `backend/api/health.py` - Health Endpoints

```python
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get('/health')
async def health_check() -> Dict[str, Any]:
    return {
        'status': 'healthy',
        'service': 'pitwall-analytics-backend'
    }

@router.get('/status')
async def status() -> Dict[str, Any]:
    return {
        'status': 'running',
        'cache': get_cache_status(),
        'version': '2.0.0-fastapi'
    }
```

**Changed:**
- ✅ `Blueprint` → `APIRouter`
- ✅ `def` → `async def`
- ✅ `jsonify()` → direct dict return
- ✅ Type hints added

---

### 3. `backend/api/data.py` - Data Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional

router = APIRouter()
f1_service = F1DataService()

@router.get('/data/seasons')
async def get_seasons() -> Dict[str, Any]:
    try:
        seasons = f1_service.get_available_seasons()
        return {'success': True, 'data': seasons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/data/races/{season}')
async def get_races(season: int) -> Dict[str, Any]:
    races = f1_service.get_races_for_season(season)
    return {'success': True, 'data': races}

@router.get('/data/session')
async def get_session_data(
    season: Optional[int] = Query(None, description="Season year"),
    event: Optional[str] = Query(None, description="Event name"),
    session_type: str = Query('R', description="Session type")
) -> Dict[str, Any]:
    if not season or not event:
        raise HTTPException(status_code=400, detail="Missing parameters")
    
    data = f1_service.load_session_data(season, event, session_type)
    return {'success': True, 'data': data}
```

**Changed:**
- ✅ Path parameters: `<int:season>` → `{season}` with type hint
- ✅ Query params: `request.args.get()` → function parameters with `Query()`
- ✅ Error handling: tuple returns → `HTTPException`
- ✅ All functions are async

---

### 4. `backend/services/async_api_client.py` - NEW!

```python
import httpx
from typing import Dict, Any

class AsyncAPIClient:
    async def fetch_external_data(self, url: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
```

**Use Case:**
```python
@router.get('/external-weather')
async def get_weather():
    client = AsyncAPIClient()
    data = await client.fetch_external_data("https://api.weather.com/current")
    return {'weather': data}
```

---

## 📦 Dependencies

### Removed:
```
flask
flask-cors
```

### Added:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
httpx>=0.25.0
python-multipart>=0.0.6
```

---

## 🚀 Running the Backend

### Method 1: Using run.py (Recommended)
```powershell
python run.py backend
```

### Method 2: Direct execution
```powershell
python -m backend.app
```

### Method 3: Using uvicorn CLI
```powershell
uvicorn backend.app:app --reload --host 127.0.0.1 --port 5000
```

---

## 📚 API Documentation

FastAPI automatically generates interactive API documentation:

### Swagger UI (Recommended)
```
http://127.0.0.1:5000/docs
```

### ReDoc (Alternative)
```
http://127.0.0.1:5000/redoc
```

### OpenAPI JSON
```
http://127.0.0.1:5000/openapi.json
```

---

## 🔗 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/status` | Detailed status with cache info |
| GET | `/api/data/seasons` | Get available seasons |
| GET | `/api/data/races/{season}` | Get races for season |
| GET | `/api/data/session?season=X&event=Y` | Get session data |
| GET | `/api/data` | Sample endpoint |

---

## 🧪 Testing Endpoints

### Using curl:
```bash
# Health check
curl http://127.0.0.1:5000/api/health

# Get seasons
curl http://127.0.0.1:5000/api/data/seasons

# Get races
curl http://127.0.0.1:5000/api/data/races/2023

# Get session
curl "http://127.0.0.1:5000/api/data/session?season=2023&event=Monaco"
```

### Using PowerShell:
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health" | ConvertFrom-Json
```

### Using Browser:
Just visit http://127.0.0.1:5000/docs and test interactively!

---

## ⚡ Async Patterns

### Single Request
```python
@router.get('/fetch')
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com')
        return response.json()
```

### Multiple Concurrent Requests
```python
import asyncio

@router.get('/fetch-multiple')
async def fetch_multiple():
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            client.get('https://api1.com'),
            client.get('https://api2.com'),
            client.get('https://api3.com')
        )
    return [r.json() for r in results]
```

### CPU-Bound Tasks
```python
from concurrent.futures import ThreadPoolExecutor

@router.post('/process')
async def process_heavy_data(data: dict):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, heavy_function, data)
    return result
```

---

## 🔧 Configuration

### Environment Variables (.env)
```env
# Backend API
API_ENV=development
API_DEBUG=True
API_HOST=127.0.0.1
API_PORT=5000
API_TITLE=Pitwall Analytics API
API_VERSION=2.0.0

# Cache
CACHE_DIR=.ff1cache
CACHE_ENABLED=True

# CORS
CORS_ORIGINS=http://localhost:8050,http://127.0.0.1:8050
```

---

## 📊 Performance Benefits

| Feature | Flask (Before) | FastAPI (After) |
|---------|---------------|----------------|
| **Async I/O** | ❌ No | ✅ Yes |
| **Concurrent Requests** | Limited by threads | Unlimited (async) |
| **Request Validation** | Manual | Automatic |
| **API Docs** | Manual | Auto-generated |
| **Type Safety** | Optional | Built-in |
| **Performance** | Good | Excellent |

---

## 🎯 What's Next?

1. ✅ **Test the migration** - Run and verify all endpoints work
2. 🔜 **Convert services to async** - Make `F1DataService` async
3. 🔜 **Add Pydantic models** - Better request/response validation
4. 🔜 **Add authentication** - JWT tokens, OAuth2
5. 🔜 **Add database** - SQLAlchemy with async support
6. 🔜 **Add WebSockets** - For live data streaming

---

## 🆘 Quick Troubleshooting

### Backend won't start
```powershell
# Check dependencies
pip install -r requirements.txt

# Check port availability
netstat -ano | findstr :5000
```

### "Module not found: uvicorn"
```powershell
pip install "uvicorn[standard]"
```

### Frontend can't connect
```powershell
# Verify backend is running
curl http://127.0.0.1:5000/api/health

# Check CORS in .env
CORS_ORIGINS=http://localhost:8050,http://127.0.0.1:8050
```

---

## 📚 Resources

- **FastAPI Tutorial**: https://fastapi.tiangolo.com/tutorial/
- **API Docs**: http://127.0.0.1:5000/docs (when running)
- **Migration Guide**: See `FLASK_TO_FASTAPI_MIGRATION.md`

---

**Backend successfully migrated to FastAPI! 🚀**
