# syntax=docker/dockerfile:1

# ---------- Базовый образ ----------
# slim, а не alpine: paddlepaddle/torch собраны под glibc, на musl (alpine) не заведутся
FROM python:3.11-slim AS base

# Не создавать .pyc и не буферизовать stdout — чтобы логи сразу были видны в docker logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ---------- Системные зависимости ----------
# libgl1, libglib2.0-0, libsm6, libxext6 — нужны OpenCV (тянет PaddleOCR)
# poppler-utils — нужен docling для работы с PDF
# libgomp1 — рантайм OpenMP, нужен paddlepaddle
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libgomp1 \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---------- Python-зависимости ----------
# Копируем сначала только requirements.txt, чтобы Docker кэшировал этот слой
# и не переустанавливал torch/paddle (самые тяжёлые пакеты) при каждом изменении кода
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ---------- Код приложения ----------
COPY . .

# Скрипт, который ждёт БД и накатывает миграции перед стартом
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
