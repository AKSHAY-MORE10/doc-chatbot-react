FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend_react/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend_react ./
RUN npm run build
# Produces /frontend_dist (see vite.config.js outDir), copied into the final image below.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY --from=frontend-build /frontend_dist ./frontend_dist
COPY README.md ./README.md
COPY .env.example ./.env.example

# Create non-root user for security
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --no-create-home appuser \
    && mkdir -p /app/chroma_data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]