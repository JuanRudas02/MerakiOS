# syntax=docker/dockerfile:1.7
# ── Etapa 1: build de Vite ──
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ── Etapa 2: servir estáticos con nginx (SPA fallback) ──
FROM nginx:1.31-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK CMD wget -qO- http://localhost/ >/dev/null || exit 1
