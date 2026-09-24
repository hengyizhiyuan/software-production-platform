# SPG Runtime

This repository contains the controlled implementation of the Software Production Governor Runtime.

The current implementation runs governed Work through Watt's API-key-native Executor, Tool Host, Production Environment, independent observation, verification, Candidate governance, authorized integration, and durable recovery. The 8+1 autonomous production behavior is implemented through those existing owners; Human authority remains required for sensitive access, Delivery Authorization, and final acceptance. Earlier FVS/R4 milestones remain historical evidence, not alternate execution paths.

The repository includes the Goal / Work application flow, its HTTP API, a same-origin Control Room, and a local Docker product runtime. The [historical MVP scope calibration](docs/roadmap/mvp-scope-calibration.md) remains available for provenance; current qualification uses the native runtime and the executable evaluation gate below.

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

The default WIC and Conversation path uses the DeepSeek Responses API with
`deepseek-flash` at low reasoning effort. Configure `SPG_DEEPSEEK_API_KEY` in the
ignored local environment. Human-facing realization remains independently
configurable through `SPG_CONVERSATION_PROVIDER_ADAPTER=deepseek` and
`SPG_CONVERSATION_PROVIDER_MODEL`. There is no coding-agent SDK fallback.

Human collaboration retains WIC interpretation (including Design Intent Framing)
and Conversation expression as separate responsibilities. Pre-Work conversations
use one model call when model and reasoning settings match; active Work or
different settings or custom provider/context implementations use separate calls. Set `SPG_WIC_COALESCE_PRE_WORK=false` to
retain separate calls explicitly. Set
`SPG_WIC_PROVIDER_REASONING_EFFORT` and
`SPG_CONVERSATION_PROVIDER_REASONING_EFFORT` independently to a supported value
(`none`, `minimal`, `low`, `medium`, `high`, `xhigh`).
Set both efforts alike to preserve eligible single-call transport; a configured
effort on one side and an unset effort on the other selects separate calls.
`pipeline_selection(basis)` reports the effective route without calling a model;
completed provider observations include `pipeline_reason`, models, efforts and
actual call count. Unset effort remains an unknown provider default, not a
measured reasoning budget.
`SPG_COLLABORATION_PROVIDER_TIMEOUT_SECONDS` bounds each model stream (default
120 seconds); it is independent of the Executor timeout. The durable
acknowledgement is prepared before provider work.
See the [pipeline assessment](docs/architecture/human-collaboration-pipeline-review.md)
for ownership, context, and latency-measurement details.

The [v3.1 quality and latency report](docs/evidence/human-collaboration-pipeline-v31.md)
records Chinese before/after samples, useful recommendations and direct answers,
explicit validated reuse of unchanged semantic values, and separate text,
validation and persistence timings. It retains slower scenarios and intermediate
trials; Human product acceptance remains open.

The [v3.2 experience report](docs/evidence/human-collaboration-experience-v32.md)
records a smaller single-call output contract, recommendations grounded in user
constraints, fixed-input model comparisons and continuous conversation checks.
The browser now keeps streamed message nodes stable and accepts pending input
while a reply is running. Pending input is submitted after committed completion;
reload restores drafts but pauses pending delivery. This uses tab-local browser
storage, with uncertain sends never automatically retried. Model waiting remains
variable, and the default model/effort configuration is unchanged.

For governed API-key-native execution, configure the DeepSeek key in the
ignored local environment and run the native profile. The optional E2E
overlay selects contract-driven verification on top of that profile:

    docker compose -f compose.yaml -f compose.native-executor.yaml -f compose.e2e.yaml --profile provider up -d --build

The Native Executor owns model/tool execution; the tool host and Production
Environment constrain side effects. Provider failures are recorded as failures,
not routed to an alternate coding-agent runtime. Never mount host model or Git
credentials into an untrusted workspace.

The normal app launcher activates only the committed Current Trusted Baseline.
For pre-commit qualification of an image built from a dirty worktree, append
`compose.uncommitted-qualification.yaml` to the native Compose files and use a
distinct Compose project and
`SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_WORKSPACE_VOLUME` value. This
explicit profile still creates/migrates its isolated PostgreSQL database and
checks the repository foundation, but serves the image's current package
without claiming an admitted application revision. It is not a production or
Human Acceptance profile; omit the overlay for ordinary startup.

The first real MVP-E2E-1A Attempt remains blocked historical evidence:
Provider Outcome is `UNKNOWN`, Production Reality is `NONE`, and no Provider
Thread or Turn was created. MVP-E2E-1D created one real Thread and Turn whose
Provider Outcome was `SUCCESS`, while independent Production Reality remained
`NONE` because nested `bwrap` sandbox initialization failed. Both lineages are
projected `BLOCKED` when their Completion Contract requires a production
result. Provider Outcome remains a separate immutable fact; no retry, resume,
or Completion evaluation authority is inferred.

## Host-side development

The supported local workflow uses uv:

    uv sync --extra test

The local test profile uses the same API-key-native dependency set:

    uv sync --locked --extra test

Before promoting a candidate Watt version, set `SPG_TEST_DATABASE_URL` to an
isolated migrated PostgreSQL test database and run:

    uv run spg-evaluate --report evaluation-result.json

The command executes the domain-separated acceptance corpus and exits nonzero
if a critical case fails or the database-backed cases are unavailable. It
does not replace full regression, Guardian evidence, or Human Acceptance.

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
