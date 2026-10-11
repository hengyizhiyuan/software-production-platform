# Work Trace self-analysis — first-phase release qualification, 2026-10-11

## Scope and identity

Human-triggered, read-only advisory investigation for terminal/blocked Work.
Native Kernel, existing context/contract/evidence and exact Git reads are reused.
No autonomous code changes, new Work, deployment or acceptance are granted.
C3, canonical main and N1 are outside this release.

- Branch: `codex/watt-trace-self-analysis`.
- Qualified source: `8505c7bd75ca0e53be4cfd189b34eac653f8764d`.
- Qualified Git tree: `938cc0f01533298783a9732f0727012a1145e1f1`.
- Formal API architecture baseline: `5de657f3cb65780adf50f6557b54171a6c3cfae5`.
- Original image: `sha256:580470ce749f07ba9a3e3c2f043d7568ed3419f60b8c1060c4185df00ac353bc`.
- Release image: `watt-cloud-worker:trace-self-analysis-8505c7bd`.
- Release image ID: `sha256:75980116516128bffc00d322b7c6721aa6bfd1a9cae86a47d5044450ca69cf2f`.

The image layers the seven qualified changed files onto the original formal image.
Both `/app/src/spg` and installed `site-packages/spg` contain the same 276
Git-byte-qualified source files. The read-only Git object repository at
`/opt/watt-trace-source` exposes the exact release commit/tree to investigation.
This current source is comparison evidence, not historical Worker identity.

## Regression and historical Work qualification

- Python/PostgreSQL: **138 PASS**, no failures, errors or skips; 43.554 seconds.
- Admin JavaScript: **31 PASS**.
- Source/import/image preflight: **PASS**, both package locations and exact Git
  source checked; default budgets remain 12 inferences / 48 tools / 600 seconds.
- Historical real-model investigation: **COMPLETED**, request
  `70bc8ded-3c1e-4655-a040-d0f81006c71a`, 11 inferences / 37 tools / 109 audit events.
- Report SHA-256: `f38c6ac909bb2a5c14b09ffbabfbfd36e775fb0e4d456ac3fec42a8aaba6a28f`.
- Replay of those recorded Native decisions on exact committed Git bytes:
  **PASS**, completed, identical report, no additional model calls.

Historical Work: `3ee622b5-b816-5679-afdc-e5de51cd2702`, a completed real-model
qualification/dogfood website-change Work, **not customer evidence or an unseen
holdout**. The frozen full diagnostic ZIP has SHA-256
`3df14f6430f47bd1a85d909d3a3e5c51e06fcf84d738e58eda90b0d4530c275c`.
Its capture is non-atomic and redacted. Historical Worker revision remains UNKNOWN.

The first report submission mixed an unrelated commit timestamp into a dated
Human acceptance entry. The general timestamp gate rejected it and Native bounded
refinement corrected it. No report text was manually repaired.

### Qualification boundary

Functional first phase and structured citation/timestamp checks PASS. **Arbitrary
free-language semantics remain HUMAN_REVIEW_REQUIRED**, rather than semantic PASS:

1. F1/F3 uncertainty prose describes historical content as not retained beyond the
   checked `execution_steps.raw_response` scope. Existence elsewhere is UNKNOWN.
2. A refinement timeline entry uses verified creation time while describing its
   eventual recovered status. Recovery completion time is the separate updated
   Owner timestamp; that prose is not independently qualified.
3. A deferred download-audit suggestion cites the process-allowlist finding F2,
   a different concern. Recommendation topic lineage still needs manual review.
4. Root causes and improvement proposals are hypotheses/advice, not approved fixes.

The UI explicitly says conclusions require Human review. This release does not
qualify automatic diagnosis acceptance or autonomous improvement. The observed
residual errors are retained in `independent-review.json`; they are not rewritten
as successful semantic validation.

## ECS deployment evidence

Only `watt-cloud-worker-api-1` is selected for replacement under the Human's
deployment authorization. Compose resolved configuration is checked for equality
except `services.api.image`; mounts are identical, and environment differences
are limited to exact current source root/revision. Worker, coordinator, tool-host,
PostgreSQL and N1 container IDs are checked against their original identities.

Private rollback material lives at `/data/watt/trace-analysis-releases/8505c7bd`:
original API inspect/configuration, original compose, and immutable rollback tag
`watt-cloud-worker:trace-analysis-rollback-8505c7bd`. Credentials in those private
files are not copied to Git or the public evidence package.

The first activation used a health window of about 40 seconds and automatically
rolled back. Original-image startup subsequently took about 5.5 minutes, including
existing governed recovery attempts. Original API returned healthy HTTP 200.
The retry extends the observation window to 15 minutes and preserves candidate
startup logs before any rollback. No startup/recovery behavior is disabled.

Retry activation: **API_ACTIVATED_HEALTH_PASS**. Current API container ID is
`f834f9b87b944d1ae3725c763f6df628ded4275267f57cf8626f7cb4dda91f1b`, started
`2026-10-11T08:05:14.803483731Z`; application startup completed
`2026-10-11T08:10:40.660229378Z`. Docker health and public HTTP
`http://8.130.172.58:8080/health` are healthy/200. All **96** preexisting non-API
container identities remain unchanged, including C3 environments.

Authenticated smoke checks: unauthenticated 401, invalid Origin 403, unknown Work
409/`TRACE_SOURCE_NOT_FOUND`, authorized history 200, Admin page 200, served JS
hash exactly matching the source manifest. The initial helper incorrectly expected
403 for unknown Work and used a nonexistent `production_runs.work_id` in its
read-only invariance query. The helper was corrected against existing route/error
mapping and `work_runtime_bindings`; no application code, permission gate or
database Schema was changed. Both stopped before any analysis model invocation.

Live ECS API historical Work request: `2b274704-406f-4b58-b1c5-d5c760029342`.
**COMPLETED / RESULT_READY**, HTTP 200; 12 inferences, 35 tools, 108 audit events.
Request started `2026-10-11T08:14:59.785628+00:00` and finished
`2026-10-11T08:24:50.205418+00:00` (590.420 seconds); the client script's 605.687
seconds also includes fetching details and read-only Owner invariance checks.
Default budgets were not increased. Final report SHA-256:
`4124db060f2535749cadf36c096569a2765a689c5ac1c83c093b7296d9bcb807`.
The initial submission combined different incidents in a dated timeline entry;
the general association gate rejected it, followed by bounded revision and
`CITATIONS_AND_STRUCTURE_PASS`. Source/input/output Git identities were read at
the configured exact commits. Work/PWU/Self-Refine/acceptance row digests before
and after the request match. Original Owner state was not changed.

**ECS semantic review is PARTIAL, not fully qualified.** The receipt-only
`finding-ls-allowlisted.uncertainty` says full argv was not retained, although the
linked original effect `23d4b789-ef1d-472d-8246-bac1801a55eb` at
`/lifecycle/advanced/owners/execution_effects/9` contains `argv=["ls","-la"]`.
Catalog evidence `3cea8837-2868-504d-beaf-a45aa2f96df6` was not read by the model.
The raw-response absence claim must remain selector-scoped; redacted authorization
values are not historical absence; creation time still cannot qualify later
recovery prose. These residual limits are recorded in `ecs-independent-review.json`.
The original generated report is preserved without manual text repair. This is
an available advisory first-phase capability, not closure of every semantic issue.

Post-qualification observation at `2026-10-11T08:29:20.185807+00:00`: same release
API container/image, Docker healthy, health HTTP 200, analysis lock absent, all
96 other baseline containers unchanged. The remote qualification Python process
had exited after writing all three complete JSON records; its lingering local
SSH transport was closed only after evidence retrieval and process inspection.
This transport cleanup did not stop/restart any ECS service.

Recovery remains API-only: preserve current compose changes, use the immutable
rollback image through the protected API-only override and recreate only `api`
with `--no-deps --no-build --pull never --force-recreate`. Reconcile only the API
image declaration afterward; do not overwrite future unrelated composition
changes with the historical whole-file backup. Allow the existing cold-start
recovery window and confirm health. No rollback is presently required.

## Evidence location

Local evidence: `C:\Users\yuchunbo\Downloads\Watt-Self-Analysis-Release-20261011`.
Key files: `regression.junit.xml`, `admin-js.tap.txt`, `release-manifest.json`,
`ecs-image-preflight.json`, `historical-work-analysis.json`,
`historical-work-report.json`, `final-source-replay.json`,
`independent-review.json`, `ecs-api-analysis.json`, `ecs-api-report.json`,
`ecs-api-qualification-summary.json`, `ecs-independent-review.json`, and
deployment/admission/isolation records.
Original frozen diagnostic artifacts remain under `Watt-Trace-Review-20261011`.
Build context contains source/Git objects and the release manifest, not secrets.
