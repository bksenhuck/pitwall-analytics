# Flask vs FastAPI - Side-by-Side Comparison

## Application Setup

### Flask (Before)
```python
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:8050"]}})

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
```

### FastAPI (After)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Pitwall Analytics API", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8050"])

@app.get('/api/health')
async def health_check():
    return {'status': 'healthy'}

if __name__ == '__main__':
    uvicorn.run("backend.app:app", host='127.0.0.1', port=5000, reload=True)
```

---

## Routing with Blueprints/Routers

### Flask Blueprint
```python
from flask import Blueprint, jsonify, request

data_bp = Blueprint('data', __name__)

@data_bp.route('/data/seasons', methods=['GET'])
def get_seasons():
    try:
        seasons = [2021, 2022, 2023, 2024]
        return jsonify({'success': True, 'data': seasons}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Register in main app
app.register_blueprint(data_bp, url_prefix='/api')
```

### FastAPI APIRouter
```python
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get('/data/seasons')
async def get_seasons():
    try:
        seasons = [2021, 2022, 2023, 2024]
        return {'success': True, 'data': seasons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include in main app
app.include_router(router, prefix="/api", tags=["Data"])
```

---

## Path Parameters

### Flask
```python
@data_bp.route('/data/races/<int:season>', methods=['GET'])
def get_races(season):
    races = f1_service.get_races_for_season(season)
    return jsonify({'data': races}), 200
```

### FastAPI
```python
@router.get('/data/races/{season}')
async def get_races(season: int):
    races = f1_service.get_races_for_season(season)
    return {'data': races}
```

---

## Query Parameters

### Flask
```python
@data_bp.route('/data/session', methods=['GET'])
def get_session_data():
    season = request.args.get('season', type=int)
    event = request.args.get('event', type=str)
    session_type = request.args.get('session_type', 'R', type=str)
    
    if not season or not event:
        return jsonify({'error': 'Missing parameters'}), 400
    
    data = f1_service.load_session_data(season, event, session_type)
    return jsonify({'data': data}), 200
```

### FastAPI
```python
from typing import Optional

@router.get('/data/session')
async def get_session_data(
    season: Optional[int] = Query(None, description="Season year"),
    event: Optional[str] = Query(None, description="Event name"),
    session_type: str = Query('R', description="Session type")
):
    if not season or not event:
        raise HTTPException(status_code=400, detail="Missing parameters")
    
    data = f1_service.load_session_data(season, event, session_type)
    return {'data': data}
```

---

## Request Body (POST)

### Flask
```python
from flask import request

@data_bp.route('/data/analyze', methods=['POST'])
def analyze_data():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    result = process_data(data)
    return jsonify({'result': result}), 200
```

### FastAPI
```python
from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    season: int
    event: str
    driver: str

@router.post('/data/analyze')
async def analyze_data(request: AnalysisRequest):
    # Data already validated by Pydantic
    result = process_data(request.dict())
    return {'result': result}
```

---

## Error Handling

### Flask
```python
@app.route('/api/data')
def get_data():
    try:
        data = fetch_data()
        return jsonify({'data': data}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### FastAPI
```python
@app.get('/api/data')
async def get_data():
    try:
        data = fetch_data()
        return {'data': data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## External API Calls

### Flask (Sync)
```python
import requests

@app.route('/api/external')
def get_external_data():
    response = requests.get('https://api.example.com/data')
    return jsonify(response.json()), 200
```

### FastAPI (Async)
```python
import httpx

@app.get('/api/external')
async def get_external_data():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com/data')
        return response.json()
```

---

## Multiple Concurrent Requests

### Flask (Sequential)
```python
import requests

@app.route('/api/multi')
def fetch_multiple():
    # These run one after another (slow)
    r1 = requests.get('https://api1.com')
    r2 = requests.get('https://api2.com')
    r3 = requests.get('https://api3.com')
    
    return jsonify({
        'data1': r1.json(),
        'data2': r2.json(),
        'data3': r3.json()
    })
```

### FastAPI (Concurrent)
```python
import httpx
import asyncio

@app.get('/api/multi')
async def fetch_multiple():
    async with httpx.AsyncClient() as client:
        # These run concurrently (fast!)
        results = await asyncio.gather(
            client.get('https://api1.com'),
            client.get('https://api2.com'),
            client.get('https://api3.com')
        )
    
    return {
        'data1': results[0].json(),
        'data2': results[1].json(),
        'data3': results[2].json()
    }
```

---

## Dependency Injection

### Flask (Manual)
```python
from flask import g

@app.before_request
def get_db():
    g.db = Database()

@app.route('/api/users')
def get_users():
    users = g.db.get_users()
    return jsonify(users)
```

### FastAPI (Built-in)
```python
from fastapi import Depends

def get_db():
    db = Database()
    try:
        yield db
    finally:
        db.close()

@app.get('/api/users')
async def get_users(db: Database = Depends(get_db)):
    users = db.get_users()
    return users
```

---

## Startup/Shutdown Events

### Flask
```python
@app.before_first_request
def startup():
    init_cache()

# No built-in shutdown event
```

### FastAPI
```python
@app.on_event("startup")
async def startup_event():
    init_cache()

@app.on_event("shutdown")
async def shutdown_event():
    cleanup_resources()
```

---

## Response Models

### Flask
```python
@app.route('/api/user/<int:user_id>')
def get_user(user_id):
    user = db.get_user(user_id)
    # Manual serialization
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email
    })
```

### FastAPI
```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

@app.get('/api/user/{user_id}', response_model=User)
async def get_user(user_id: int):
    user = db.get_user(user_id)
    # Automatic serialization + validation
    return user
```

---

## API Documentation

### Flask
```python
# Manual - need to install flask-swagger or similar
# Write YAML/JSON specs manually
```

### FastAPI
```python
# Automatic!
# Just add docstrings and type hints

@app.get('/api/data')
async def get_data(
    season: int = Query(..., description="F1 season year", example=2023)
):
    """
    Get F1 data for a specific season.
    
    Returns race and driver information.
    """
    return {'data': fetch_data(season)}

# Auto-generates Swagger UI at /docs
```

---

## Testing

### Flask
```python
import pytest

def test_health_check(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
```

### FastAPI
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get('/api/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'healthy'
```

---

## Summary

| Feature | Flask | FastAPI |
|---------|-------|---------|
| **Server** | WSGI (Gunicorn) | ASGI (Uvicorn) |
| **Async** | ❌ No | ✅ Yes |
| **Type Hints** | Optional | Required |
| **Validation** | Manual | Automatic (Pydantic) |
| **API Docs** | Manual | Auto-generated |
| **Performance** | Good | Better (async) |
| **Learning Curve** | Easy | Medium |
| **Maturity** | Very mature | Growing fast |

---

**Conclusion:** FastAPI is the modern choice for async Python APIs with better performance, automatic documentation, and built-in validation. Perfect for your F1 analytics backend! 🚀
