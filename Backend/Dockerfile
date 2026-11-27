# Backend Dockerfile - FastAPI only (scraping runs in the worker)
# syntax=docker/dockerfile:1.4
FROM python:3.13-slim

ARG APP_UID=10001
ARG APP_GID=10001

WORKDIR /app

COPY requirements-api.lock .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements-api.lock

COPY Backend/ .

RUN groupadd --gid ${APP_GID} appuser \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --shell /bin/bash appuser \
    && mkdir -p /app/database /app/logs /app/outputs /home/appuser \
    && chown -R appuser:appuser /app /home/appuser \
    && chmod -R 755 /app

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOME=/home/appuser
ENV LOG_FALLBACK_DIR=/tmp/scraper-logs
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_PORT=8000
ENV DATABASE_PATH=/app/database/real_estate.db
ENV GO_PROXY_URL=http://invisible-proxy:8080
ENV USE_GO_PROXY=false

USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
