# Production "gateway" image: builds the frontend static bundle, then serves it
# (and proxies /api/v1 + /titiler) with nginx. This is the ONLY container port
# published to the host in production (see docker-compose.prod.yml) — host nginx
# (installed directly on the server, outside Docker) proxies the public port to it.
#
# Build context must be the repo root, e.g.:
#   docker compose -f docker-compose.yml -f docker-compose.prod.yml build gateway

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

FROM node:20-slim AS build

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

# Same-origin in production: the gateway serves the frontend AND proxies these
# paths, so relative URLs avoid CORS entirely and avoid baking a specific
# host/port into the frontend bundle.
ENV VITE_API_URL=/api/v1
ENV VITE_TITILER_URL=/titiler
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
