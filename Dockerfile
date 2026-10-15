# Stage 1: build the React frontend
FROM node:20-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: API + built frontend in one image
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    APP_ENV=production SERVE_FRONTEND=true API_HOST=0.0.0.0 API_PORT=8000 \
    DATABASE_URL=sqlite:////data/db/fraudshield.db REPORTS_DIR=/data/reports BACKUPS_DIR=/data/backups LOGS_DIR=/data/logs
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app backend/app
COPY data data
COPY --from=frontend /build/frontend/dist frontend/dist
RUN mkdir -p /data/db /data/reports /data/backups /data/logs && useradd --create-home appuser && chown -R appuser /data /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
