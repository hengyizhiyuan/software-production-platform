# C2 normal-entry driver (prepared, not run by this subtask)

`c2_normal_entry.py` uses Python standard library only. It reads the preserved
G0 `prompt` verbatim and uses only the new C2 `credentials.json` field
`operator_token`. It does not read old N1 settings or credentials, invoke a
provider directly, synthesize facts, approve Work, retry admission/execution, or
write Integration / Acceptance / Delivery authorization.

## Prerequisites

Root deployment must produce a **sanitized** identity JSON with these fields.
This is a reference to deployment observations, not a claim of Work qualification:

```json
{
  "qualification": "C2",
  "isolated": true,
  "api_service": "watt-c2-api-20261009",
  "api_base_url": "http://watt-c2-api-20261009:8000",
  "source_revision": "<exact 40-hex deployed source commit>",
  "image_id": "sha256:<exact 64-hex deployed image ID>",
  "database_name": "<dedicated C2 database name>",
  "captured_at_utc": "<UTC deployment observation time>",
  "model_credential_scope": "HUMAN_AUTHORIZED_SHARED_TEST",
  "provider_ready": true
}
```

`ISOLATED_C2` is the other allowed provider scope. `provider_ready=true` must come
from the host deployment check. A configuration assertion cannot prove provider
success. The current Human permission allows shared test provider credentials;
the driver still reads only the newly prepared C2 private credentials file.

The URL must exactly match the identity and use explicit port, with hostname
`localhost`, `127.0.0.1`, `::1`, or the exact C2 API service. Redirects and ambient
HTTP proxies are disabled. For SSH loopback forwarding, record that loopback URL
in the sanitized identity before first execution. Do not put private settings or
ENV contents in identity or evidence.

Root will place the exact input at:
`/data/watt/c2-execution-readiness-20261009/evidence/original-g0-input.json`.
Local source:
`D:\hy\c2-execution-readiness\watt\docs\evidence\core-production-execution-readiness-c2-20261009\original-g0-input.json`.

## Invocation

Use Python inside the controlled network runner or an SSH loopback connection.
This illustrative command contains no credentials or fabricated identity:

```sh
python c2_normal_entry.py \
  --base-url http://watt-c2-api-20261009:8000 \
  --identity-path /data/watt/c2-execution-readiness-20261009/evidence/driver-runtime-identity.json \
  --credentials-file /data/watt/c2-execution-readiness-20261009/private/credentials.json \
  --input-file /data/watt/c2-execution-readiness-20261009/evidence/original-g0-input.json \
  --state-file /data/watt/c2-execution-readiness-20261009/evidence/normal-entry-state.json \
  --evidence-dir /data/watt/c2-execution-readiness-20261009/evidence/normal-entry
```

Without `--execute`, the driver validates prerequisites only (no HTTP, state,
Work or model invocation). Add `--execute` for the authorized first run.
A fresh state performs exactly one `POST /api/products` with `source_mode=managed`
and one `POST /api/experience/products/{product_id}/turns` using the exact `prompt`.
The normal service owns WIC/IRK and LONG_LIVED_STEERING admission. The driver
never manually calls admission or approve. Runtime may itself call models after
the normal Turn is submitted.

## Restart and unknown effects

State is atomically saved and fsynced **before each POST** (`IN_FLIGHT`). The OS
process lock survives file reuse and releases after process death. Receipts have
run UUID and reserved sequence numbers; raw API response bodies and free-text
errors never persist. SHA256, byte count, HTTP status and allowlisted structural
IDs/enums/times are retained. Missing fields in this filtered projection mean
unrecorded here, not absent from the authoritative Owner.

An existing state never repeats a Product POST. Confirmed Product/Turn IDs allow
GET-only polling on the same invocation. A Product confirmed before an interruption
and a Turn still `NOT_ATTEMPTED` requires the explicit
`--submit-unattempted-turn` flag; this submits its first Turn, never a retry.

An attempted POST with missing/failed/ambiguous response remains `IN_FLIGHT` or
`UNKNOWN_OUTCOME`. Neither state is retried even for HTTP errors. Use read-only
Owner records to locate the exact unique Product name in state and the exact
request text, then reconcile with IDs:

- Product only: `--adopt-product-id <UUID>` validates Product name and managed source.
  If the Turn was never attempted, a later invocation may use
  `--submit-unattempted-turn`.
- Turn: `--adopt-product-id <UUID> --adopt-interaction-id <UUID> --adopt-turn-id <UUID>`
  validates actual Product, Turn, interaction request-record content and normal
  Product Workspace ownership projection. It changes only local driver state.

All recovery flags need `--execute` to perform their read-only reconciliation.
Confirmed IDs cannot be replaced. Changed input or runtime identity fails closed.
Existing receipts without a state also prevent fresh creation. Do not delete or
reset state to hide an unknown effect. Preserve state and receipts in the ECS
persistent evidence directory and sync them into the C2 evidence branch.

## Read-only tracking and qualification boundary

Each bounded poll reads Turn, Interaction and Intent Realization. Once an actual
Work ID is observed it reads Work, Operations, Steering, Self-Refine, Guardian and
Delivery projections. No Candidate Preview POST is made. The driver stops its
observation window on explicit failure, Human attention, or a completed/terminated
Work boundary. It does not authorize a Human gate. A completed Turn is not Work
completion, and any reported boundary is `OBSERVATION_ONLY_NOT_WORK_PASS`.
`--poll-limit` (default 20) bounds GET polling, not model Self-Refine budgets.
Reinvoke with the same state for another GET-only observation window.

Source paths checked at Watt `e7c1b70ac30b89940a7596f835c6f0ccc928a9ba` before
preparing this harness: `src/spg/api/http.py` normal Product/Experience/GET routes;
`src/spg/api/dto.py` Turn, Work Reality, Work and Steering DTOs;
`application/control_room.py`, `interaction.py`, `guardian_assurance.py`,
`product_experience.py` actual projections. Deployed source/image must be supplied
from the new root receipts, not inferred from this earlier read.

Preparation check: AST parse only. No script execution, API call, model call,
test, Work creation, production operation or PASS claim was made by this subtask.
