# SPG Runtime

This repository contains the controlled implementation of the Software Production Governor Runtime.

The current implementation includes the FVS-1 project and persistence foundations plus the S1–S5 governed Runtime path: Context Package and Attempt preparation, isolated dispatch, Provider Report, independent Production Observation, Completion and Verification, Candidate governance, authorized Repository Integration, Runtime Commit, and recovery foundations. R4-B verified maintenance-lineage recovery is implemented and has focused/affected validation plus Architecture Lead review PASS; complete R4 qualification and real maintenance recovery are deferred from the MVP critical path.

The repository includes the Goal / Work application flow, its minimal HTTP API, a functional same-origin Web UI, and a local Docker product runtime. The current delivery priority is defined by [MVP Scope Calibration and Phase-2 Hardening Backlog](docs/roadmap/mvp-scope-calibration.md): validate the integrated local MVP before Linux deployment and systematic self-dogfood.

## Local Docker product

Prerequisite: Docker Desktop or Docker Engine with Compose is available.

Start PostgreSQL, migrate the interactive `spg_dev` database, and start the
application/UI with one command:

    docker compose up --build

Open:

    http://127.0.0.1:8000/app

View application logs:

    docker compose logs -f app

Stop the product:

    docker compose down

The normal `down` command does not delete the named PostgreSQL volume. Do not
add `--volumes` when local Goal/Work data must be preserved. The application
uses `spg_dev`; automated tests use the separate `spg_test`; historical
`spg_runtime` data is not connected or migrated by this composition. The
committed database password is an intentionally non-secret local-development
value and must not be reused outside this local environment.

No Codex credential is required for startup. Without an explicitly configured
Executor, Provider-required Work remains truthfully blocked or needs attention.

For the explicitly governed local Codex E2E only, set `SPG_CODEX_HOME_HOST` in
the ignored `.env` file to the absolute existing Codex state directory, then use
the optional override:

    docker compose -f compose.yaml -f compose.e2e.yaml up -d --build
    docker compose -f compose.yaml -f compose.e2e.yaml exec -T app python /app/docker/e2e_preflight.py

The override installs the locked `codex-executor` dependency extra and mounts
the existing state at the Executor infrastructure boundary. It uses separate
persistent E2E database/runtime volumes. Credentials are not copied into the
image or transported through SPG product/domain contracts. This local topology
does not claim OS/container-level credential isolation.

## Host-side development

The supported local workflow uses uv:

    uv sync --extra test

For a Dedicated Executor host using the Codex Provider, select the
Provider-specific profile explicitly in addition to the test profile:

    uv sync --locked --extra test --extra codex-executor

Run the CLI:

    uv run spg --help
    uv run spg status

Start only the local PostgreSQL service when running host-side tests or CLI
commands:

    docker compose up -d postgres

Configure Runtime and tests with distinct explicit URLs:

    export SPG_DATABASE_URL=postgresql+psycopg://spg:spg-local-dev@127.0.0.1:54329/spg_dev?sslmode=disable&connect_timeout=5
    export SPG_TEST_DATABASE_URL=postgresql+psycopg://spg:spg-local-dev@127.0.0.1:54329/spg_test?sslmode=disable&connect_timeout=5

Check non-destructive PostgreSQL connectivity and Alembic configuration:

    uv run spg db check
    uv run alembic upgrade head
    uv run alembic current

Alternatively, start the HTTP application on the host and open
`http://127.0.0.1:8000/app`:

    uv run uvicorn spg.api.http:create_http_application --factory --host 127.0.0.1 --port 8000

The Web UI is served from the same application origin as `/api/*`; it has no
frontend build step, npm dependency, external CDN, or browser-side production
authority.

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

The Compose credentials are local development values only. Logical database
separation prevents pytest fixture cleanup from targeting local product state;
it is not physical database isolation. Alembic revision `20260827_01`
owns the eight S1-C Runtime tables, `20260828_02` adds the two S2-A preparation
tables, and `20260828_03` adds the four S2-B
dispatch/report/observation/reference tables.
