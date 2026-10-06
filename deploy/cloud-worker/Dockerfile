FROM ghcr.io/astral-sh/uv:0.12.5 AS uv
FROM public.ecr.aws/docker/library/docker:29-cli AS docker-cli
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm AS runtime

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
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable
COPY alembic.ini ./
COPY migrations ./migrations
COPY docker ./docker

RUN useradd --create-home --uid 10001 spg \
    && mkdir -p /var/lib/spg/native-workspaces \
        /var/lib/spg/native-executor \
        /var/lib/spg/native-tool-receipts \
    && chown -R spg:spg /var/lib/spg

ARG WATT_REVISION
ENV SPG_RUNTIME_REVISION=${WATT_REVISION}

USER spg
EXPOSE 8000

# Optional isolated Quality recipe runner; production image does not ship tests.
FROM runtime AS quality-runner
USER root
RUN uv sync --locked --no-dev --no-editable --extra test
COPY tests /qualification/tests
COPY src /qualification/src
COPY migrations /qualification/migrations
COPY alembic.ini pyproject.toml /qualification/
USER spg
WORKDIR /qualification
CMD ["python", "-m", "spg.evaluation.campaign_worker"]
