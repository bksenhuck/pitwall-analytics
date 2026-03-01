"""
Google Cloud Storage service.
Faz upload e download do banco SQLite para/de um bucket GCS.

Uso via CLI:
    python -m backend.services.gcs_service upload
    python -m backend.services.gcs_service download
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env a partir da raiz do projeto
basedir = Path(__file__).parent.parent.parent
load_dotenv(basedir / ".env")

# ── Configurações lidas do .env ────────────────────────────────────────────────
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
GCS_DB_BLOB_PATH = os.getenv("GCS_DB_BLOB_PATH", "db/pitwall_cache.db")
DB_DIR = os.getenv("DB_DIR", "data")
DB_NAME = os.getenv("DB_NAME", "pitwall_cache.db")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

def _local_db_path_for(season: int | None = None):
    """Return the local DB path. If season is provided use per-season DB naming."""
    if season:
        return basedir / DB_DIR / f"pitwall_{season}.db"
    return basedir / DB_DIR / DB_NAME


def _get_client():
    """Retorna cliente GCS autenticado."""
    try:
        from google.cloud import storage
    except ImportError:
        print("❌ google-cloud-storage não instalado. Execute: pip install google-cloud-storage")
        sys.exit(1)

    if GOOGLE_APPLICATION_CREDENTIALS:
        return storage.Client.from_service_account_json(GOOGLE_APPLICATION_CREDENTIALS)

    # Usa credenciais padrão (ADC) — funciona automaticamente no GCloud
    return storage.Client()


def upload_db(season: int | None = None) -> None:
    """
    Faz upload do banco SQLite local para o bucket GCS.
    Sobrescreve o arquivo existente no bucket.
    """
    if not GCS_BUCKET_NAME:
        print("❌ GCS_BUCKET_NAME não definido no .env")
        sys.exit(1)

    local_path = _local_db_path_for(season)
    if not local_path.exists():
        print(f"❌ Banco local não encontrado: {local_path}")
        sys.exit(1)

    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(GCS_DB_BLOB_PATH)

    target_blob = GCS_DB_BLOB_PATH
    # if season provided, upload to season-specific path if GCS_DB_BLOB_PATH is a folder
    if season:
        # if GCS_DB_BLOB_PATH ends with .db treat as filename, otherwise join
        if GCS_DB_BLOB_PATH.endswith('.db'):
            target_blob = Path(GCS_DB_BLOB_PATH).parent / f"pitwall_{season}.db"
        else:
            target_blob = Path(GCS_DB_BLOB_PATH) / f"pitwall_{season}.db"

    print(f"⬆️  Enviando {local_path} → gs://{GCS_BUCKET_NAME}/{target_blob}")
    blob.upload_from_filename(str(local_path))
    print(f"✅ Upload concluído ({local_path.stat().st_size / 1024 / 1024:.1f} MB)")


def download_db(season: int | None = None) -> None:
    """
    Faz download do banco SQLite do bucket GCS para o caminho local.
    Útil na inicialização do app em produção (Cloud Run, GCE etc.).
    """
    if not GCS_BUCKET_NAME:
        print("❌ GCS_BUCKET_NAME não definido no .env")
        sys.exit(1)

    local_path = _local_db_path_for(season)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    source_blob = GCS_DB_BLOB_PATH
    if season:
        if GCS_DB_BLOB_PATH.endswith('.db'):
            source_blob = Path(GCS_DB_BLOB_PATH).parent / f"pitwall_{season}.db"
        else:
            source_blob = Path(GCS_DB_BLOB_PATH) / f"pitwall_{season}.db"

    blob = bucket.blob(str(source_blob))

    if not blob.exists():
        print(f"❌ Arquivo não encontrado no bucket: gs://{GCS_BUCKET_NAME}/{source_blob}")
        sys.exit(1)

    print(f"⬇️  Baixando gs://{GCS_BUCKET_NAME}/{source_blob} → {local_path}")
    blob.download_to_filename(str(local_path))
    print(f"✅ Download concluído ({local_path.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    commands = {"upload": upload_db, "download": download_db}

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("Uso: python -m backend.services.gcs_service <upload|download> [--season YEAR]")
        sys.exit(1)

    cmd = sys.argv[1]
    season = None
    if "--season" in sys.argv:
        try:
            idx = sys.argv.index("--season")
            season = int(sys.argv[idx + 1])
        except Exception:
            print("Uso: --season YEAR (ex: --season 2025)")
            sys.exit(1)

    commands[cmd](season)
