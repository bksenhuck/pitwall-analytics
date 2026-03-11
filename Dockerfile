# --- Stage 1: Build wheels ---
FROM python:3.11-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip
RUN pip wheel --wheel-dir=/wheels -r requirements.txt || true

# --- Stage 2: Final image ---
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    || pip install --no-cache-dir -r requirements.txt

# --- Copy app code ---
COPY backend /app/backend
COPY frontend /app/frontend
COPY assets /app/assets
COPY main.py /app/main.py
COPY startup.sh /app/startup.sh

# --- Environment ---
ENV PORT=8080 PYTHONUNBUFFERED=1

RUN useradd --create-home appuser \
    && chown -R appuser /app \
    && sed -i 's/\r//' /app/startup.sh \
    && chmod +x /app/startup.sh
USER appuser

EXPOSE 8080

CMD ["/app/startup.sh"]
