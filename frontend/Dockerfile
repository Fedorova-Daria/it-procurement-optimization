# syntax=docker/dockerfile:1

# ---------- Этап 1: сборка React-приложения ----------
FROM node:20-alpine AS build

WORKDIR /app

# Сначала только package*.json — чтобы npm install кэшировался,
# пока не меняются зависимости, а не весь код.
# npm install (а не npm ci) — потому что package-lock.json ещё не создан;
# после первой установки он появится в /app, и тогда можно перейти на npm ci для стабильности.
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build
# После этого шага статика лежит в /app/build (Create React App) или /app/dist (Vite) —
# если у вас Vite, замените ниже COPY --from=build /app/build на /app/dist

# ---------- Этап 2: раздача через Nginx ----------
FROM nginx:1.27-alpine

# Убираем дефолтный конфиг Nginx и ставим свой
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
