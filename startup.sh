#!/bin/bash
# Download DBs from GCS synchronously before starting gunicorn.
# Cloud Run will keep retrying the health check until gunicorn responds.
set -e

if [ -n "$GCS_BUCKET_NAME" ]; then
    echo "[startup] Downloading data from GCS..."
    python -c "from main import _download_dbs_from_gcs; _download_dbs_from_gcs()"
    echo "[startup] GCS download complete."
else
    echo "[startup] GCS_BUCKET_NAME not set — using local data."
fi

exec gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -w 1 \
    -b "0.0.0.0:${PORT:-8080}" \
    --timeout 120 \
    main:app
