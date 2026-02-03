# Backend Dockerfile - FastAPI + Selenium + Chrome
FROM python:3.11-slim

# Chrome ve sistem bağımlılıkları
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libdrm2 \
    libgbm1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Chrome kurulumu
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
ENV CHROME_HEADLESS=true

# Başlatma komutu
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
