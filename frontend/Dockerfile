# Multi-stage Dockerfile for REACT-X Frontend
FROM node:20-slim AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --quiet
COPY . .
RUN npm run build

# Production Nginx web server
FROM nginx:alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config for SPA routing and API proxying
RUN rm /etc/nginx/conf.d/default.conf
COPY ../deploy/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf 2>/dev/null || :

# Fallback default.conf if built independently
RUN if [ ! -f /etc/nginx/conf.d/default.conf ]; then \
    cat > /etc/nginx/conf.d/default.conf << 'EOF' \
server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location /api { \
        proxy_pass http://api:8000; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
    } \
    location /health { \
        proxy_pass http://api:8000; \
    } \
    location /readiness { \
        proxy_pass http://api:8000; \
    } \
    location /metrics { \
        proxy_pass http://api:8000; \
    } \
    add_header X-Frame-Options "SAMEORIGIN"; \
    add_header X-Content-Type-Options "nosniff"; \
    add_header Referrer-Policy "strict-origin-when-cross-origin"; \
} \
EOF \
; fi

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s \
    CMD wget -qO- http://localhost:80/ || exit 1
