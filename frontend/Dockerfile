
# syntax=docker/dockerfile:1

# Этап 1. Сборка React
FROM node:20-alpine AS build

WORKDIR /app

# Копируем только файлы зависимостей
COPY package*.json ./

# Используем package-lock.json, если он существует
RUN --mount=type=cache,target=/root/.npm \
    sh -c 'if [ -f package-lock.json ]; then npm ci; else npm install; fi'

# Копируем исходники
COPY . .

# Собираем приложение
RUN npm run build

# Поддерживаем как Create React App (build),
# так и Vite (dist)
RUN mkdir -p /static && \
    if [ -d /app/build ]; then \
        cp -a /app/build/. /static/; \
    elif [ -d /app/dist ]; then \
        cp -a /app/dist/. /static/; \
    else \
        echo "ERROR: React build directory not found"; \
        exit 1; \
    fi

# Этап 2. Nginx
FROM nginx:1.27-alpine

RUN rm -f /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /static/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
