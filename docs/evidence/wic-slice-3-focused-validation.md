# WIC Slice 3 Focused Validation

## Result

```text
WIC Slice 3 — Active Work Evolution, Focus Preservation, Feedback & Plan Reassessment
    IMPLEMENTED / PASS

WIC Core
    IN PROGRESS

Watt Product MVP
    NOT CLOSED
```

This is deterministic implementation evidence, not Human Dogfood or real
Provider evidence. No real Provider Thread/Turn or production Work was created.

## Proved behavior

- `SIDE_QUESTION` and `RELEVANT_EXPLORATION` produce
  `NO_GOVERNED_CHANGE`; `MATERIAL_BRANCH` and `UNRELATED_NEW_DEMAND` produce
  `NEW_WORK_RECOMMENDED`. All preserve the admitted current Work revision.
- An on-topic feedback/constraint candidate remains `PENDING_HUMAN`; stale CAS
  and stale Interaction basis fail closed and no production fact is created.
- Human approval appends immutable Work Reality revision #2 with exact
  predecessor, source records/assessment, governance, Baseline, Resource,
  versioned Scope, evidence references, rationale, and fingerprint. Exact replay
  is idempotent; a conflicting later decision is rejected.
- The new current revision is resolved by `PlanFrame`; approval schedules the
  existing Steering driver and does not call SPG directly.
- A test active cycle remains byte/fact-equivalent and bound to revision #1,
  while revision #2 is admitted separately. Run, Plan/PWU binding, PWU, Attempt,
  Dispatch, MEI, Completion Contract, Scope binding, and Baseline are not
  rewritten or incrementally prompted. `CURRENT_RESULT_MAY_BE_INSUFFICIENT`
  becomes a PlanFrame blocker, so old-cycle evidence cannot silently satisfy the
  latest Work revision.
- Interrupted assessment reconstructs from persisted records. Provider output
  cannot introduce a supporting Reality reference absent from the Human record.
- Work-revision admission and production-cycle admission serialize on the
  persisted Work row; stale exact-revision requests fail before a new Runtime
  spine is created. Duplicate Human decisions and duplicate cycle admission are
  idempotent through persisted identity and existing binding checks.
- Migration `20260907_25` downgrades to `20260907_24` and re-upgrades to head.

## Focused validation

```text
WIC PostgreSQL integration (Slices 1–3)
    19 passed
    1 skipped real-Provider proof

Provider/UI Python contracts
    7 passed

Web state Node tests
    10 passed

Compile/import
    PASS

Migration round-trip
    PASS

Real Provider Threads / Turns
    0 / 0
```

Slice 4 completion/new-Work transition and final Human WIC Dogfood remain
explicitly outside this checkpoint.
