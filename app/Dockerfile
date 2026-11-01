FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
# prepare only installs git hooks (husky), which do not exist in the image.
RUN npm ci --ignore-scripts

# VITE_* are baked into the bundle at build time and are public (docs/10-deployment.md).
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ARG VITE_APP_ENV=local
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL VITE_APP_ENV=$VITE_APP_ENV

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/client /usr/share/nginx/html

EXPOSE 5173
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget -q -O /dev/null http://127.0.0.1:5173/ || exit 1
