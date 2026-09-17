# First Human-validated Watt End-to-End Software Production Loop

Date: 2026-09-17

```text
MILESTONE
    FIRST HUMAN-VALIDATED END-TO-END SOFTWARE PRODUCTION LOOP

FORMAL_UX_UI_REAL_PRODUCTION_PREVIEW_DELIVERY_PHASE
    CLOSED / PASS

HUMAN_PRODUCT_ACCEPTANCE
    PASS

WATT_AS_A_WHOLE
    NOT CLAIMED COMPLETE
```

This record closes the current Formal UX/UI, real production, Preview, and
Delivery integration phase. It preserves the Human Governor's acceptance and
the final target-environment regression evidence without converting either
into a broader claim that Watt is complete.

## Accepted representative journey

The Human-accepted representative requirement was:

> 创建一个最基本网页，包含按钮，点击后 alert 弹出 hello Watt

The accepted product journey is:

```text
Human natural-language intent
    -> WIC
    -> Human Work Admission
    -> Work
    -> Steering
    -> PWU
    -> Execution Queue
    -> Scheduler / Allocation
    -> Watt-native Executor
    -> Attempt
    -> real engineering artifact
    -> Verification
    -> sealed Candidate
    -> Preview
    -> Candidate Authorization
    -> Trusted Baseline advancement
    -> direct artifact Download
    -> Delivery Context
    -> Human inspection / acceptance
```

The Human Retest passed and the Human Governor reported no additional blocking
finding for this phase. The disposable retest database is not treated as the
canonical production-history store: its final read-only inspection contained
one `READY` Work and no Delivery Acceptance row. Human Product Acceptance is
therefore recorded as the explicit Human closure decision, while engineering
and lifecycle claims remain grounded in repository implementation and the
target-environment integration evidence below. No Runtime fact was fabricated
to make the acceptance look persisted.

## Truth and Authority distinctions

- Provider Attempt outcome is not implementation Reality.
- Technical Verification is not Human Product Acceptance.
- Candidate Authorization retains its existing exact Human Authority
  semantics; it is not inferred from Preview, Download, or Verification.
- Preview and Download are read-only projections over exact governed artifact
  Reality and do not own lifecycle Truth.
- Human Authority remains required wherever the admitted flow requires it.

## Preview and direct Download Reality

```text
PREVIEW_SOURCE_ARTIFACT
    sealed Candidate -> exact Git revision/blob

PREVIEW_MATERIALIZATION_PATH
    NONE

PREVIEW_RUNTIME_TYPE
    direct immutable Git-blob HTTP projection
```

Preview creates no duplicate artifact and owns no physical cleanup lifecycle.
Direct Workspace Download reads the exact current Candidate artifact, creates
no additional Delivery lifecycle or state mutation, and rejects a stale
Candidate fingerprint. A generic isolated full-stack or multi-service Preview
Sandbox remains `NOT STARTED` and was not introduced by this phase.

## Full target-environment regression

The complete Python suite ran in the Linux target image against the isolated
PostgreSQL database `spg_test`. `SPG_DATABASE_URL` was not passed to pytest and
no real Provider test ran.

```text
PYTHON FULL REGRESSION
    collected: 1192
    passed: 1182
    failed: 0
    errors: 0
    skipped: 0
    deselected: 10 real-Provider cases
    duration: 1353.31 seconds

OPEN_WIC
    5 passed

POSTGRESQL INTEGRATION
    614 integration cases in the full JUnit evidence
    0 failed / 0 errors / 0 skipped

NATIVE EXECUTOR
    102 Native Executor / continuity cases in the full JUnit evidence
    0 failed / 0 errors / 0 skipped

DELIVERY / PREVIEW / DOWNLOAD
    29 delivery-matched Python cases in the full JUnit evidence
    0 failed / 0 errors / 0 skipped

FORMAL UI PYTHON CONTRACTS
    11 passed in the full JUnit evidence

NODE / WEB
    47 passed
    0 failed / 0 skipped

ALEMBIC
    current: 20260915_41 (head)
    heads: 20260915_41 (head)

COMPILE / IMPORT
    PASS

UV LOCK CHECK
    PASS
```

Spatial-memory coverage passed in the Python Formal UI contracts and Node/Web
state tests, including stable four-surface order, collapse persistence, Focus
as temporary emphasis, refresh/reconnect reconstruction, and duplicate-response
suppression.

The Python run emitted four existing Pydantic instance-`model_fields`
deprecation warnings and one expected pytest-cache warning because the source
checkout was mounted read-only. They did not alter test outcomes. No skip or
failure was hidden.

## Closure boundary and preserved future direction

No blocker remains known for the Human-accepted E2E path. The current
implementation preserves WIC, Steering sufficiency, Human Action projection,
Work Admission, PWU, Scheduler/Allocation, Watt-native Executor, Candidate,
Verification, Preview, Download, Delivery Context, Industrial Cyan, and stable
2 x 2 spatial-memory semantics as reviewed.

The next phase is `WORK_CONTROL_ROOM_CONTENT_OPTIMIZATION`. It is
`NOT_STARTED` and requires separate Human/Architecture discussion before any
implementation. This closure does not authorize that phase.
