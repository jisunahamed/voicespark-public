# ═══════════════════════════════════════════════════════════════════
#  Voice Spark AI — Frontend Dockerfile
#  Multi-stage: Node build → Nginx serve
# ═══════════════════════════════════════════════════════════════════

# ── Stage 1: Build ────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

# Copy package files first for better layer caching
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

# Accept build-time env vars for API URL configuration
ARG VITE_BACKEND_SERVER=http://localhost/
ARG VITE_SCRAPER_BACKEND_SERVER=http://localhost/
ENV VITE_BACKEND_SERVER=$VITE_BACKEND_SERVER
ENV VITE_SCRAPER_BACKEND_SERVER=$VITE_SCRAPER_BACKEND_SERVER

# Copy source and build
COPY . .
RUN npm run build

# ── Stage 2: Serve ────────────────────────────────────────────────
FROM nginx:alpine AS production

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
