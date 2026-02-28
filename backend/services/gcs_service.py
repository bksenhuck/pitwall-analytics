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

LOCAL_DB_PATH = basedir / DB_DIR / DB_NAME


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


def upload_db() -> None:
    """
    Faz upload do banco SQLite local para o bucket GCS.
    Sobrescreve o arquivo existente no bucket.
    """
    if not GCS_BUCKET_NAME:
        print("❌ GCS_BUCKET_NAME não definido no .env")
        sys.exit(1)

    if not LOCAL_DB_PATH.exists():
        print(f"❌ Banco local não encontrado: {LOCAL_DB_PATH}")
        sys.exit(1)

    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(GCS_DB_BLOB_PATH)

    print(f"⬆️  Enviando {LOCAL_DB_PATH} → gs://{GCS_BUCKET_NAME}/{GCS_DB_BLOB_PATH}")
    blob.upload_from_filename(str(LOCAL_DB_PATH))
    print(f"✅ Upload concluído ({LOCAL_DB_PATH.stat().st_size / 1024 / 1024:.1f} MB)")


def download_db() -> None:
    """
    Faz download do banco SQLite do bucket GCS para o caminho local.
    Útil na inicialização do app em produção (Cloud Run, GCE etc.).
    """
    if not GCS_BUCKET_NAME:
        print("❌ GCS_BUCKET_NAME não definido no .env")
        sys.exit(1)

    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(GCS_DB_BLOB_PATH)

    if not blob.exists():
        print(f"❌ Arquivo não encontrado no bucket: gs://{GCS_BUCKET_NAME}/{GCS_DB_BLOB_PATH}")
        sys.exit(1)

    print(f"⬇️  Baixando gs://{GCS_BUCKET_NAME}/{GCS_DB_BLOB_PATH} → {LOCAL_DB_PATH}")
    blob.download_to_filename(str(LOCAL_DB_PATH))
    print(f"✅ Download concluído ({LOCAL_DB_PATH.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    commands = {"upload": upload_db, "download": download_db}

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("Uso: python -m backend.services.gcs_service <upload|download>")
        sys.exit(1)

    commands[sys.argv[1]]()
