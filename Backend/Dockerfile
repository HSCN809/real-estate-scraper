# Backend Dockerfile - FastAPI + Selenium + Chrome
# syntax=docker/dockerfile:1.4
FROM python:3.11-slim-bookworm

# Chrome ve sistem bağımlılıkları (Debian Bookworm uyumlu)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    libxi6 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libdrm2 \
    libgbm1 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libpango-1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc-s1 \
    libglib2.0-0 \
    libnspr4 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxfixes3 \
    fonts-liberation \
    ca-certificates

# Chrome kurulumu (cache ile)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable

# Çalışma dizini
WORKDIR /app

# Python bağımlılıkları (cache ile)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Uygulama kodları
COPY . .

# Dizin izinleri
RUN mkdir -p /app/database /app/logs /app/outputs \
    && chmod -R 755 /app

# Port
EXPOSE 8000

# Ortam değişkenleri
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_PORT=8000
ENV DATABASE_PATH=/app/database/real_estate.db
ENV CHROME_HEADLESS=false
ENV DISPLAY=:99

# Başlatma komutu - Xvfb ile sanal ekran (lock dosyası temizlenerek)
CMD rm -f /tmp/.X99-lock && Xvfb :99 -screen 0 1920x1080x24 & sleep 1 && uvicorn main:app --host 0.0.0.0 --port 8000 --reload
