# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.12.5 AS uv

FROM python:3.13-slim-bookworm AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/spg-venv \
    PATH="/opt/spg-venv/bin:$PATH"

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates git nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

COPY alembic.ini ./
COPY migrations ./migrations
COPY docker ./docker

RUN useradd --create-home --uid 10001 spg \
    && mkdir -p /var/lib/spg /home/spg/.codex \
    && chown -R spg:spg /var/lib/spg /home/spg/.codex

USER spg

EXPOSE 8000

CMD ["python", "/app/docker/start_app.py"]

FROM runtime-base AS codex-executor

USER root
RUN uv sync --locked --no-dev --no-editable --extra codex-executor
USER spg

FROM runtime-base AS runtime
