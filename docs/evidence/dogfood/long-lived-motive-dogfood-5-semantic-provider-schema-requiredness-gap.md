# Long-lived Motive Dogfood #5 — Provider Schema Requiredness Finding

## Preserved Runtime Reality

Dogfood #5 reached strict Provider response-format admission from the same
long-lived Motive:

```text
Work Admission                         PASS
Steering Activation                    PASS
Semantic Step Input                    PASS
Structured output_schema supplied      PASS
Provider response-format admission     FAIL
Content generation                     NOT REACHED
Provider Threads / Turns                1 / 1
SemanticStepResult                      0
Production facts                        0
Current Step                            DESIGN
Driver                                  STOPPED / BLOCKED
```

The Provider rejected the schema with `invalid_json_schema` because every
object property must appear in `required`; the first reported omission was
`artifact_targets`. Recursive inspection found the same omission class in the
top-level nullable/default fields and the other production-proposal collection
fields.

The preserved `watt-motive-dogfood-5` Runtime remains immutable evidence. It is
not retried, repaired, or rewritten by MVP-PLAN-STEER-1K.

## Classification

```text
SEMANTIC_PROVIDER_SCHEMA_REQUIREDNESS_GAP
    CONFIRMED

SEMANTIC_STRUCTURED_OUTPUT_GAP
    STILL OPEN IN REAL DOGFOOD
```

## Admitted Correction

MVP-PLAN-STEER-1K introduces a typed Provider-only wire proposal over the
unchanged semantic production domain contract. Every wire object requires all
properties. Empty collections remain explicit empty arrays; nullable values
remain explicit nulls. The wire proposal converts deterministically into the
existing domain proposal, whose target-kind, artifact shape, repository area,
authority, and production-boundary checks remain unchanged.

No schema-conforming response becomes Authority without the existing
application admission path. `DESIGN` remains non-mutating and no Run/PWU exists
before a governed `PRODUCE` admission.

## Current Status

```text
MVP-PLAN-STEER-1K
    CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

Reality-driven Plan Steering
    IMPLEMENTED FOR MVP BEHAVIOR
    REAL PROVIDER DOGFOOD CONTINUES
```

Core Closure is not claimed by this evidence.
