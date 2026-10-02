FROM python:3.12-slim-bookworm AS backend-deps
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt gunicorn

FROM node:20-alpine AS frontend-build
WORKDIR /frontend
ENV NEXT_TELEMETRY_DISABLED=1 INTERNAL_API_URL=http://127.0.0.1:8000
COPY frontend/package.json frontend/package-lock.json* /frontend/
RUN npm install
COPY frontend /frontend
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0 INTERNAL_API_URL=http://127.0.0.1:8000
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl nodejs \
  && rm -rf /var/lib/apt/lists/*
COPY --from=backend-deps /usr/local /usr/local
COPY backend /app/backend
COPY --from=frontend-build /frontend/.next/standalone /app/frontend
COPY --from=frontend-build /frontend/.next/static /app/frontend/.next/static
COPY --from=frontend-build /frontend/public /app/frontend/public
COPY scripts/render-start.sh /app/scripts/render-start.sh
RUN chmod +x /app/scripts/render-start.sh \
  && mkdir -p /app/backend/data/uploads /app/backend/data/samples
EXPOSE 3000
CMD ["/app/scripts/render-start.sh"]
