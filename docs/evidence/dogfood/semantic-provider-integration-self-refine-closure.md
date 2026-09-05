# Semantic Provider Integration — Bounded Self-refine Closure

## Scope and Method

This is one bounded integration closure effort for MVP-PLAN-STEER-1L, not a new
architecture Slice. It starts from the accepted pure-`$ref` implementation and
uses real Provider execution as the compatibility oracle. Historical
`watt-motive-dogfood-1` through `-6` Runtimes remain immutable.

Human Dogfood is no longer the iterative Provider-compatibility oracle. Within
this bounded integration boundary, Executor self-refine includes fresh real
Provider validation, first-divergence inspection, systematic compatibility
correction when required, focused regression, and another fresh proof.

## Real Provider Proof

Two independent disposable PostgreSQL/repository states exercised the complete
path from the same high-level target-free Motive semantics. Both real executions
passed after the accepted 1L correction; no new compatibility divergence was
found. The second execution is the final fresh proof:

```text
target-free LONG_LIVED_STEERING Work       PASS
Steering bootstrap / CURRENT DESIGN        PASS
Provider strict output_schema admission    PASS
real structured semantic generation        PASS
wire payload validation                     PASS
wire -> domain conversion                   PASS
SemanticStepResultCandidate creation        PASS
application admission                       PASS
governed SemanticStepResult persistence     PASS
persisted result reconstruction              PASS
DESIGN completion evidence                  PASS
Run / PWU / Runtime Commit                   0 / 0 / 0
repository mutation                         0
```

The final proof admitted result
`18bce0f6-91e7-4053-b899-4eb5c5acec87` for DESIGN Step
`a9529713-1904-4c99-8310-bbaa59ab8ba2`. The Provider identity was recorded as
`codex-sdk:thread:01a07213-8f4d-7732-aaa6-26de59f7bb6d:turn:01a07213-9203-77d3-88c0-8422db4a1884`.
The result kind was `DESIGN_DIRECTION`, `completion_satisfied` was true,
Authority was `WITHIN_AUTHORITY`, Human Attention was absent, and the basis
fingerprint was
`f28b2b34218e4dff2b123bf6a9ad3fd30dd1af27db4086bbe8c523de7170e89c`.

## Design Quality Sanity

The governed result materially addressed execution-progress observability. It
was grounded in the supplied disposable repository Reality, proposed only the
existing `src/spg/web/app.js` path, and bounded the direction to current stage,
current activity, available progress, recent activity, and blocker visibility.
It explicitly avoided fabricated progress, complex new infrastructure, and a
full UX/UI redesign. The proposal remained advisory and inside the approved
scope; it did not authorize or perform production.

## Isolation and Invariants

The proof repositories contained only bounded disposable context and remained
clean at completion. Each proof began from a fresh database and repository;
neither used a pre-existing Production Plan, injected DESIGN Reality, a manual
candidate, a manually transitioned Step, a fake Provider, or historical
Dogfood state.

Provider output remained advisory. Strict typed and application validation
remained fail-closed. DESIGN did not mutate the repository or create production
facts. Production still requires Authority validation, PLAN-1B, and SPG. No
Human-approved scope or constraint was expanded, and no fuzzy repair, hidden
session state, ECF, generic Agent framework, Multi-PWU/DAG, or retry subsystem
was introduced.

## Finding Status

```text
SEMANTIC_PROVIDER_SCHEMA_REQUIREDNESS_GAP
    RESOLVED BY REAL PROVIDER EVIDENCE

SEMANTIC_PROVIDER_SCHEMA_REF_SIBLING_GAP
    RESOLVED BY REAL PROVIDER EVIDENCE

SEMANTIC_STRUCTURED_OUTPUT_GAP
    RESOLVED BY FRESH END-TO-END REAL PROVIDER EVIDENCE

MVP-PLAN-STEER-1L
    CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS
```

The process evidence is also admitted: bounded Executor self-refine with real
validation closed Provider integration without iterative Human Dogfood.

This closure preserves `SPG_EXECUTION_GRANULARITY_CALIBRATION_REQUIRED` for
later architecture calibration. Its working hypothesis is to govern the
execution envelope, not every Executor move; no SPG redesign is implemented
here. `SEMANTIC_EXECUTION_OBSERVABILITY_GAP` remains **CONFIRMED / PARTIALLY
MITIGATED / OPEN**. Core Closure is not claimed by this evidence.
