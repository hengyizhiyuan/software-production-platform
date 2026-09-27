# Separate Web Search live qualification

Current constraint: `SPG_WEB_SEARCH_API_KEY` is withheld. Every qualification
that requires actual Web retrieval is `BLOCKED_EXTERNAL`; deterministic provider
fixtures and available GitHub retrieval may still be tested. A partial pass
cannot be reported as full GC-EX-12 or Web Search live success.

When the credential becomes available through the existing private environment,
run each entry with a **new** immutable trial number:

```sh
.venv/bin/python benchmarks/golden/runtime/qualify_research.py \
  --scope web-live --trial NEW_TRIAL --base http://127.0.0.1:8078 \
  --env-file PRIVATE_RUNTIME_ENV --evidence-root NEW_EVIDENCE_ROOT
.venv/bin/python benchmarks/golden/runtime/qualify_research.py \
  --scope GC-EX-12 --trial NEW_TRIAL --base http://127.0.0.1:8078 \
  --env-file PRIVATE_RUNTIME_ENV --evidence-root NEW_EVIDENCE_ROOT
```

Retain runtime image/source identity, Human input, immutable IR and provenance,
expected/observed obligation projection, actual provider requests/failure
categories, retrieved source URLs/provider/type/query/rank/time, inspected
content fingerprints, citations, project exact commit/tree/material packet,
complete final browser stream, no-unrequested-Work proof and qualification checks.
Keep credentials out of every receipt. A Search narrative or memory answer is
not retrieval evidence. Full GC-EX-12 additionally requires real GitHub sources
and project-grounded recommendations. Human acceptance remains separate.
