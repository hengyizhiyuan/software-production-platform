# Deferred real Web Search qualification

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
