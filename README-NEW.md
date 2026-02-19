# 🏁 Pitwall Analytics - Refactored Architecture

> A scalable F1 analytics platform with clean backend/frontend separation

## 📋 Table of Contents
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Development Guide](#development-guide)
- [Migration Strategy](#migration-strategy)

---

## 🏗️ Architecture Overview

This project follows a **clean separation of concerns** architecture:

### Backend (Flask API)
- **Purpose**: Data processing, business logic, external API calls
- **Technology**: Flask REST API
- **Why Flask?** Lightweight, already integrated with Dash, perfect for serving APIs
- **Port**: `5000` (default)

### Frontend (Dash UI)
- **Purpose**: User interface, visualization, user interactions
- **Technology**: Plotly Dash
- **Responsibilities**: ONLY layout, callbacks, and API calls (no data processing)
- **Port**: `8050` (default)

### Data Flow
```
User → Dash UI → HTTP Request → Flask Backend → FastF1 API
                                      ↓
User ← Dash Charts ← JSON Response ← Data Processing
```

---

## 📁 Project Structure

```
pitwall-analytics/
│
├── backend/                    # Backend Flask API
│   ├── app.py                  # Flask application entry point
│   ├── config.py               # Configuration management
│   ├── api/                    # API routes/endpoints
│   │   ├── health.py           # Health check endpoints
│   │   └── data.py             # Data endpoints
│   └── services/               # Business logic layer
│       ├── f1_data_service.py  # F1 data processing
│       └── cache_service.py    # Caching logic
│
├── frontend/                   # Frontend Dash application
│   ├── app.py                  # Dash entry point
│   ├── config.py               # Frontend configuration
│   ├── components/             # Reusable UI components
│   │   ├── navigation.py       # Navigation bar
│   │   └── charts.py           # Chart components
│   ├── pages/                  # Dash pages
│   │   ├── home.py
│   │   ├── analytics.py
│   │   └── live.py
│   └── assets/                 # Static files (CSS)
│       └── style.css
│
├── shared/                     # Shared utilities
│   └── utils.py
│
├── .env                        # Environment variables (local)
├── .env.example                # Environment template
├── requirements-new.txt        # Python dependencies
├── run.py                      # Development server launcher
├── ARCHITECTURE.md             # Detailed architecture docs
└── README-NEW.md               # This file
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. **Clone or navigate to the project**
   ```powershell
   cd pitwall-analytics
   ```

2. **Create virtual environment** (if not exists)
   ```powershell
   python -m venv venv_pitwall_analytics
   ```

3. **Activate virtual environment**
   ```powershell
   # Windows PowerShell
   .\venv_pitwall_analytics\Scripts\Activate.ps1
   
   # Windows CMD
   .\venv_pitwall_analytics\Scripts\activate.bat
   ```

4. **Install dependencies**
   ```powershell
   pip install -r requirements-new.txt
   ```

5. **Configure environment**
   ```powershell
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env if needed (optional for local development)
   ```

---

## 🎯 Running the Application

### Option 1: Run Both Services (Recommended for Development)
```powershell
python run.py both
```

This will:
- Start backend API on http://127.0.0.1:5000
- Start frontend UI on http://127.0.0.1:8050
- Open http://127.0.0.1:8050 in your browser

### Option 2: Run Services Separately

**Terminal 1 - Backend:**
```powershell
python -m backend.app
```

**Terminal 2 - Frontend:**
```powershell
python -m frontend.app
```

### Option 3: Run Individual Services

**Backend only:**
```powershell
python run.py backend
```

**Frontend only:**
```powershell
python run.py frontend
```

---

## 📡 API Documentation

### Health Endpoints

#### `GET /api/health`
Check if backend is running
```json
{
  "status": "healthy",
  "timestamp": "2026-02-19T10:00:00",
  "service": "pitwall-analytics-backend"
}
```

#### `GET /api/status`
Detailed status including cache info
```json
{
  "status": "running",
  "timestamp": "2026-02-19T10:00:00",
  "cache": {
    "enabled": true,
    "directory": ".ff1cache"
  },
  "version": "1.0.0"
}
```

### Data Endpoints

#### `GET /api/data/seasons`
Get available F1 seasons
```json
{
  "success": true,
  "data": [2021, 2022, 2023, 2024]
}
```

#### `GET /api/data/races/:season`
Get races for a season
```json
{
  "success": true,
  "data": [
    {
      "round": 1,
      "name": "Bahrain",
      "location": "Bahrain",
      "date": "2023-03-05"
    }
  ]
}
```

#### `GET /api/data/session?season=2023&event=Monaco`
Get session data with laps
```json
{
  "success": true,
  "data": {
    "session": {...},
    "drivers": ["VER", "HAM", "LEC"],
    "laps": [...],
    "total_laps": 1234
  }
}
```

---

## 🛠️ Development Guide

### Adding a New API Endpoint

1. **Create endpoint in `backend/api/data.py`**:
```python
@data_bp.route('/data/myendpoint', methods=['GET'])
def get_my_data():
    # Delegate to service layer
    result = f1_service.my_business_logic()
    return jsonify({'success': True, 'data': result})
```

2. **Add business logic in `backend/services/f1_data_service.py`**:
```python
def my_business_logic(self):
    # Process data here
    return processed_data
```

3. **Call from frontend `frontend/pages/analytics.py`**:
```python
response = requests.get(f"{config.BACKEND_API_URL}/data/myendpoint")
data = response.json()
```

### Adding a New Page

1. **Create page file in `frontend/pages/mypage.py`**:
```python
import dash
from dash import html

dash.register_page(__name__, path="/mypage", name="My Page")

layout = html.Div([
    html.H1("My Page")
])
```

2. **Add navigation link in `frontend/app.py`**:
```python
dcc.Link("My Page", href="/mypage", className="nav-link")
```

---

## 🔄 Migration Strategy

### Gradual Migration (Recommended)

Your **current app continues to work**. Migrate piece by piece:

1. **Phase 1**: Test new architecture
   - Run new structure alongside old code
   - Verify endpoints work: http://127.0.0.1:5000/api/health

2. **Phase 2**: Migrate data processing
   - Move logic from `data_loader.py` to `backend/services/f1_data_service.py`
   - Create API endpoints for each function
   - Test endpoints

3. **Phase 3**: Update Dash callbacks
   - Replace direct data calls with API requests
   - Update callbacks one page at a time
   - Start with simple pages (home), then complex (analytics)

4. **Phase 4**: Move UI components
   - Extract charts from `charts.py` to `frontend/components/charts.py`
   - Refactor pages to use new components

5. **Phase 5**: Clean up
   - Remove old files once fully migrated
   - Update documentation

### Quick Test

Test the new architecture works:

```powershell
# Terminal 1: Start backend
python -m backend.app

# Terminal 2: Test API
curl http://127.0.0.1:5000/api/health

# Terminal 3: Start frontend
python -m frontend.app

# Browser: http://127.0.0.1:8050
```

---

## 🐳 Docker Ready

The structure is ready for Docker. Example:

```dockerfile
# Backend Dockerfile
FROM python:3.11
WORKDIR /app
COPY backend/ ./backend/
COPY shared/ ./shared/
COPY requirements-new.txt .
RUN pip install -r requirements-new.txt
CMD ["python", "-m", "backend.app"]
```

```dockerfile
# Frontend Dockerfile
FROM python:3.11
WORKDIR /app
COPY frontend/ ./frontend/
COPY shared/ ./shared/
COPY requirements-new.txt .
RUN pip install -r requirements-new.txt
CMD ["python", "-m", "frontend.app"]
```

---

## 📝 Best Practices

### Backend
- ✅ Keep API endpoints thin (controllers)
- ✅ Put logic in services layer
- ✅ Return consistent JSON structure
- ✅ Handle errors gracefully
- ✅ Use environment variables for config

### Frontend
- ✅ No data processing in Dash callbacks
- ✅ Only make API calls and update UI
- ✅ Reuse components
- ✅ Handle loading/error states
- ✅ Show user-friendly error messages

### General
- ✅ Keep `.env` out of git (already in `.gitignore`)
- ✅ Document API endpoints
- ✅ Write tests (add `pytest` when ready)
- ✅ Use type hints
- ✅ Follow PEP 8 style guide

---

## 🧪 Testing

```powershell
# Install test dependencies
pip install pytest pytest-cov

# Run tests (when you add them)
pytest

# With coverage
pytest --cov=backend --cov=frontend
```

---

## 🤝 Contributing

1. Create feature branch
2. Make changes following architecture
3. Test both backend and frontend
4. Submit pull request

---

## 📞 Support

For issues or questions:
- Check `ARCHITECTURE.md` for detailed design docs
- Review API documentation above
- Check logs in console

---

## 🎉 Next Steps

1. ✅ Run `python run.py both`
2. ✅ Visit http://127.0.0.1:8050
3. ✅ Test analytics page with backend integration
4. 🔜 Start migrating your existing code gradually
5. 🔜 Add more endpoints as needed
6. 🔜 Enhance with authentication, database, etc.

---

**Built with ❤️ for F1 analytics**
