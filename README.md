# Контейнеризация стека: Django + DRF + Swagger + React + Nginx + PostgreSQL + OCR/Layout

## Структура проекта

```
project/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── (ваш код Django: manage.py, config/, apps/...)
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── (ваш код React: package.json, src/...)
```

Положите свой существующий код Django в `backend/` (рядом с `manage.py`), а код React — в `frontend/` (рядом с `package.json`). Если кода ещё нет — ниже есть шаги, как создать минимальный каркас.

---

## Шаг 1. Настройка Django под контейнер

### 1.1 settings.py — подключение к PostgreSQL через переменные окружения

```python
import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ["DB_PORT"],
    }
}

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-dev-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")

STATIC_URL = "/static/"
STATIC_ROOT = "/app/staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = "/app/media"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # добавить сразу после SecurityMiddleware
    # ...остальной middleware
]
```

**Почему через переменные окружения, а не хардкод:** это позволяет использовать один и тот же образ для dev/staging/prod — меняется только `.env`, а не код.

### 1.2 INSTALLED_APPS — добавить DRF и Swagger

```python
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "drf_spectacular",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API проекта",
    "VERSION": "1.0.0",
}
```

### 1.3 urls.py (в корневом `config/urls.py`) — маршруты Swagger

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # ...ваши урлы...
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
```

**Важно:** файл `backend/Dockerfile` запускает `gunicorn config.wsgi:application` — если ваш Django-проект называется не `config`, а иначе, поправьте эту строку в `Dockerfile` (последняя строка `CMD`).

---

## Шаг 2. Что делают ключевые файлы

### `backend/Dockerfile`
Собирает образ в 2 логических блока:
1. Ставит системные библиотеки (`libgl1`, `poppler-utils` и т.д.) — они нужны не Django, а PaddleOCR/Docling, которые внутри используют OpenCV и работу с PDF.
2. Ставит Python-зависимости из `requirements.txt` **отдельным слоем до копирования кода** — это ключевая оптимизация: пока вы меняете только код приложения, Docker не будет переустанавливать torch/paddle (это самые тяжёлые пакеты, установка может занимать 5-10 минут).

### `backend/entrypoint.sh`
Перед стартом Django контейнер:
1. Ждёт, пока PostgreSQL реально начнёт принимать соединения (частая ошибка новичков — Django стартует раньше БД и падает с `OperationalError`).
2. Прогоняет `migrate`.
3. Собирает статику (`collectstatic`) — она отдаётся через `whitenoise` прямо из Django-процесса, отдельный сервер не нужен.

### `frontend/Dockerfile`
Двухэтапная (multi-stage) сборка:
- **Этап build**: полноценный Node.js-образ, ставит зависимости, собирает React (`npm run build`) в статические файлы.
- **Этап финальный**: лёгкий `nginx:alpine`, в который копируются только уже собранные файлы. Сам Node.js в финальном образе не остаётся — это уменьшает размер образа с ~1 ГБ до ~50 МБ.

### `frontend/nginx.conf`
Nginx выполняет две роли:
1. Отдаёт статику React (с `try_files ... /index.html` для корректной работы React Router).
2. Проксирует `/api/`, `/swagger/`, `/schema/`, `/admin/` на backend-контейнер — так фронтенд и бэкенд для браузера выглядят как один домен на порту 80, и не нужно настраивать CORS.

### `docker-compose.yml`
Связывает три сервиса в одну сеть:
- `db` — Postgres с healthcheck (backend не стартует, пока Postgres не готов принимать запросы — `condition: service_healthy`).
- `backend` — Django, слушает порт 8000 только внутри сети Docker (`expose`, не `ports`).
- `frontend` — Nginx, единственный, кто "смотрит наружу" на порт 80.

Такая схема (наружу торчит только Nginx) — стандартная практика: меньше открытых портов = меньше поверхность атаки.

---

## Шаг 3. Запуск

```bash
# 1. Клонируйте/скопируйте структуру, положите свой код в backend/ и frontend/

# 2. Создайте .env из примера
cp .env.example .env
# откройте .env и впишите реальный DJANGO_SECRET_KEY и пароль от БД

# 3. Соберите образы
docker compose build

# 4. Запустите всё
docker compose up -d

# 5. Проверьте логи, если что-то не так
docker compose logs -f backend
docker compose logs -f frontend
```

После запуска:
- `http://localhost/` — React-приложение
- `http://localhost/api/` — API Django
- `http://localhost/swagger/` — Swagger UI

## Шаг 4. Проверка, что всё живое

```bash
docker compose ps          # все сервисы должны быть "healthy"/"running"
docker compose exec backend python manage.py createsuperuser   # создать админа
```

---

## Частые ошибки и как их избежать

| Проблема | Причина | Решение |
|---|---|---|
| `OperationalError: could not connect to server` | Django стартовал раньше Postgres | Уже решено `entrypoint.sh` + `healthcheck`, но если вы уберёте entrypoint — ошибка вернётся |
| Образ backend собирается 15+ минут / весит 5-8 ГБ | torch + paddlepaddle — тяжёлые ML-библиотеки | Это ожидаемо для такого стека. Чтобы ускорить пересборки — не меняйте `requirements.txt` без необходимости (слой кэшируется) |
| `ImportError: libGL.so.1` при использовании PaddleOCR | В образе нет системной библиотеки OpenGL | Уже добавлено (`libgl1`) в Dockerfile — если ошибка всё равно есть, пересоберите образ (`docker compose build --no-cache backend`) |
| React делает запросы на `localhost:8000` и ловит CORS-ошибку | Фронтенд обращается напрямую к backend, а не через Nginx-прокси | В коде React используйте относительные пути `/api/...`, а не `http://localhost:8000/api/...` — тогда браузер пойдёт через Nginx на том же порту 80 |
| 502 Bad Gateway на `/api/` | backend ещё не поднялся или упал | `docker compose logs backend` — почти всегда там видна причина |
| Долгая обработка документа (OCR/LayoutLM) обрывается по таймауту | Дефолтные таймауты Nginx/Gunicorn малы для тяжёлых ML-запросов | В `nginx.conf` уже стоит `proxy_read_timeout 300s`; при необходимости увеличьте `--timeout` у gunicorn в `Dockerfile` |

---

## О размере образа и GPU

PaddlePaddle + Torch + Transformers в одном образе — это реально тяжёлый стек (образ может занимать 6-10 ГБ). Варианты оптимизации, если станет критично:

1. **Разделить на два сервиса**: `backend` (лёгкий Django API) и `ml-worker` (отдельный контейнер с paddle/torch/LayoutLM), общаются через очередь (Celery + Redis/RabbitMQ). Это стандартная практика для тяжёлых ML-задач — long-running обработку документов не стоит держать в том же процессе, что отвечает на обычные API-запросы.
2. **GPU**: если нужна обработка на видеокарте — понадобится образ на базе `nvidia/cuda`, `paddlepaddle-gpu` вместо CPU-версии, и `docker-compose.yml` с секцией `deploy.resources.reservations.devices` (NVIDIA Container Toolkit должен быть установлен на хосте).

Если хотите — могу сразу собрать вариант с Celery-воркером для асинхронной обработки документов (это будет правильнее для продакшена, чем гонять OCR/LayoutLM синхронно внутри Django-запроса).
