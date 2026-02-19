"""
Backend FastAPI application.

This is the API layer that handles:
- Data processing (FastF1)
- Business logic
- External API calls
- Caching

Dash frontend will consume these endpoints via HTTP.

FastAPI provides:
- Automatic API documentation (Swagger UI at /docs)
- Async/await support for better performance
- Built-in data validation with Pydantic
- Type hints and auto-completion
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_config
import uvicorn


def create_app() -> FastAPI:
    """
    Application factory pattern for FastAPI.
    
    Returns:
        FastAPI application instance
    """
    # Load configuration
    config = get_config()
    
    # Create FastAPI app
    app = FastAPI(
        title="Pitwall Analytics API",
        description="F1 Race Analytics Backend API",
        version="2.0.0",
        docs_url="/docs",  # Swagger UI
        redoc_url="/redoc"  # ReDoc
    )
    
    # Configure CORS for frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routers (equivalent to Flask blueprints)
    from backend.api.health import router as health_router
    from backend.api.data import router as data_router
    from backend.routes.data import router as cached_data_router
    
    app.include_router(health_router, prefix="/api", tags=["Health"])
    app.include_router(data_router, prefix="/api", tags=["Data"])
    app.include_router(cached_data_router, prefix="/api/cached", tags=["Cached Data"])
    
    # Startup event: Initialize services
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        # Initialize FastF1 cache
        from backend.services.cache_service import init_cache
        init_cache(config.CACHE_DIR, config.CACHE_ENABLED)
        print("✅ FastF1 cache initialized")
        
        # Initialize SQLite database for caching layer
        from backend.db.session import init_database
        init_database()
        print("✅ SQLite cache database initialized")
    
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    config = get_config()
    print(f"🏁 Backend API starting on http://{config.API_HOST}:{config.API_PORT}")
    print(f"📚 API Documentation: http://{config.API_HOST}:{config.API_PORT}/docs")
    
    # Run with uvicorn (ASGI server)
    uvicorn.run(
        "backend.app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,  # Auto-reload on code changes in dev mode
        log_level="info"
    )
