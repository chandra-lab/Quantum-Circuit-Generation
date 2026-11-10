FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.ts tsconfig.json postcss.config.js tailwind.config.js ./
COPY src ./src
RUN npm run build

FROM nginx:1.27-alpine

RUN apk add --no-cache wget
# The nginx entrypoint renders templates with envsubst into conf.d at startup.
ENV MAX_UPLOAD_MB=10
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
