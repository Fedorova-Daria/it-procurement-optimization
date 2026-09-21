#!/bin/sh
set -e

echo "==> Жду доступности PostgreSQL на ${DB_HOST}:${DB_PORT}..."
# Простой цикл ожидания: пытаемся открыть TCP-соединение к базе,
# пока Postgres не поднимется (это частая причина ошибок при первом запуске)
while ! python -c "
import socket, sys, os
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
try:
    s.connect((os.environ['DB_HOST'], int(os.environ['DB_PORT'])))
except Exception:
    sys.exit(1)
"; do
  sleep 1
done
echo "==> PostgreSQL доступен."

echo "==> Применяю миграции..."
python manage.py migrate --noinput

echo "==> Собираю статику..."
python manage.py collectstatic --noinput

echo "==> Запускаю приложение: $@"
exec "$@"
