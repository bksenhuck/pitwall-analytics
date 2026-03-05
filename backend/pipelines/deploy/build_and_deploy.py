"""
Build da imagem Docker com Cloud Build e deploy no Cloud Run.

Uso:
    python -m backend.pipelines.deploy.build_and_deploy
    python -m backend.pipelines.deploy.build_and_deploy --build-only
    python -m backend.pipelines.deploy.build_and_deploy --deploy-only

Todos os valores de infra sao lidos das variaveis de ambiente (ver .env).
"""
import sys
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv
import os

basedir = Path(__file__).parent.parent.parent.parent
load_dotenv(basedir / ".env")

GCP_PROJECT = os.getenv("GCP_PROJECT", "")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")
AR_REPOSITORY = os.getenv("AR_REPOSITORY", "pitwall-repo")
IMAGE_NAME = os.getenv("IMAGE_NAME", "pitwall-analytics")
CLOUDRUN_SERVICE = os.getenv("CLOUDRUN_SERVICE", "pitwall-analytics")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
GCS_DB_BLOB_PATH = os.getenv("GCS_DB_BLOB_PATH", "pitwall_cache.db")


def _get_image(tag: str = "latest") -> str:
    if not GCP_PROJECT:
        print("GCP_PROJECT nao definido no .env")
        sys.exit(1)
    return (
        f"{GCP_REGION}-docker.pkg.dev"
        f"/{GCP_PROJECT}/{AR_REPOSITORY}/{IMAGE_NAME}:{tag}"
    )


def build(tag: str = "latest") -> bool:
    image = _get_image(tag)
    cmd = ["gcloud", "builds", "submit", "--tag", image]
    print(f"[BUILD] Executando: {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"[BUILD] falhou (exit {result.returncode})")
        return False
    print(f"[BUILD] Imagem enviada: {image}")
    return True


def deploy(tag: str = "latest") -> bool:
    image = _get_image(tag)
    # GCS_SEASONS usa ":" como separador (ex: "2024:2025") para evitar
    # conflito com a virgula que o gcloud usa em --set-env-vars
    gcs_seasons = os.getenv("GCS_SEASONS", "2024:2025")
    env_vars = ",".join([
        f"GCS_BUCKET_NAME={GCS_BUCKET_NAME}",
        f"GCS_DB_BLOB_PATH={GCS_DB_BLOB_PATH}",
        f"GCS_SEASONS={gcs_seasons}",
    ])
    cmd = [
        "gcloud", "run", "deploy", CLOUDRUN_SERVICE,
        "--image", image,
        "--region", GCP_REGION,
        "--platform", "managed",
        "--allow-unauthenticated",
        "--set-env-vars", env_vars,
        "--memory=4Gi",
        "--cpu=2",
        "--timeout=300s",
    ]
    print(f"[DEPLOY] Executando: {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"[DEPLOY] falhou (exit {result.returncode})")
        return False
    print("[DEPLOY] Cloud Run atualizado com sucesso")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Build Docker e deploy no Cloud Run"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--build-only", action="store_true", help="Apenas build da imagem"
    )
    group.add_argument(
        "--deploy-only",
        action="store_true",
        help="Apenas redeploy com imagem existente",
    )
    parser.add_argument(
        "--tag", default="latest", help="Tag da imagem Docker (padrao: latest)"
    )
    args = parser.parse_args()

    if args.build_only:
        ok = build(args.tag)
    elif args.deploy_only:
        ok = deploy(args.tag)
    else:
        print("=" * 50)
        print("BUILD + DEPLOY - Pitwall Analytics")
        print("=" * 50)
        ok = build(args.tag) and deploy(args.tag)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
