FROM node:22.14.0-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm test && npm run build
FROM nginx:1.28.3-alpine3.23-slim
# Refresh security fixes from the same Alpine release; keep nginx API/config compatible.
RUN cp /etc/nginx/nginx.conf /tmp/nginx.conf \
    && apk upgrade --no-cache \
    && apk add --no-cache nginx=1.28.3-r7 \
    && mv /tmp/nginx.conf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN nginx -t
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=6 CMD wget -q -O /dev/null http://127.0.0.1/healthz || exit 1
