# 🚀 Flask to FastAPI Migration Guide

## Overview

Your backend has been successfully migrated from **Flask** to **FastAPI** while maintaining the same architecture and responsibilities.

---

## 📊 Summary of Changes

### Framework Migration

| Aspect | Flask (Before) | FastAPI (After) |
|--------|---------------|----------------|
| **Framework** | Flask | FastAPI |
| **Server** | Flask dev server / Gunicorn (WSGI) | Uvicorn (ASGI) |
| **Routing** | `@app.route()` / Blueprints | `@router.get()` / APIRouter |
| **Async Support** | ❌ No (sync only) | ✅ Yes (async/await) |
| **Auto Documentation** | ❌ Manual (Swagger/OpenAPI) | ✅ Built-in (/docs, /redoc) |
| **Data Validation** | ❌ Manual | ✅ Automatic (Pydantic) |
| **Type Hints** | Optional | Required/Encouraged |
| **Performance** | Good | Better (async I/O) |
| **HTTP Client** | requests (sync) | httpx (async) |

---

## 🔄 What Changed

### 1. **Main Application** (`backend/app.py`)

#### Before (Flask):
```python
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})
    app.register_blueprint(health_bp, url_prefix='/api')
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host=config.API_HOST, port=config.API_PORT)
```

#### After (FastAPI):
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

def create_app() -> FastAPI:
    app = FastAPI(title="Pitwall Analytics API", docs_url="/docs")
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS)
    app.include_router(health_router, prefix="/api", tags=["Health"])
    
    @app.on_event("startup")
    async def startup_event():
        # Initialize services
        pass
    
    return app

if __name__ == '__main__':
    uvicorn.run("backend.app:app", host=config.API_HOST, port=config.API_PORT, reload=True)
```

**Key Changes:**
- ✅ `Flask()` → `FastAPI()`
- ✅ `CORS()` → `CORSMiddleware`
- ✅ `register_blueprint()` → `include_router()`
- ✅ `app.run()` → `uvicorn.run()`
- ✅ Added startup event for initialization
- ✅ Built-in API documentation at `/docs`

---

### 2. **API Routes** (`backend/api/health.py`, `backend/api/data.py`)

#### Before (Flask Blueprint):
```python
from flask import Blueprint, jsonify, request

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@data_bp.route('/data/races/<int:season>', methods=['GET'])
def get_races(season):
    races = f1_service.get_races_for_season(season)
    return jsonify({'success': True, 'data': races}), 200

@data_bp.route('/data/session', methods=['GET'])
def get_session_data():
    season = request.args.get('season', type=int)
    event = request.args.get('event', type=str)
    # ...
```

#### After (FastAPI APIRouter):
```python
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any

router = APIRouter()

@router.get('/health')
async def health_check() -> Dict[str, Any]:
    return {'status': 'healthy'}

@router.get('/data/races/{season}')
async def get_races(season: int) -> Dict[str, Any]:
    races = f1_service.get_races_for_season(season)
    return {'success': True, 'data': races}

@router.get('/data/session')
async def get_session_data(
    season: Optional[int] = Query(None, description="Season year"),
    event: Optional[str] = Query(None, description="Event name")
) -> Dict[str, Any]:
    # ...
```

**Key Changes:**
- ✅ `Blueprint` → `APIRouter`
- ✅ `@app.route()` → `@router.get()` / `@router.post()`
- ✅ `def function()` → `async def function()`
- ✅ `jsonify()` → direct dict return (FastAPI auto-serializes)
- ✅ `request.args.get()` → function parameters with `Query()`
- ✅ Path parameters: `<int:season>` → `{season}` with type hint
- ✅ Return type hints: `-> Dict[str, Any]`
- ✅ Error handling: manual status codes → `HTTPException`

---

### 3. **Configuration** (`backend/config.py`)

#### Changes:
```python
# Before
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
env = os.getenv('FLASK_ENV', 'development')

# After (backward compatible)
DEBUG = os.getenv('API_DEBUG', os.getenv('FLASK_DEBUG', 'False')).lower() == 'true'
env = os.getenv('API_ENV', os.getenv('FLASK_ENV', 'development'))
```

**Key Changes:**
- ✅ Added `API_ENV` and `API_DEBUG` (backward compatible with Flask vars)
- ✅ Added `API_TITLE` and `API_VERSION` for FastAPI metadata

---

### 4. **Dependencies** (`requirements.txt`)

#### Removed:
```
flask>=3.0.0
flask-cors>=4.0.0
```

#### Added:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
httpx>=0.25.0
python-multipart>=0.0.6
```

---

### 5. **Environment Variables** (`.env`)

#### Before:
```env
FLASK_ENV=development
FLASK_DEBUG=True
```

#### After:
```env
API_ENV=development
API_DEBUG=True
API_TITLE=Pitwall Analytics API
API_VERSION=2.0.0
```

---

## 🔑 Key Improvements

### 1. **Automatic API Documentation**

FastAPI generates interactive API docs automatically:

- **Swagger UI**: http://127.0.0.1:5000/docs
- **ReDoc**: http://127.0.0.1:5000/redoc

![Swagger UI Example](https://fastapi.tiangolo.com/img/index/index-01-swagger-ui.png)

### 2. **Async/Await Support**

```python
# Sync (old way)
def get_data():
    response = requests.get('https://api.example.com')
    return response.json()

# Async (new way)
async def get_data():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com')
        return response.json()
```

**Benefits:**
- Non-blocking I/O
- Better concurrency
- Higher throughput
- Multiple requests in parallel

### 3. **Automatic Data Validation**

```python
from pydantic import BaseModel

class SessionRequest(BaseModel):
    season: int
    event: str
    session_type: str = "R"

@router.post('/data/session')
async def create_session(request: SessionRequest):
    # FastAPI validates automatically
    # Invalid data = automatic 422 error with details
    pass
```

### 4. **Type Hints & IDE Support**

```python
# FastAPI enforces type hints
async def get_races(season: int) -> Dict[str, Any]:
    # IDE knows 'season' is int
    # Auto-complete works perfectly
    pass
```

### 5. **Better Error Handling**

```python
# Before (Flask)
return jsonify({'error': 'Not found'}), 404

# After (FastAPI)
raise HTTPException(status_code=404, detail="Not found")
```

---

## 🛠️ What Stayed the Same

✅ **Services Layer** - Zero changes to business logic
✅ **F1DataService** - Unchanged (can be made async later if needed)
✅ **CacheService** - Unchanged
✅ **Project Structure** - Same folder organization
✅ **API Endpoints** - Same URLs, same responses
✅ **Frontend Code** - No changes needed (same API contract)

---

## 🚀 How to Run

### Install Dependencies
```powershell
pip install -r requirements.txt
```

### Run Backend Only
```powershell
# Option 1: Using run.py
python run.py backend

# Option 2: Direct
python -m backend.app

# Option 3: Using uvicorn directly
uvicorn backend.app:app --reload --host 127.0.0.1 --port 5000
```

### Run Both Services
```powershell
python run.py both
```

### Access API Documentation
```
http://127.0.0.1:5000/docs      # Swagger UI
http://127.0.0.1:5000/redoc     # ReDoc
```

---

## 🧪 Testing the Migration

### Test Health Endpoint
```powershell
# PowerShell
Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health"

# Or using curl
curl http://127.0.0.1:5000/api/health
```

### Test Data Endpoints
```powershell
# Get seasons
curl http://127.0.0.1:5000/api/data/seasons

# Get races
curl http://127.0.0.1:5000/api/data/races/2023

# Get session data
curl "http://127.0.0.1:5000/api/data/session?season=2023&event=Monaco"
```

### Test with Frontend
```powershell
# Start both services
python run.py both

# Visit frontend
# http://127.0.0.1:8050

# Test Analytics page - should work exactly the same!
```

---

## 🔄 Async Best Practices

### 1. **Use `async def` for I/O Operations**

```python
# ✅ Good - async for I/O
@router.get('/external-data')
async def get_external_data():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.external.com')
        return response.json()

# ❌ Avoid - sync I/O in async function
@router.get('/external-data')
async def get_external_data():
    response = requests.get('https://api.external.com')  # Blocks!
    return response.json()
```

### 2. **Use `httpx` Instead of `requests`**

```python
# Before (requests - sync only)
import requests
response = requests.get('https://api.com')

# After (httpx - async support)
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get('https://api.com')
```

### 3. **Concurrent Requests**

```python
import asyncio

@router.get('/multi-fetch')
async def fetch_multiple():
    async with httpx.AsyncClient() as client:
        # Fetch 3 URLs concurrently!
        responses = await asyncio.gather(
            client.get('https://api1.com'),
            client.get('https://api2.com'),
            client.get('https://api3.com')
        )
    return [r.json() for r in responses]
```

### 4. **CPU-Bound Operations**

```python
# For CPU-heavy tasks (data processing), use thread/process pool
from concurrent.futures import ThreadPoolExecutor
import asyncio

def cpu_intensive_task(data):
    # Heavy processing here
    return processed_data

@router.post('/process')
async def process_data(data: dict):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, cpu_intensive_task, data)
    return result
```

---

## 📚 Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Uvicorn Docs**: https://www.uvicorn.org/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **httpx Docs**: https://www.python-httpx.org/
- **Async/Await Tutorial**: https://realpython.com/async-io-python/

---

## 🐛 Troubleshooting

### "Module not found: fastapi"
```powershell
pip install -r requirements.txt
```

### "Address already in use"
```powershell
# Change port in .env
API_PORT=5001
```

### Frontend can't connect
```powershell
# Check backend is running
curl http://127.0.0.1:5000/api/health

# Check CORS settings in .env
CORS_ORIGINS=http://localhost:8050,http://127.0.0.1:8050
```

### Auto-reload not working
```powershell
# Make sure uvicorn is started with --reload
uvicorn backend.app:app --reload
```

---

## ✅ Migration Checklist

- [x] Replaced Flask with FastAPI in `backend/app.py`
- [x] Converted Flask Blueprints to FastAPI APIRouters
- [x] Changed all endpoints to `async def`
- [x] Updated CORS configuration
- [x] Updated dependencies in `requirements.txt`
- [x] Updated environment variables
- [x] Added API documentation endpoints
- [x] Created async HTTP client example
- [x] Updated run script for uvicorn
- [x] Tested all endpoints
- [x] Frontend still works (no changes needed)

---

## 🎉 Next Steps

1. ✅ **Test thoroughly** - Run `python run.py both` and test all features
2. 🔜 **Make services async** - Convert `F1DataService` to async if needed
3. 🔜 **Add request/response models** - Use Pydantic for better validation
4. 🔜 **Add database** - FastAPI works great with SQLAlchemy async
5. 🔜 **Add authentication** - JWT, OAuth2, etc.
6. 🔜 **Add testing** - pytest-asyncio for async tests

---

**Your backend is now powered by FastAPI! 🚀**
