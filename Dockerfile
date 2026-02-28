# Stage 1: frontend-builder
FROM node:22-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json* ./

RUN npm ci || npm install

COPY frontend/ .

RUN npm run build

# Stage 2: python-builder
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY amaototyann amaototyann

RUN uv sync --frozen --no-dev

# Stage 3: runtime
FROM python:3.12-slim

RUN useradd --create-home amaoto

WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY --from=builder /app/amaototyann amaototyann
COPY --from=builder /app/pyproject.toml .
COPY --from=frontend-builder /frontend/dist frontend/dist

ENV PATH="/app/.venv/bin:$PATH"

RUN mkdir -p amaototyann/logs && chown -R amaoto:amaoto /app

USER amaoto

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD [".venv/bin/uvicorn", "amaototyann.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
