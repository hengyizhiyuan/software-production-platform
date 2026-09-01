# SPG Runtime

This repository contains the controlled implementation of the Software Production Governor Runtime.

The current implementation includes the FVS-1 project and persistence foundations, the S1-C minimum durable Runtime spine, and the closed S2 governed artifact-production path: S2-A Context Package / Attempt preparation plus S2-B governed dispatch, provider-report, independent observation, and Work Product References. S3 Completion evaluation, Verification/Qualification, Candidate governance, Repository Integration, and Runtime Candidate Commit are not implemented or started.

## Local setup

The supported local workflow uses uv:

    uv sync --extra test

For a Dedicated Executor host using the Codex Provider, select the
Provider-specific profile explicitly in addition to the test profile:

    uv sync --locked --extra test --extra codex-executor

Run the CLI:

    uv run spg --help
    uv run spg status

Start the development/test PostgreSQL service and configure the explicit database URLs:

    docker compose up -d postgres
    export SPG_DATABASE_URL=postgresql+psycopg://spg:spg-local-dev@127.0.0.1:54329/spg_test?sslmode=disable&connect_timeout=5
    export SPG_TEST_DATABASE_URL="$SPG_DATABASE_URL"

Check non-destructive PostgreSQL connectivity and Alembic configuration:

    uv run spg db check
    uv run alembic upgrade head
    uv run alembic current

The governed Runtime commands are explicit:

    uv run spg bootstrap --repository-path /path/to/clean/repository --repository-identity repo:example --repository-ref refs/heads/main --authority-identity authority:example
    uv run spg baseline show
    uv run spg run create --intent-ref intent:example --goal "Update documentation" --horizon DOCUMENTATION --pwu-objective "Produce the update" --completion-contract completion-contract.json
    uv run spg run inspect RUN_UUID

Bootstrap observes a clean repository and exact commit through read-only Git commands. It never silently admits the current working directory or dynamic `HEAD` as the Trusted Baseline.

Run tests:

    uv run pytest

Stop PostgreSQL when it is no longer needed:

    docker compose down

The Compose credentials are local development values only. Alembic revision `20260827_01` owns the eight S1-C Runtime tables, `20260828_02` adds the two S2-A preparation tables, and `20260828_03` adds the four S2-B dispatch/report/observation/reference tables.
