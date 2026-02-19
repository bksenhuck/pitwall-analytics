# Pitwall Analytics - Architecture

## 📁 Folder Structure

```
pitwall-analytics/
│
├── backend/                    # Backend service (Flask API)
│   ├── __init__.py
│   ├── app.py                  # Flask application entry point
│   ├── config.py               # Configuration management
│   │
│   ├── api/                    # API routes/controllers
│   │   ├── __init__.py
│   │   ├── health.py           # Health check endpoints
│   │   └── data.py             # Data endpoints
│   │
│   └── services/               # Business logic layer
│       ├── __init__.py
│       ├── f1_data_service.py  # F1 data processing
│       └── cache_service.py    # Caching logic
│
├── frontend/                   # Frontend Dash application
│   ├── __init__.py
│   ├── app.py                  # Dash app entry point
│   ├── config.py               # Frontend configuration
│   │
│   ├── components/             # Reusable UI components
│   │   ├── __init__.py
│   │   ├── navigation.py       # Navigation bar
│   │   └── charts.py           # Chart components
│   │
│   ├── callbacks/              # Dash callbacks
│   │   ├── __init__.py
│   │   └── analytics_callbacks.py
│   │
│   ├── pages/                  # Dash pages
│   │   ├── __init__.py
│   │   ├── home.py
│   │   ├── analytics.py
│   │   └── live.py
│   │
│   └── assets/                 # Static files
│       └── style.css
│
├── shared/                     # Shared utilities/models
│   ├── __init__.py
│   └── utils.py
│
├── .env.example                # Environment variables template
├── .env                        # Local environment (gitignored)
├── requirements.txt            # Python dependencies
├── README.md                   # Setup and run instructions
└── run.py                      # Unified dev server launcher
```

## 🏗️ Architecture Principles

### Backend (Flask)
**Why Flask?** Already integrated with Dash, lightweight, perfect for serving APIs to Dash frontend

**Responsibilities:**
- Data processing (FastF1 API calls)
- Business logic (lap analysis, telemetry processing)
- External API calls
- Caching strategy
- Future: ML models, advanced analytics

**Layers:**
- `api/`: HTTP endpoints (thin controllers)
- `services/`: Business logic (heavy lifting)
- `config.py`: Environment-based configuration

### Frontend (Dash)
**Responsibilities:**
- UI layout and components
- User interactions
- Data visualization
- Callbacks that fetch from backend API

**Layers:**
- `pages/`: Multi-page routing
- `components/`: Reusable UI elements
- `callbacks/`: Event handlers that call backend

### Data Flow
```
User Interaction (Dash UI)
    ↓
Dash Callback triggered
    ↓
HTTP Request to Backend API
    ↓
Backend Service processes (FastF1, analytics)
    ↓
JSON Response
    ↓
Dash updates UI (charts, tables)
```

## 🚀 Future Scalability

This structure supports:
- **Microservices**: Backend can be split into multiple services
- **Docker**: Each layer can be containerized independently
- **API Gateway**: Add authentication, rate limiting
- **Database**: Add data persistence layer in backend/services
- **Testing**: Clear separation enables isolated unit/integration tests
- **CI/CD**: Independent deployment pipelines

## 🔄 Migration Strategy

1. Start by moving data processing logic to `backend/services/`
2. Create API endpoints in `backend/api/`
3. Update Dash callbacks to call backend APIs instead of direct processing
4. Move charts to `frontend/components/`
5. Refactor pages one at a time

Keep old code running while gradually migrating to new structure.
