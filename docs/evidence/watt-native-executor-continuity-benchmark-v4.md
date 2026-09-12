# Watt-native Executor Continuity Benchmark v4 — Frozen Result

Date: 2026-09-12

Plan digest: `04affa90cf744deef9db257156014910ea712bad9aea28d3634e7de45f784124`.

V4 preserves the frozen 18-pair/36-execution plan, but stopped after the second
execution made the zero-failure B gate impossible. The remaining 34 executions
were not started. No failed execution was discarded or reclassified.

## Result

| Execution | Outcome | Independent checks | Quality | Requests known/unknown | Known cost | Result |
|---|---|---|---|---:|---:|---|
| T5-1-B | RESULT_READY | client 11 tests, server 7 tests, both compile checks PASS | 4/4/4/4/4 | 8/0 | RMB 0.07915598 | PASS |
| T3-1-B | UNABLE_TO_COMPLETE | 3 tests and compile check PASS | 2/4/4/4/2 | 5/0 | RMB 0.02847946 | FAIL |

- V4 Provider spend: RMB 0.10763544 known, RMB 0 unknown.
- Combined conservative spend through v4: RMB 3.99016268 / RMB 100.
- T5-1-B consumed its prescribed two-repository partial-convergence injection.
- T3-1-B consumed its prescribed compaction-failure injection and recovered into
  one successor execution from the portable checkpoint.
- Neither execution recorded Human technical intervention.
- Neither execution had a response-unknown Provider request.

T3-1-B produced correct repository output, but two consecutive completed and
metered Provider responses failed the native terminal-decision schema. The
kernel retained both stable `NATIVE_DECISION_SCHEMA_REJECTED` facts and stopped
at the authorized one-correction bound. Because its terminal outcome was
`UNABLE_TO_COMPLETE`, the execution remains FAIL despite passing repository
checks.

## Classification

`CONTINUITY_QUALIFIED`: **NO**.

The v4 failure exposed an Adapter contract defect: terminal text required the
Provider to reproduce Watt-owned working-plan state and the complete native
response shape. The subsequent implementation correction narrows Provider text
to terminal fields, retains Watt's current working plan, and records only safe
validation locations/types when local validation rejects observed output. That
correction belongs to a new versioned run and does not alter v4.

Authoritative machine evidence remains in
`.spg/validation-evidence/native-cont-v4/results.json` and `frozen-plan.json`.
