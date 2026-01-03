# Базовый образ с Python 3.12
FROM python:3.12-slim

# Устанавливаем минимальные системные зависимости и зависимости для Playwright
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    # Зависимости для Chromium - Core libraries
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libglib2.0-0 \
    # X11 и графические библиотеки
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    libgbm1 \
    # Рендеринг и шрифты
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    fonts-noto-color-emoji \
    # Аудио
    libasound2t64 \
    # Accessibility
    libatspi2.0-0 \
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