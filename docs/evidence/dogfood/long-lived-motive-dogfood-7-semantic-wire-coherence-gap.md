# Long-lived Motive Dogfood #7 — Semantic Wire Coherence Finding

## Preserved Runtime Reality

Dogfood #7 used the same target-free long-lived Motive after the real semantic
Provider and bounded multi-turn Executor closures:

```text
Work Admission                         PASS
Steering Activation                    PASS
Current Step                           DESIGN
Provider terminal status               COMPLETED
Provider Threads / Turns                1 / 1
Strict wire schema validation           PASS
Wire-to-domain conversion               PASS
SemanticStepResultCandidate             FAIL
SemanticStepResult                      0
Steering Decisions / History            0 / 0
Run / PWU / Attempt / Dispatch          0 / 0 / 0 / 0
Runtime Commit                          0
Driver                                  STOPPED / BLOCKED
```

The exact first divergence was the `SemanticStepResultCandidate` coherence
invariant:

```text
semantic uncertainty or authority expansion requires Human Attention
```

The Provider-facing schema guaranteed individual field types but did not make
the correlated combination of `authority_assessment`, `unresolved_questions`,
`human_attention_recommendation`, and `completion_claimed` structurally
coherent. The application correctly failed closed; no governed result or
production fact was fabricated.

The `watt-motive-dogfood-7` Runtime remains preserved without retry, repair,
fact injection, Step transition, or repository mutation.

## Bounded Correction

The Provider wire contract now exposes three finite dispositions:

```text
RESOLVED
UNRESOLVED
AUTHORITY_EXPANSION
```

Each branch carries an internally coherent authority, unresolved-question,
Human Attention, and completion shape. This is a wire-only structural
correction. The domain `SemanticStepResultCandidate`, application admission,
DESIGN non-mutation, Authority, PLAN-1B, SPG, independent Verification,
Candidate Authorization, and Runtime Commit boundaries are unchanged.

## Autonomous Self-refine Evidence

Fresh disposable PostgreSQL and synthetic repository state was used for every
repair validation. Three authorized real read-only Provider attempts materially
advanced the boundary:

1. The first corrected-schema attempt exposed that the resolved empty array
   schema had `minItems/maxItems` but no `items`; Provider schema admission
   rejected it.
2. The resolved branch was changed to a string array with `maxItems: 0`. The
   next real attempt passed Provider schema admission and persisted a governed
   `DESIGN_DIRECTION` result with `WITHIN_AUTHORITY`, no unresolved questions,
   and exact target `src/spg/web/app.js`.
3. The final proof repeated real semantic generation and continued through the
   application boundary: the governed result satisfied DESIGN, the Step
   transitioned lawfully to PRODUCE, and the exact CODE_WORK contract passed
   Authority validation, PLAN-1B `ONE_PWU_FIT`, and SPG admission.

Final fresh evidence:

```text
Real semantic Provider                 PASS
Wire validation                        PASS
Wire-to-domain conversion              PASS
SemanticStepResultCandidate            PASS
Application admission                  PASS
Governed SemanticStepResult            PERSISTED
DESIGN completion                      PASS
Current Step after transition          PRODUCE
Production Authority                   WITHIN_AUTHORITY
PLAN-1B                                ONE_PWU_FIT
Run / PWU                              1 / 1
Attempt / Dispatch / Provider Report   0 / 0 / 0
Executor execution                     NOT STARTED
Runtime Commit                         0
Repository diff                        0
```

The task's minimum PASS condition is satisfied. Production execution,
independent Completion/Verification, Candidate Authorization, integration, and
Runtime Commit were not required because this proof stopped immediately after
lawful PRODUCE admission.

## Preserved Findings

```text
SEMANTIC_PROVIDER_WIRE_COHERENCE_GAP
    RESOLVED BY FOCUSED AND FRESH REAL PROVIDER EVIDENCE

SEMANTIC_EXECUTION_OBSERVABILITY_GAP
    CONFIRMED / PARTIALLY MITIGATED / OPEN
```

This correction does not declare MVP Core Closure.
