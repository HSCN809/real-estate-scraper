# Backend Dockerfile - FastAPI only (scraping runs in the worker)
# syntax=docker/dockerfile:1.4
FROM python:3.11-slim-bookworm

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY Backend/ .

RUN mkdir -p /app/database /app/logs /app/outputs \
    && chmod -R 755 /app

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_PORT=8000
ENV DATABASE_PATH=/app/database/real_estate.db
ENV GO_PROXY_URL=http://invisible-proxy:8080
ENV USE_GO_PROXY=false

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
