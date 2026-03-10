"""
Aplicacao principal para PRODUCAO.

Integra o backend FastAPI e o frontend Dash em um unico servidor.

Arquitetura:
- FastAPI serve a API REST em /api/*
- Dash app montado em / (raiz) via WSGIMiddleware
- Um unico processo, uma unica porta
- No startup: baixa os bancos SQLite do GCS se GCS_BUCKET_NAME estiver definido
"""
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from backend.config import get_config


def create_production_app() -> FastAPI:
    config = get_config()

    # ------------------------------------------------------------------
    # 1. FastAPI app — docs only when ENABLE_API_DOCS=true
    # ------------------------------------------------------------------
    _enable_docs = os.getenv("ENABLE_API_DOCS", "false").lower() == "true"
    app = FastAPI(
        title="Pitwall Analytics",
        description="F1 Race Analytics - API + Frontend unificados",
        version="2.0.0",
        docs_url="/api/docs" if _enable_docs else None,
        redoc_url="/api/redoc" if _enable_docs else None,
    )

    # ------------------------------------------------------------------
    # 2. Security headers
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api"):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = (
                "strict-origin-when-cross-origin"
            )
            response.headers["Permissions-Policy"] = (
                "geolocation=(), microphone=(), camera=()"
            )
        return response

    # ------------------------------------------------------------------
    # 3. CORS — origins from CORS_ALLOW_ORIGINS env var, no credentials
    # ------------------------------------------------------------------
    _cors_raw = os.getenv("CORS_ALLOW_ORIGINS", "")
    _cors_origins = (
        [o.strip() for o in _cors_raw.split(",") if o.strip()] or ["*"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Content-Type", "X-Admin-Key"],
    )

    # ------------------------------------------------------------------
    # 4. Rate limiting (slowapi)
    # ------------------------------------------------------------------
    from backend.security import limiter, SLOWAPI_AVAILABLE
    if SLOWAPI_AVAILABLE:
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware
        app.state.limiter = limiter
        app.add_exception_handler(
            RateLimitExceeded, _rate_limit_exceeded_handler
        )
        app.add_middleware(SlowAPIMiddleware)

    from backend.api.health import router as health_router
    from backend.api.data import router as data_router

    app.include_router(health_router, prefix="/api", tags=["Health"])
    app.include_router(data_router, prefix="/api", tags=["Data"])

    # ------------------------------------------------------------------
    # 5. Startup: inicializar cache FastF1
    # O download do GCS e feito pelo startup.sh antes do gunicorn iniciar.
    # ------------------------------------------------------------------
    @app.on_event("startup")
    async def startup_event():
        from backend.services.cache_service import init_cache
        init_cache(config.CACHE_DIR, config.CACHE_ENABLED)
        print("FastF1 cache inicializado")

    # ------------------------------------------------------------------
    # 3. Dash app montado dentro do FastAPI
    # ------------------------------------------------------------------
    from frontend.app import create_app as create_dash_app
    dash_app = create_dash_app()
    dash_app.config.suppress_callback_exceptions = True

    app.mount("/", WSGIMiddleware(dash_app.server))

    return app


def _download_dbs_from_gcs():
    """
    Baixa bancos SQLite e telemetria Parquet do GCS para data/.
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME", "")
    if not bucket_name:
        print("GCS_BUCKET_NAME nao definido — usando bancos locais")
        return

    try:
        from google.cloud import storage
    except ImportError:
        print("google-cloud-storage nao instalado — pulando download do GCS")
        return

    from pathlib import Path

    root_dir = Path(__file__).parent
    db_dir = root_dir / os.getenv("DB_DIR", "data")
    telemetry_dir = db_dir / "telemetry"
    db_dir.mkdir(parents=True, exist_ok=True)
    telemetry_dir.mkdir(parents=True, exist_ok=True)

    credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    try:
        client = (
            storage.Client.from_service_account_json(credentials_file)
            if credentials_file
            else storage.Client()
        )
        bucket = client.bucket(bucket_name)

        # 1. Download de Bancos SQLite
        all_blobs = {
            b.name: b
            for b in bucket.list_blobs()
            if b.name.startswith("pitwall_") and b.name.endswith(".db")
        }

        if not all_blobs:
            print(f"[GCS] Nenhum banco pitwall_*.db no bucket {bucket_name}")
        else:
            seasons_env = os.getenv("GCS_SEASONS", "")
            if seasons_env:
                target_blobs = [
                    all_blobs[f"pitwall_{s.strip()}.db"]
                    for s in seasons_env.replace(",", ":").split(":")
                    if f"pitwall_{s.strip()}.db" in all_blobs
                ]
            else:
                latest = sorted(all_blobs.keys())[-1]
                target_blobs = [all_blobs[latest]]
                print(
                    f"[GCS] GCS_SEASONS nao definido — baixando apenas {latest}"
                )

            for blob in target_blobs:
                dest = db_dir / blob.name
                if dest.exists():
                    print(f"[GCS] {blob.name} ja existe localmente — pulando")
                    continue
                print(f"[GCS] Baixando {blob.name} -> {dest}")
                blob.download_to_filename(str(dest))

        # 2. Download de Dados Otimizados (Parquet)
        print("[GCS] Baixando arquivos de performance otimizados...")
        data_prefixes = ["telemetry/", "laps/", "weather/", "results/"]
        total_count = 0

        for prefix in data_prefixes:
            blobs = bucket.list_blobs(prefix=prefix)
            for blob in blobs:
                if not blob.name.endswith(".parquet"):
                    continue

                # Formato: {dtype}/{season}/{filename}.parquet
                parts = blob.name.split("/")
                if len(parts) >= 3:
                    dtype = parts[0]
                    season = parts[1]
                    filename = parts[2]

                    target_dir = root_dir / "data" / dtype / season
                    target_dir.mkdir(parents=True, exist_ok=True)

                    dest = target_dir / filename
                    if not dest.exists():
                        blob.download_to_filename(str(dest))
                        total_count += 1
        
        if total_count > 0:
            print(f"[GCS] {total_count} arquivos otimizados sincronizados.")

    except Exception as e:
        print(f"[GCS] Erro ao sincronizar dados: {e}")


# Instancia da aplicacao (referenciada pelo gunicorn/uvicorn)
app = create_production_app()


if __name__ == "__main__":
    config = get_config()

    print("=" * 60)
    print("PITWALL ANALYTICS - PRODUCTION MODE")
    print("=" * 60)
    print(f"API:      http://{config.API_HOST}:{config.API_PORT}/api")
    print(f"API Docs: http://{config.API_HOST}:{config.API_PORT}/api/docs")
    print(f"Frontend: http://{config.API_HOST}:{config.API_PORT}/")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level="info",
    )
