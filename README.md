# SPG Runtime

This repository contains the controlled implementation of the Software Production Governor Runtime.

The current implementation includes the FVS-1 project and persistent Runtime foundations. Runtime domain lifecycle, Executor integration, repository integration, and Runtime Commit are not implemented.

## Local setup

The supported local workflow uses uv:

    uv sync --extra test

Run the CLI:

    uv run spg --help
    uv run spg status

Start the development/test PostgreSQL service and configure the explicit database URLs:

    docker compose up -d postgres
    export SPG_DATABASE_URL=postgresql+psycopg://spg:spg-local-dev@localhost:54329/spg_test
    export SPG_TEST_DATABASE_URL="$SPG_DATABASE_URL"

Check non-destructive PostgreSQL connectivity and Alembic configuration:

    uv run spg db check
    uv run alembic current

Run tests:

    uv run pytest

Stop PostgreSQL when it is no longer needed:

    docker compose down

The Compose credentials are local development values only. No Runtime domain tables or substantive Alembic revision exist yet; the first Runtime schema migration is deferred to its authorized slice.
