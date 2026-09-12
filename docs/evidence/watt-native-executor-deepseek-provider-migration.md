# Watt-native Executor — DeepSeek Provider Migration Evidence

> Final closure note (2026-09-13): Q01–Q50 and Continuity Benchmark v8 are
> technically closed. Human Product Acceptance is deferred by Human governance.
> See the [final technical closure](watt-native-executor-technical-closure.md)
> and [qualification closure](watt-native-executor-qualification-closure-20260912.md)
> for current classification. Historical P1/P2/Q01 evidence, including the P2
> HTTP 400, remains unchanged below.

Date: 2026-09-11. Continuation basis:
`e40f69b0c001604b9149a491695116fb2200289f` on
`feature/spg-first-vertical-slice`.

## Historical classification at the Q01 checkpoint

```text
DEEPSEEK PROVIDER ADAPTER
    IMPLEMENTED / FOCUSED VALIDATION PASS

ENVIRONMENT READY / GATE P0
    PASS

GATE P1
    PASS

GATE P2
    PASS AFTER ONE HUMAN-AUTHORIZED CORRECTED FLOW

Q01 CONTINUATION
    PASS; FINAL GOVERNED RESULT ADVANCED THE ISOLATED TRUSTED BASELINE

QUALIFICATION CLOSURE
    BROAD DETERMINISTIC REGRESSION PASS; NORMATIVE LIVE BENCHMARK OPEN

HUMAN ACCEPTANCE
    ISOLATED RUNTIME PREPARED; HUMAN DECISION PENDING
```

No production DeepSeek Attempt had been issued through P2. The two
prior OpenAI Q01 Attempts and their `UNKNOWN / RECONCILING` outcomes remain
immutable historical evidence in the implementation progress report.

## Home-machine Repository Reality

- Branch: `feature/spg-first-vertical-slice`.
- HEAD before this uncommitted continuation: `e40f69b0c001604b9149a491695116fb2200289f`.
- Migration head: `20260911_34`.
- The Native Executor implementation, Compose profile, architecture package and
  prior progress evidence are present.
- No local `.env` existed at discovery time. `.env` is intentionally ignored by
  `.gitignore`; this continuation created it with mode `0600`, generated the
  dedicated Tool Host token locally, populated the admitted non-secret Provider
  settings, and left only the DeepSeek API key empty for Human entry.
- No Native Executor, Watt application or PostgreSQL container was running when
  the continuation began. No Watt ports were listening.

## Official DeepSeek Protocol Findings

The current official DeepSeek documentation was consulted on 2026-09-11:

- Responses endpoint: `POST https://api.deepseek.com/responses`.
- Authentication: bearer API key.
- The exact Human-selected model ID `deepseek-flash` is current and supported.
- Responses are stateless; Watt continues to carry the durable Session and
  prior tool Reality.
- Structured output supports `text.format.type=json_schema`.
- Function tools use provider-safe names matching `[a-zA-Z0-9_-]+`; Watt tool
  identities such as `file.read` therefore require adapter-local projection.
- Function call output supplies `call_id`, name and JSON arguments. Watt retains
  the provider call ID only as correlation evidence; the Watt Step, Effect,
  delivery and Tool Host remain authoritative.
- Completion status, effective model, request ID, input/output/cached/reasoning
  token usage are available in the response and are normalized.
- HTTP 402 means insufficient balance and is non-retryable. HTTP 429, 500 and
  503 are retryable resource/capacity failures, but the Worker parks them and
  does not perform a hidden adapter retry.
- Responses reasoning effort accepts `none`, `low`, `high`, and `max`; the
  selected initial profile is explicitly `high`.
- Live P2 evidence refined the documented compatibility surface: with thinking
  effort `high`, DeepSeek rejected `tool_choice=required` with HTTP 400. The
  production-compatible `auto` choice remains the selected behavior.

Protocol authority:

- <https://api-docs.deepseek.com/api/create-response/>
- <https://api-docs.deepseek.com/quick_start/pricing/>
- <https://api-docs.deepseek.com/quick_start/error_codes/>
- <https://api-docs.deepseek.com/quick_start/rate_limit/>
- <https://api-docs.deepseek.com/guides/responses_api/>
- <https://api-docs.deepseek.com/guides/thinking_mode/>

## Implemented Provider Boundary

- Added `DeepSeekResponsesInferenceAdapter` behind the existing inference port.
- Retained `OpenAIResponsesInferenceAdapter` as a replaceable adapter rather
  than deleting historical compatibility.
- Shared only verified Responses-wire mechanics. DeepSeek request fields,
  reasoning, tool projection, call parsing, status, usage and error behavior
  remain inside Provider infrastructure.
- Added provider-neutral inference observation fields so effective identity,
  request identity and token usage become durable Step evidence.
- Provider tool names are projected to safe names and mapped back to exact Watt
  tool identities. Unknown calls and invalid JSON arguments fail closed.
- Native admission and worker offers now select the configured Provider profile;
  Compose defaults the first production profile to `deepseek-responses` with
  exact model `deepseek-flash`.
- Added a no-inference `--check-readiness` Worker command. It validates the
  selected Provider wiring and emits only secret-free identity fields. It does
  not connect to PostgreSQL, admit Work or call the Provider.

WIC and Conversation Provider behavior were not changed. DeepSeek protocol
logic remains inside the Provider adapter. Live Q01 did expose generic runtime
defects outside that adapter: missing Tool Host Git visibility, expected missing
file handling, verifier packaging/configuration, invalid-response termination,
tool-contract clarity, residual-obligation checkpointing, and incomplete Work
constraint projection. Those boundaries were corrected without adding
DeepSeek-specific branches to the Kernel, Tool Host, Work or Verification
contracts. This is evidence that Provider replacement is structurally
decoupled, while also showing that the original generic runtime was not yet
production-complete.

## Configuration Contract

Secret-bearing local file: ignored repository-root `.env`.

```text
SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN=<dedicated Tool Host token>
SPG_NATIVE_EXECUTOR_INFERENCE_PROVIDER=deepseek
SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY=<DeepSeek API key>
SPG_NATIVE_EXECUTOR_DEEPSEEK_BASE_URL=https://api.deepseek.com
SPG_NATIVE_EXECUTOR_INFERENCE_MODEL=deepseek-flash
SPG_NATIVE_EXECUTOR_INFERENCE_REASONING_EFFORT=high
```

Provider profile/start surface:

```text
docker compose -f compose.native-executor.yaml --profile provider ...
```

The exact post-configuration readiness command is:

```text
docker compose -f compose.native-executor.yaml --profile provider run --rm --no-deps native-worker python -m spg.executor_worker --check-readiness
```

## Deterministic and P0 Evidence

- Focused Provider, Native Executor, configuration and Docker contract tests:
  **35 passed** after the P2 correction.
- Python compileall: **PASS**.
- Compose provider profile rendering: **PASS**.
- Runtime image build from current source: **PASS**;
  `software-production-platform-native-worker:latest`, local image
  `460ea3de296a`.
- One-shot Worker container readiness with placeholder non-secret configuration:
  **PASS**. It reported Provider `deepseek`, profile `deepseek-responses`, model
  `deepseek-flash`, base URL `https://api.deepseek.com`, effort `high`,
  `provider_request_sent=false`, and `production_attempt_created=false`.

After Human configuration, the same one-shot P0 check passed with the real
secret-bearing `.env` while exposing no secret value. It proved Provider
`deepseek`, profile `deepseek-responses`, exact model `deepseek-flash`, base URL
`https://api.deepseek.com`, reasoning effort `high`, no Provider request and no
production Attempt.

P1 then issued exactly one real minimal inference without database, production
Work or tools. It passed with request ID
`492acc34-32b4-4e75-8c40-bdcaf999c967`, effective model `deepseek-flash`, status
`completed`, normalized action `UNABLE_TO_COMPLETE`, and usage 1,587 input / 342
output / 78 reasoning / 1,929 total tokens.

The first P2 proposal request was sent once with `tool_choice=required` and the
selected `high` reasoning effort. DeepSeek rejected it before inference with
HTTP 400 `Thinking mode does not support this tool_choice`. No tool, second
inference, workspace mutation, database record or production object occurred.
The adapter/probe now use `tool_choice=auto`, keep the single-tool capability
and explicit qualification instruction, and pass deterministic validation.

After explicit Human authorization, one corrected P2 flow ran with exact model
`deepseek-flash`, reasoning effort `high`, `tool_choice=auto`, no parallelism
and no retry. It passed with exactly two sequential Provider submissions and
one isolated read-only `file.read` Tool Host delivery. Provider request IDs were
`409242fe-8dc8-4395-96b6-d556ae470150` and
`759e91f0-dc0c-4016-acc3-117a840ed2a7`; the Tool Host delivery ID was
`942ffc4c-e449-4038-9695-86ee948ab7f4`. The returned output digest was
`3ffa8b7fbce69a006de3519bfeb5b77a4dddfcfd19a190c17aad922e376fbba5`.
The two observations recorded 1,932 input / 202 output / 21 reasoning / 2,134
total tokens and 1,781 input / 460 output / 137 reasoning / 2,241 total tokens,
respectively.

With `auto`, DeepSeek selected Watt's structured tool-proposal response rather
than a native Responses function-call item, so the Provider call ID is absent.
Watt nevertheless correlated the exact proposed Step to the single delivery,
receipt and output through its provider-neutral contract. This difference is
preserved as observed Reality rather than rewritten as a native Provider call.
The flow created no production Work or Attempt and performed zero mutations.

The one-shot containers were removed automatically and the P2 Tool Host was
stopped. Compose created four named runtime volumes and two networks. An
attempted blanket volume cleanup was rejected by automatic approval review
because emptiness could not be independently guaranteed, so those named
resources were left intact.

## Historical next governed boundary

P0, P1, the corrected P2 flow and Q01 real native production are complete.
Explicit Human authorization continues the original Watt-native Executor
Qualification Closure Mission through the remaining qualification matrix.

## Q01 live qualification history

The first DeepSeek Q01 Work was admitted through the public Work refinement and
Human approval routes. Capacity Scheduling allocated native Attempt
`2af79b0e-2ba8-4526-b37c-527584ea3890` for PWU
`1f79247d-5152-4053-9538-b5027a5f7f3d`. DeepSeek request
`b15f0d98-8d19-4eb7-935f-c9e4bc427f26` completed on exact model
`deepseek-flash`, using 5,998 input / 383 output / 250 reasoning / 6,381 total
tokens. Its response produced three native Provider function calls with call
IDs for `git.status` and two `file.read` observations.

The production attempt then exposed two Tool Host runtime defects. The isolated
Host could not resolve the managed worktree's Git metadata because the
read-only parent repository was not mounted, and `file.read` converted an
expected absent CREATE target into an unhandled HTTP 500. The Worker exited,
its lease expired, and the coordinator fenced the Attempt as immutable
`UNKNOWN / RECONCILING`; the in-flight read Effect remains explicit UNKNOWN.
No repository mutation occurred and no checkpoint or RESULT_READY claim was
created. This Attempt will not be replayed or rewritten.

The bounded correction mounts application repository state read-only beside
the writable private workspace and makes a missing UTF-8 file a settled
`exists=false` observation. Focused deterministic validation passes, and a
live read-only Git status from the repaired Tool Host resolves successfully.
The failed Attempt is retained as crash-frontier evidence.

A later Attempt `2cf9da17-...` for Work `7319f4ab-...` reached
`RESULT_READY` and passed its Executor-side tests. Independent Verification
then exposed two runtime gaps in sequence: the native Compose application had
no explicit independent verifier adapter, and after that was configured the
application image did not contain pytest. The resulting Work was truthfully
blocked. This result was not promoted or rewritten.

Attempt `dc8e068f-...` for Work `bd801c3c-...` reached DeepSeek and completed
read-only Tool Host observations. Its next Provider response violated the
normalized `InferenceResponse` contract. The Worker previously crashed at
that boundary and lease expiry produced `UNKNOWN / RECONCILING`. The Worker now
records an inadmissible Provider decision as a settled
`UNABLE_TO_COMPLETE` outcome and releases its lease; it still does not invent a
tool action or retry the Provider request.

Attempt `a9ec235f-...` for Work `fe9b6223-...` entered a 44-Step loop because
each inference context incorrectly restored the full original obligation set.
Watt issued a governed PAUSE at a checkpoint, proved no unresolved effect,
then resumed the same Attempt after the generic context/checkpoint fix. The
Attempt reached `RESULT_READY` and all independent checks passed, producing
sealed Candidate `f810885c-...`. Exact manual inspection found that the code
returned an empty value instead of the required error and implemented the
maximum-length behavior incorrectly. Authorization was withheld; the sealed
Candidate remains immutable evidence and is not trusted.

A stricter successor Attempt `89724eae-...` for Work `6ad44534-...` completed
in seven Steps and produced sealed Candidate `74dba27e-...`, again with all
configured checks passing. Exact inspection found further contract drift:
the default length was 128 rather than 48, whitespace was not converted to a
hyphen, and lowercase/collapse behavior was incomplete. Authorization was
again withheld. This showed that passing checks cannot compensate for an
incomplete admitted Work contract.

The Work admission projection was therefore corrected generically so every
admitted constraint is included in the immutable code-production objective.
Final Work `c4e3341f-5016-4f99-b634-fe25f63e3662`, Attempt
`7c3d9a9e-95c5-4536-a79f-22869cf233e5`, ran nine sequential Steps on exact
model `deepseek-flash` with reasoning effort `high`. Provider request IDs were
`ca466cb8-b0f9-41ec-8f27-4bc4a58b988f`,
`813dc999-227b-4478-95af-a9bd2c107ba3`,
`6e7b0360-fa59-497c-85e9-1a1751dde893`,
`e9c1baa6-aef3-4590-90a3-1bf596690960`,
`2207b45d-3637-440f-8320-837c8b0ad691`,
`7ba48463-145f-4e36-9b69-3a28c88e9ddb`,
`bdbb4087-717d-4f27-8791-54d1bdb369d8`,
`6e71d590-234c-4031-8202-65219bf843a3`, and
`a5912a56-f355-4ec4-aa3f-29995b81a30c`. The trace contains a recorded
failure-repair-green loop. Its initial red observation was a missing target
test rather than a completed behavioral test failing, so that limitation is
preserved instead of overstating test-first quality.

The final Attempt emitted `RESULT_READY` with no unresolved effect. Independent
Verification passed `PATH_SCOPE`, `GIT_DIFF_CHECK`, `PYTHON_COMPILE`,
`PYTEST_TARGET:tests/test_execution_label.py`, and
`IMPORT_CHECK:spg.execution_label`. Candidate
`36c3f8b8-6abe-53b8-ab5f-04151f932773` was sealed at repository commit
`23d7438a75f00cd5f63cd4732dbffdcf9b5576d4`. Exact inspection confirmed the
required signature and default, trimming, whitespace-to-hyphen conversion,
ASCII lowercase filtering, repeated-hyphen collapse, boundary stripping,
post-normalization truncation, and required `ValueError` cases. Human authority
`human:deepseek-q01-authorized` resolved attention
`ef838c22-d38e-545e-ae1d-09be4d75af88` for this exact Candidate. The Work is
`COMPLETED`, `trusted_result=true`, and the isolated repository Trusted Baseline
advanced from `e40f69b0c001604b9149a491695116fb2200289f` to
`23d7438a75f00cd5f63cd4732dbffdcf9b5576d4`.

The original Q01 application process still reports the earlier active revision,
so that environment remains `ACTIVATION_REQUIRED`; it was not rewritten or
represented as an active deployment. Q01 is **PASS** as a governed production
chain. It does not by itself qualify continuity or Human acceptance.

## Post-Q01 deterministic closure

The continuation added generic runtime behavior without changing WIC or adding
DeepSeek types to the Kernel/domain contract:

- supervised process-group cancellation and mid-tool Pause/Stop/Cancel;
- safe same-Attempt restart before an effect, receipt-suffix rehydration after
  an effect, and `UNKNOWN` fencing for unresolved effects;
- exact Session checkpoint fork/close, bounded invariant-preserving context
  compaction, and conservative PWU-wide resource accounting;
- outbox publish/ack reclaim, SSE `RESET`, snapshot high-water and bounded
  lossless replay batches;
- descriptor-relative file access, hardlink/symlink/non-regular/`.git` denial,
  and verified content-addressed workspace archives;
- independent exact-subject Verification plus multi-repository CandidateVector,
  per-target physical convergence, durable `PARTIAL`, forward recovery and one
  atomic aggregate Runtime Commit; and
- explicit retention pins, 30-day hibernation/restore and 180-day tombstoned
  cold retirement that retains the final recovery bundle.

An actual two-repository Git/PostgreSQL scenario passed: repository A advanced,
repository B drifted, aggregate trust stayed unchanged, the projection remained
`PARTIAL`, and only a later exact forward recovery allowed the aggregate commit.
Missing evidence and a `model:` self-issued PASS were both rejected before
Candidate sealing.

The additive migrations now end at `20260912_37`. A dedicated database completed
`20260911_34 → 20260912_37 → 20260911_34 → 20260912_37` successfully. The current
tree passed all 412 non-integration cases. The full PostgreSQL integration run
collected 607 cases and exited successfully: 599 passed and eight existing
conditional cases skipped. Its only output beyond progress was known Pydantic
2.11 deprecation warnings in the existing MVP flow test.

## Isolated Human Acceptance runtime

The current-tree runtime is a distinct Compose project:

```text
project/container prefix: watt-native-human-acceptance-v32
UI:                       http://127.0.0.1:8042/app
API:                      http://127.0.0.1:8042
database:                 project-local PostgreSQL / spg_dev
migration:                20260912_37
seed Work:                e49b7a20-f6f6-4dd3-8831-e3af98c22547 (DRAFT)
base revision:             e40f69b0c001604b9149a491695116fb2200289f
runtime delta digest:      9b70ba2316f737ae344a6a0604c8d590fcce64965fcf4a12a2505294b5f6a592
```

The delta digest covers the 30 changed runtime/configuration files under
`src/`, `migrations/`, `docker/`, the Compose overlays, `Dockerfile`, and
`.env.example`; it excludes evidence, tests and the ignored secret-bearing
`.env`. Together with the base revision it identifies the uncommitted runtime
candidate being exercised.

It is reproducible with `compose.native-executor.yaml` plus
`compose.native-executor.human-acceptance.yaml`; the latter mounts the current
source read-only into every application process and uses
`docker/start_human_acceptance.py` so the acceptance object cannot silently fall
back to an older activated checkout.

Its application image is
`sha256:f0325d35f9de624a8426be227b7ea6c09d9ed69e4c0d82d7849e4863b3c45195`;
its Worker image is
`sha256:88383343e0589fbc0969f286e5f6c9707722c6ade2e25b03edb39daafbba3ef0`.
All five project containers are healthy/running. A read-only browser inspection
showed the seed Work as Draft, no native execution queued, and the expected
current trust/production controls. The seed created zero PWUs, zero Steps and
zero Effects, so this preparation consumed no additional Provider request.

Thirty warm, read-only host samples measured `/health` at p50 14.720 ms / p95
34.806 ms and `/api/works` at p50 51.693 ms / p95 69.809 ms (maxima 46.467 ms
and 81.913 ms). These are local warm API observations only; they are not a cold
container, first-token or end-to-end production benchmark.

The effective readiness probe reported exact Provider `deepseek`, profile
`deepseek-responses`, model `deepseek-flash`, reasoning effort `high`, status
`READY`, `provider_request_sent=false` and `production_attempt_created=false`.
No credential value was printed, persisted in evidence or added to source.

The pre-existing `software-production-platform-*` Q01 runtime on port 8040 was
left running and its database/volumes were not migrated, stopped or deleted.
An automatic approval review rejected a proposed direct migration of that
existing database because its blast radius was not independently established;
the new Compose project was created as the safer isolated alternative.

Human acceptance has not been performed. The seed is intentionally DRAFT so the
Human owns refinement, admission, execution controls, exact Candidate review and
the acceptance decision.

## Remaining release gates

The current Q-case ledger uses `PASS` only for the admitted live flow,
`FOCUSED_PASS` for the exact deterministic/PostgreSQL property covered by the
current suite, `PARTIAL` where the required cross-product or fault surface is
incomplete, and `OPEN` where the prescribed qualification has not run. These
labels do not aggregate into technical qualification:

| Case | Status | Current evidence / remaining boundary |
|---|---|---|
| Q01 | PASS | Governed real DeepSeek production, repair, exact Candidate, independent Verification and Runtime Commit. |
| Q02 | FOCUSED_PASS | Durable idempotency, changed-payload conflict and 100-round dual-scheduler allocation race. |
| Q03 | FOCUSED_PASS | Kernel result claims require structured artifact/evidence state; provider prose has no trust authority. |
| Q04 | FOCUSED_PASS | Missing/failed independent Verification prevents Candidate sealing. |
| Q05 | PARTIAL | Immutable revisions and fencing exist; full material-change race matrix remains. |
| Q06 | FOCUSED_PASS | Same-Session continuation, exact checkpoint fork and non-completing close. |
| Q07 | FOCUSED_PASS | Repository-optional source vector and managed workspace contracts. |
| Q08 | PARTIAL | Source inventory/provenance exists; complete dirty/binary/ignored recovery fixture remains. |
| Q09 | FOCUSED_PASS | Bounded ineffective-action and context-fit failure paths fail closed. |
| Q10 | FOCUSED_PASS | Real process-group termination, bounded output and truncation receipts. |
| Q11 | PARTIAL | Durable provider/tool/context/source/usage evidence exists; full provenance attack matrix remains. |
| Q12 | PARTIAL | Durable update/control receipts exist; both terminal-update race orders remain to be seeded. |
| Q13 | FOCUSED_PASS | Mid-tool pause reaches safe barrier before checkpoint and resume. |
| Q14 | FOCUSED_PASS | Unresolved external effect prevents false `PAUSED`. |
| Q15 | FOCUSED_PASS | Production survives subscriber absence; bounded reconnect replay and snapshot high-water. |
| Q16 | PARTIAL | Durable scheduler/control recovery exists; full coordinator outage rehearsal remains. |
| Q17 | FOCUSED_PASS | Before-effect same-Attempt restart and after-admission unresolved-effect fencing. |
| Q18 | PARTIAL | Mutation cancellation and recovery inventory paths exist; hard-crash partial-file matrix remains. |
| Q19 | FOCUSED_PASS | Receipt reconciliation prevents duplicate effect execution. |
| Q20 | FOCUSED_PASS | Receipt suffix rehydrates without replay before the next checkpoint. |
| Q21 | FOCUSED_PASS | Content-addressed publication preserves the old pointer until atomic commit and detects corruption. |
| Q22 | FOCUSED_PASS | Typed capacity handling releases allocation and requeues/parks without hidden retry or fallback. |
| Q23 | FOCUSED_PASS | Quota preserves useful edits, residual work, checks and unknown usage. |
| Q24 | FOCUSED_PASS | Compaction preserves exact invariants and fails closed when the contract cannot fit. |
| Q25 | HUMAN_BOUNDARY | Live compatible model replacement needs a second pre-admitted exact profile and Provider spend authority. |
| Q26 | FOCUSED_PASS | Stop/cancel barriers fence new effects and terminate owned descendants. |
| Q27 | FOCUSED_PASS | Stale epochs cannot mutate current lease/authority; late evidence is fenced. |
| Q28 | FOCUSED_PASS | Safe pre-effect worker restart rotates epoch while retaining Attempt identity. |
| Q29 | OPEN | Retained-volume host reboot rehearsal has not run. |
| Q30 | PARTIAL | Verified archive restore exists; complete lost-workspace recovery-promise fixture remains. |
| Q31 | FOCUSED_PASS | One exact CandidateVector spans two real Git repositories. |
| Q32 | FOCUSED_PASS | First-target success plus second-target drift remains durably `PARTIAL` without trust advance. |
| Q33 | FOCUSED_PASS | Forward recovery completes only the remaining named CAS target. |
| Q34 | FOCUSED_PASS | Aggregate PostgreSQL commit is idempotent and atomic after Git convergence. |
| Q35 | FOCUSED_PASS | Target/source drift invalidates authorization/evidence reuse. |
| Q36 | PARTIAL | Durable Human control/update disposition exists; the full five-kind steering acceptance script remains. |
| Q37 | FOCUSED_PASS | Missing evidence and model/executor self-issued PASS are rejected. |
| Q38 | PARTIAL | Traversal, symlink, hardlink, special-file, archive and `.git` access denial pass; symlink-race coverage remains. |
| Q39 | PARTIAL | Secret filtering, no Docker socket and internal-network separation pass; hostile redirect/rebinding and package-egress qualification remain. |
| Q40 | OPEN | Warm-reuse cross-Work isolation has not been qualified. |
| Q41 | FOCUSED_PASS | PWU-wide reservation/settlement retains unknown spend and rejects duplicate debit/reset. |
| Q42 | FOCUSED_PASS | Pins, verified hibernation, crash-resume, restore, retirement tombstone and final-bundle retention. |
| Q43 | OPEN | DB/disk-full and host-reboot fault injection remain. |
| Q44 | OPEN | Exact Candidate preview, authorization and delivery remain a Human-visible acceptance exercise. |
| Q45 | FOCUSED_PASS | Publish-before-ack reclaim, monotonic IDs, `RESET`, snapshot high-water and bounded lossless replay. |
| Q46 | PARTIAL | 601-event bounded replay passes; measured slow-browser coalescing/disconnect behavior remains. |
| Q47 | FOCUSED_PASS | Five latency classes expose measured spans and explicit unavailable stages without overlap summation. |
| Q48 | OPEN | Prescribed 30-repetition cold/warm fixture measurement remains. |
| Q49 | PARTIAL | Legacy/native coexistence and additive migration round trip pass; controlled cutover/rollback rehearsal remains. |
| Q50 | PARTIAL | Historical provenance is preserved and schema upgrade/downgrade passes; incompatible-checkpoint reader matrix remains. |

`TECHNICALLY_QUALIFIED` and `HUMAN_ACCEPTED` are not asserted. The normative
36-run paired continuity benchmark still requires three real model-replacement
trials across two task types and at least two pre-admitted compatible model
profiles. Only the Human-selected `deepseek-flash / high` profile is authorized
in this mission. Selecting and spending against a second profile is a new
Provider/cost authority decision. Human acceptance itself also remains owned by
the Human.
