# Stable, production-ready base image
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Install system build tools for PostgreSQL (psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary from Astral image for fast package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy requirements.txt from root context and install using uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy all project files into container
COPY . .

EXPOSE 8080

# Production ASGI Server (Gunicorn + Uvicorn worker for WebSockets)
CMD exec gunicorn core.asgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120