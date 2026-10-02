FROM python:3.12-slim AS backend
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend

FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* /frontend/
RUN npm install
COPY frontend /frontend
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=backend /usr/local /usr/local
COPY backend /app/backend
COPY --from=frontend-build /frontend/.next/standalone /app/frontend
COPY --from=frontend-build /frontend/.next/static /app/frontend/.next/static
COPY --from=frontend-build /frontend/public /app/frontend/public
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
EXPOSE 3000 8000
CMD ["/app/start.sh"]
