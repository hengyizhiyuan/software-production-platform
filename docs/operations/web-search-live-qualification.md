# Real Web Search qualification

## Current Aliyun qualification (2026-10-02)

Watt selects `aliyun-opensearch` for the local dogfood run. The public HTTPS
OpenSearch endpoint and actual `watt` workspace returned real results with the
server-side key. The independent `web-live` trial passed with persisted Search
evidence, inspected Web sources, cited inspected sources, and complete
Interaction events. Direct Chinese and technical queries, combined GitHub +
Web research, and model-initiated Web research returned real provider evidence.
GC-EX-12 trials 3 and 4 are **PASS**; trial 4 ran after the final semantic-role
consumer correction and all 11 oracle checks passed, including the exact
project repository observation, inspected GitHub and Aliyun Web sources, cited
fetched Web content, and complete Human SSE. Trial 1 lacked an inspected Web
citation; trial 2 cited inspected GitHub and Web sources but lacked the project
repository observation. The bounded correction adds a typed
`PROJECT_REPOSITORY` reference role to Human-confirmed Engineering Semantic
Truth. Research routing now consumes that role without interpreting the fact
subject's language or the URL's shape. Historical `BLOCKED_EXTERNAL` and failed
trial receipts remain unchanged.
The preserved L1–L6 receipts and final GC-EX-12 trial 4 establish L1–L7 PASS
for this Search task; Human Acceptance remains a separate governance step.

Private local receipts are under `.spg/search-aliyun-live/receipts/`; they omit
the API key. The running app must receive the selected provider, Aliyun
endpoint, workspace, service ID, and key through server-side configuration.
Search snippets and fetched page content retain the same source identity and
distinct completeness states.

## Historical Brave credential deferral (2026-09-27)

The 2026-09-27 batch continues without `SPG_WEB_SEARCH_API_KEY` by Human
instruction. Every qualification that requires actual Web Search is
`BLOCKED_EXTERNAL`: explicit Web Search (SEARCH-Q2), the Web part of combined
research (SEARCH-Q3), model-initiated Web retrieval, live Web provenance and
refinement/convergence, and GC-EX-12. GitHub retrieval, direct page Fetch,
deterministic Search regression and project/SSE qualification remain independent.
Neither direct Fetch nor a deterministic adapter can qualify real Web Search.
Historical receipts keep their original status; current projections normalize
older `BLOCKED_EXTERNAL_CREDENTIAL` names to `BLOCKED_EXTERNAL`.

## Independent entry points

Use `benchmarks/golden/runtime/qualify_research.py`. The private runtime env file
must contain the operator token and, when available, the Web Search key. The
running application must use that same key. Configure/restart the application
before live qualification; changing only the runner env cannot enable its
Connector. Never commit or print either credential.

```sh
.venv/bin/python benchmarks/golden/runtime/qualify_research.py \
  --scope web-live --trial 2 --base http://127.0.0.1:8078 \
  --env-file .spg/stability-runtime/golden-v15.env \
  --evidence-root .spg/stability-runtime/deferred-web-qualification

.venv/bin/python benchmarks/golden/runtime/qualify_research.py \
  --scope GC-EX-12 --trial 7 --base http://127.0.0.1:8078 \
  --env-file .spg/stability-runtime/golden-v15.env \
  --evidence-root .spg/stability-runtime/golden-runs
```

Without a configured key, the runner writes a dated `BLOCKED_EXTERNAL` receipt
without submitting a Turn and exits successfully so the batch continues.
Every rerun needs a new trial identity; existing directories are immutable.
`--allow-partial` may exercise available GitHub/project/SSE surfaces without a
Web key. Its complete case stays blocked, and a failure in those available
surfaces stays FAIL rather than being hidden behind the missing credential.

GC-EX-12 uses the unchanged corpus request and business-app fixture. The fixture
server must be reachable as `qualified-git:8080` from the actual app/worker
networks. This is qualification setup, not tester repository acquisition or an
implementation hint. A new runtime needs this network connection explicitly.

## Evidence required before clearing the external gate

Retain the raw submission and Interaction/Turn identity, exact runtime activation
revision/tree/package identities, source observations, response SSE, final
qualification checks, latency/token/cost metrics and Human assistance record.

A live Web PASS requires actual Brave Search results with provider, query,
rank, timestamp, URL and stable Evidence ID; inspected page content; final
source citations; sufficient bounded synthesis; completed `response.final` and
`message.completed` events; and no unauthorized production. Search snippets alone
do not prove source inspection. Rate-limit/network/invalid-key failures remain
actual failed or blocked observations, never empty successful results.

GC-EX-12 additionally requires real inspected GitHub sources; exact project
revision/tree and inspected path hashes; the owner-validated project recommendation
and observed project paths; no production Work; and complete Human SSE without
internal project source packets. Both GitHub and Web sources must satisfy their
live obligations. Current trial 6 proves the available GitHub/project/SSE path;
it cannot supply the absent Web evidence.

After live qualification, exercise the model-initiated Web and bounded
refinement/convergence variants with retained independent Turn receipts, then
regenerate the Golden projection:

```sh
.venv/bin/python benchmarks/golden/runtime/summarize.py \
  --evidence-root .spg/stability-runtime/golden-runs \
  --output docs/evidence/stability/golden-runtime-results-20260927.json
```

Recheck every mandatory oracle and repeat requirement before upgrading Tier-0.
Update the deferred-qualification manifest and closure with the new receipt
paths/hashes. Human Acceptance remains a separate governance activity.

## Lifecycle hardening runtime entry

The subsequent lifecycle/action batch has its own isolated app at `8079` and
private env `.spg/lifecycle-hardening/runtime.env`. Its trial 1 receipts are
`BLOCKED_EXTERNAL`; they neither replace the historical `8078` receipts nor
claim live Web success. After privately configuring the key in the actual app
and activating the exact source package, run fresh identities:

```sh
.venv/bin/python benchmarks/golden/runtime/qualify_research.py \
  --scope web-live --trial 2 --base http://127.0.0.1:8079 \
  --env-file .spg/lifecycle-hardening/runtime.env \
  --evidence-root .spg/lifecycle-hardening/deferred-web-qualification

.venv/bin/python benchmarks/golden/runtime/qualify_research.py \
  --scope GC-EX-12 --trial 2 --base http://127.0.0.1:8079 \
  --env-file .spg/lifecycle-hardening/runtime.env \
  --evidence-root .spg/lifecycle-hardening/deferred-web-qualification
```

Apply every evidence requirement above, including separate model-initiated
retrieval and bounded recovery/convergence receipts. The running app must have
the key; editing only the runner env does not satisfy the gate. Do not modify
the retained user `8078` runtime or frozen FSI attempts as qualification setup.

## Natural-language action generalization follow-up (2026-09-27)

The Human subsequently authorized retirement of unused services. Port `8078`
has been stopped; the retained test runtime is `http://127.0.0.1:8079`.
Earlier entries are historical qualification instructions, not a request to
restart retired services. Frozen FSI attempts and volumes remain preserved.

This batch records both Web live and GC-EX-12 as **BLOCKED_EXTERNAL** under
`.spg/action-generalization/deferred-web`, with retrieval not attempted.
After the credential is supplied and configured in the running test app,
use independent fresh trials:

```bash
.venv/bin/python benchmarks/golden/runtime/qualify_research.py \
  --scope web-live --trial 2 --base http://127.0.0.1:8079 \
  --env-file .spg/lifecycle-hardening/runtime.env \
  --evidence-root .spg/action-generalization/deferred-web

.venv/bin/python benchmarks/golden/runtime/qualify_research.py \
  --scope GC-EX-12 --trial 2 --base http://127.0.0.1:8079 \
  --env-file .spg/lifecycle-hardening/runtime.env \
  --evidence-root .spg/action-generalization/deferred-web
```

Preserve the raw Human input, canonical search intent and speech act, current
authority/connector admission, live provider requests and provenance, raw SSE
and persisted final response, bounded refinement history and convergence,
and GC-EX-12 runtime/package evidence required above. Semantic-only recognition,
deterministic providers and direct Fetch do not satisfy these live gates.
