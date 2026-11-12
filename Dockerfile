FROM node:24-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM node:24-alpine AS demo-frontend
WORKDIR /demo-frontend
COPY demo-frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY demo-frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN useradd --create-home --uid 10001 app && mkdir /data && chown app:app /data
COPY backend/ backend/
COPY demo/ demo/
COPY --from=frontend /frontend/dist frontend/dist/
COPY --from=demo-frontend /demo-frontend/dist demo/static/
USER app
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
