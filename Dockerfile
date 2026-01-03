# Базовый образ с Python 3.12
FROM python:3.12-slim

# Устанавливаем минимальные системные зависимости
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
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

# Инициализируем Playwright (установит все необходимые зависимости автоматически)
RUN playwright install --with-deps chromium

# Рабочая директория
WORKDIR /app
RUN mkdir -p /app/downloads && chmod 755 /app/downloads

# Копируем скрипт
COPY fara_script.py /app/

CMD ["python", "fara_script.py"]