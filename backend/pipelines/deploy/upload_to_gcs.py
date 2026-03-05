"""
Upload dos bancos SQLite por temporada para o Google Cloud Storage.

Faz WAL checkpoint antes do upload para garantir consistencia dos dados.

Uso:
    python -m backend.pipelines.deploy.upload_to_gcs              # sobe todas as temporadas
    python -m backend.pipelines.deploy.upload_to_gcs --season 2025 # sobe so 2025
    python -m backend.pipelines.deploy.upload_to_gcs --deploy      # sobe tudo + redeploy

Estrutura esperada em data/:
    pitwall_2025.db
    pitwall_2024.db
    ...

Requerimentos:
    - GOOGLE_APPLICATION_CREDENTIALS configurado, ou gcloud auth ativo
    - pip install google-cloud-storage

Variaveis lidas do .env:
    GCS_BUCKET_NAME         ex: pitwall-analytics-bucket
    GCS_DB_BLOB_PATH        ex: db/pitwall_cache.db  (define a pasta-base no bucket)
    DB_DIR                  ex: data
    GCP_REGION              ex: us-central1
    CLOUDRUN_SERVICE        ex: pitwall-analytics
    GCP_PROJECT             ex: pitwall-analytics
    AR_REPOSITORY           ex: pitwall-repo
"""
import sys
import sqlite3
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import os

basedir = Path(__file__).parent.parent.parent.parent
load_dotenv(basedir / ".env")

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
GCS_DB_BLOB_PATH = os.getenv("GCS_DB_BLOB_PATH", "pitwall_cache.db")
DB_DIR = os.getenv("DB_DIR", "data")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")
CLOUDRUN_SERVICE = os.getenv("CLOUDRUN_SERVICE", "pitwall-analytics")
GCP_PROJECT = os.getenv("GCP_PROJECT", "")
AR_REPOSITORY = os.getenv("AR_REPOSITORY", "pitwall-repo")
IMAGE_NAME = os.getenv("IMAGE_NAME", "pitwall-analytics")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _local_db_path(season: int) -> Path:
    return basedir / DB_DIR / f"pitwall_{season}.db"


def _blob_path(season: int) -> str:
    """Blob name no bucket para a temporada.

    Se GCS_DB_BLOB_PATH nao tiver subpasta (ex: 'pitwall_cache.db'),
    salva na raiz: 'pitwall_2025.db'.
    Se tiver subpasta (ex: 'subdir/pitwall_cache.db'), usa 'subdir/pitwall_2025.db'.
    """
    parent = Path(GCS_DB_BLOB_PATH).parent
    if str(parent) == ".":
        return f"pitwall_{season}.db"
    return f"{parent}/pitwall_{season}.db"


def _discover_seasons() -> list[int]:
    """Descobre todas as temporadas disponiveis na pasta data/."""
    data_dir = basedir / DB_DIR
    dbs = sorted(data_dir.glob("pitwall_*.db"))
    seasons = []
    for db in dbs:
        try:
            year = int(db.stem.replace("pitwall_", ""))
            seasons.append(year)
        except ValueError:
            pass
    return seasons


def _get_client():
    try:
        from google.cloud import storage
    except ImportError:
        print("google-cloud-storage nao instalado. Execute: pip install google-cloud-storage")
        sys.exit(1)

    credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if credentials_file:
        return storage.Client.from_service_account_json(credentials_file)
    return storage.Client()


def checkpoint_wal(db_path: Path) -> None:
    """Faz WAL checkpoint antes do upload para garantir consistencia."""
    print(f"[WAL] Checkpoint em {db_path.name}...")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        print("[WAL] Checkpoint concluido")
    except Exception as e:
        conn.close()
        raise RuntimeError(f"WAL checkpoint falhou: {e}") from e


def upload_file(local_path: Path, blob_name: str) -> None:
    if not GCS_BUCKET_NAME:
        print("GCS_BUCKET_NAME nao definido no .env")
        sys.exit(1)

    size_mb = local_path.stat().st_size / (1024 * 1024)
    print(f"[GCS] Enviando {local_path.name} ({size_mb:.1f} MB) -> gs://{GCS_BUCKET_NAME}/{blob_name}")
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))
    print(f"[GCS] Concluido: {local_path.name}")


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_season(season: int) -> bool:
    local_path = _local_db_path(season)
    if not local_path.exists():
        print(f"[{season}] Banco nao encontrado: {local_path}")
        return False
    checkpoint_wal(local_path)
    upload_file(local_path, _blob_path(season))
    return True


def upload_all() -> bool:
    seasons = _discover_seasons()
    if not seasons:
        print(f"Nenhum banco pitwall_*.db encontrado em {basedir / DB_DIR}")
        return False
    print(f"Temporadas encontradas: {seasons}")
    results = [upload_season(s) for s in seasons]
    return all(results)


# ---------------------------------------------------------------------------
# Deploy Cloud Run
# ---------------------------------------------------------------------------

def trigger_deploy() -> bool:
    """Redeploy Cloud Run usando a imagem atual (pega dados frescos do GCS)."""
    if not GCP_PROJECT:
        print("GCP_PROJECT nao definido no .env")
        return False

    image = f"{GCP_REGION}-docker.pkg.dev/{GCP_PROJECT}/{AR_REPOSITORY}/{IMAGE_NAME}:latest"
    env_vars = (
        f"GCS_BUCKET_NAME={GCS_BUCKET_NAME},"
        f"GCS_DB_BLOB_PATH={GCS_DB_BLOB_PATH}"
    )
    cmd = [
        "gcloud", "run", "deploy", CLOUDRUN_SERVICE,
        "--image", image,
        "--region", GCP_REGION,
        "--platform", "managed",
        "--set-env-vars", env_vars,
    ]
    print(f"[DEPLOY] Executando: {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print("[DEPLOY] Cloud Run atualizado com sucesso")
        return True
    else:
        print(f"[DEPLOY] gcloud run deploy falhou (exit {result.returncode})")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Upload dos bancos SQLite por temporada para GCS")
    parser.add_argument("--season", type=int, default=None, help="Temporada especifica (ex: 2025). Padrao: todas")
    parser.add_argument("--deploy", action="store_true", help="Acionar redeploy no Cloud Run apos upload")
    args = parser.parse_args()

    print("=" * 50)
    print("GCS UPLOAD - Pitwall Analytics")
    print("=" * 50)

    if args.season:
        ok = upload_season(args.season)
    else:
        ok = upload_all()

    if not ok:
        print("Upload falhou")
        sys.exit(1)

    print("Upload concluido com sucesso")

    if args.deploy:
        deploy_ok = trigger_deploy()
        if not deploy_ok:
            sys.exit(1)
    else:
        print(
            "\nDica: rode com --deploy para acionar o redeploy no Cloud Run, "
            "ou manualmente:\n"
            f"  gcloud run deploy {CLOUDRUN_SERVICE} "
            f"--region {GCP_REGION} --platform managed"
        )


if __name__ == "__main__":
    main()
