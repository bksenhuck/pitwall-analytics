#!/bin/bash
# Data is provided via GCS FUSE volume mount at /app/data (no download needed).
exec gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -w 1 \
    -b "0.0.0.0:${PORT:-8080}" \
    --timeout 120 \
    main:app
