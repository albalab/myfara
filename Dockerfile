# Базовый образ с Python 3.12
FROM python:3.12-slim

# Устанавливаем минимальные системные зависимости и зависимости для Playwright
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    # Зависимости для Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    libatspi2.0-0 \
    libxshmfence1 \
    libglib2.0-0 \
    # Шрифты (обязательны для корректной работы браузера)
    fonts-liberation \
    fonts-noto-color-emoji \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Клонируем FARA и устанавливаем зависимости
RUN git clone https://github.com/microsoft/fara.git /fara && \
    cd /fara && \
    git submodule update --init --recursive && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir \
        aiohttp \
        nest-asyncio \
        httpx \
        beautifulsoup4 \
        lxml

# Инициализируем Playwright (только браузер, без системных зависимостей)
RUN playwright install chromium

# Рабочая директория
WORKDIR /app
RUN mkdir -p /app/downloads && chmod 755 /app/downloads

# Копируем скрипт
COPY fara_script.py /app/

CMD ["python", "fara_script.py"]