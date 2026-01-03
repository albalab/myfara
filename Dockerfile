# Базовый образ с Playwright и Python 3.12
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

# Устанавливаем минимальные зависимости
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    # Исправляем для Ubuntu 24.04
    libasound2t64 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Клонируем FARA и устанавливаем зависимости
RUN git clone https://github.com/microsoft/fara.git /fara && \
    cd /fara && \
    git submodule update --init --recursive && \
    pip install --no-cache-dir -e .

# Устанавливаем Python-пакеты
RUN pip install --no-cache-dir \
    aiohttp \
    nest-asyncio \
    httpx \
    beautifulsoup4 \
    lxml

# Проверяем и инициализируем Playwright
RUN python -c "import playwright; print(f'Playwright {playwright.__version__}')" && \
    playwright install chromium

# Рабочая директория
WORKDIR /app
RUN mkdir -p /app/downloads && chmod 755 /app/downloads

# Копируем скрипт
COPY fara_script.py /app/

CMD ["python", "fara_script.py"]