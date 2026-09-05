# Long-lived Motive Dogfood #6 — Provider `$ref` Schema Finding

## Preserved Runtime Reality

Dogfood #6 retested the same long-lived Motive after MVP-PLAN-STEER-1K:

```text
Work Admission                         PASS
Steering Activation                    PASS
Semantic Step Input                    PASS
Recursive required-key validation      PASS
Provider response-format admission     FAIL
Content generation                     NOT REACHED
Provider Threads / Turns                1 / 1
SemanticStepResult                      0
Production facts                        0
Current Step                            DESIGN
Driver                                  STOPPED / BLOCKED
```

The real Provider no longer reported a missing `required` property. It rejected
the `target_kind` schema because that node combined `$ref` with a `description`
sibling. The preserved `watt-motive-dogfood-6` Runtime is not retried, repaired,
or rewritten by MVP-PLAN-STEER-1L.

## Classification

```text
SEMANTIC_PROVIDER_SCHEMA_REQUIREDNESS_GAP
    RESOLVED BY REAL PROVIDER EVIDENCE

SEMANTIC_PROVIDER_SCHEMA_REF_SIBLING_GAP
    CONFIRMED

SEMANTIC_STRUCTURED_OUTPUT_GAP
    STILL OPEN IN REAL DOGFOOD
```

## Admitted Correction

MVP-PLAN-STEER-1L retains the typed Pydantic wire model and recursively adapts
its generated Provider-facing schema so every node containing `$ref` contains
only `$ref`. The transformation operates on a deep copy and does not alter the
domain schema, enum vocabulary, target shapes, path constraints, null/empty
semantics, parsing, deterministic wire-to-domain conversion, or application
admission and Authority checks.

No schema-conforming response becomes Authority without the existing fail-closed
application path. `DESIGN` remains non-mutating, and no production Runtime may
exist before governed `PRODUCE` admission.

## Current Status

```text
MVP-PLAN-STEER-1L
    CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

Reality-driven Plan Steering
    IMPLEMENTED FOR MVP BEHAVIOR
    REAL PROVIDER DOGFOOD CONTINUES
```

The later bounded self-refine closure supplied the required fresh real Provider
evidence without modifying this preserved Runtime. Core Closure is not claimed
by this evidence.
