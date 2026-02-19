"""
Aplicação principal para PRODUÇÃO.

Integra o backend FastAPI e o frontend Dash em um único servidor.
Ideal para deploy em plataformas como Render, Heroku, Railway, etc.

Arquitetura:
- FastAPI serve API REST em /api/*
- Dash app montado em / (raiz)
- Tudo roda em uma única porta
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from backend.config import get_config
import uvicorn

# Importar o Dash app
import dash
from dash import html, dcc
import data_loader


def create_production_app() -> FastAPI:
    """
    Cria aplicação unificada para produção (FastAPI + Dash).
    
    Estrutura de rotas:
    - /api/*       -> FastAPI backend
    - /docs        -> Documentação automática da API
    - /*           -> Dash frontend (todas as outras rotas)
    
    Returns:
        FastAPI app com Dash montado
    """
    config = get_config()
    
    # ==========================================
    # 1. Criar FastAPI app (Backend)
    # ==========================================
    app = FastAPI(
        title="Pitwall Analytics",
        description="F1 Race Analytics - Unified API + Frontend",
        version="2.0.0",
        docs_url="/api/docs",  # Movido para /api/docs
        redoc_url="/api/redoc"
    )
    
    # CORS (caso precise fazer requests de outros domínios)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, especifique domínios
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Registrar routers da API
    from backend.api.health import router as health_router
    from backend.api.data import router as data_router
    from backend.routes.data import router as cached_data_router
    
    app.include_router(health_router, prefix="/api", tags=["Health"])
    app.include_router(data_router, prefix="/api", tags=["Data"])
    app.include_router(cached_data_router, prefix="/api/cached", tags=["Cached Data"])
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        from backend.services.cache_service import init_cache
        init_cache(config.CACHE_DIR, config.CACHE_ENABLED)
        print("✅ FastF1 cache initialized")
        
        from backend.db.session import init_database
        init_database()
        print("✅ SQLite cache database initialized")
    
    # ==========================================
    # 2. Criar Dash app (Frontend)
    # ==========================================
    data_loader.enable_cache(".ff1cache")
    
    dash_app = dash.Dash(
        __name__,
        use_pages=True,
        suppress_callback_exceptions=True,
        requests_pathname_prefix="/"  # Dash na raiz
    )
    
    dash_app.layout = html.Div([
        # Top navigation
        html.Header([
            html.Div("Pitwall Analytics", className="brand"),
            html.Nav([
                dcc.Link("Home", href="/", className="nav-link"),
                dcc.Link("Analytics", href="/analytics", className="nav-link"),
                dcc.Link("Live", href="/live", className="nav-link"),
                dcc.Link("API Docs", href="/api/docs", className="nav-link"),
            ], className="nav"),
        ], className="header"),

        # page content
        dash.page_container,

        # small footer
        html.Footer("© Pitwall Analytics", className="footer"),
    ], className="container")
    
    # ==========================================
    # 3. Montar Dash dentro do FastAPI
    # ==========================================
    # Dash roda em Flask (WSGI), FastAPI é ASGI
    # Usamos WSGIMiddleware para compatibilidade
    app.mount("/", WSGIMiddleware(dash_app.server))
    
    return app


# Criar instância da aplicação
app = create_production_app()


if __name__ == "__main__":
    config = get_config()
    
    print("=" * 60)
    print("🏁 PITWALL ANALYTICS - PRODUCTION MODE")
    print("=" * 60)
    print(f"Backend API:  http://{config.API_HOST}:{config.API_PORT}/api")
    print(f"API Docs:     http://{config.API_HOST}:{config.API_PORT}/api/docs")
    print(f"Frontend:     http://{config.API_HOST}:{config.API_PORT}/")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",  # Importa de main.py
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level="info"
    )
