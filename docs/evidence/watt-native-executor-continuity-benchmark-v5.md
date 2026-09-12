# Watt-native Executor Continuity Benchmark v5 — Frozen Result

Date: 2026-09-12

Plan digest: `e41cb81112581bf5bf252d923c28a668d1e57c4af839676b36bf733a50cee74c`.

V5 stopped after its twelfth execution made the zero-failure gate impossible.
The other 24 executions were not started. All v5 facts remain unchanged.

## Result

- Completed: 12/36 executions; 6 A and 6 B.
- PASS: 11/12; A 5/6 and B 6/6.
- Known Provider requests: 64.
- Known Provider spend: RMB 0.62045397.
- Retained response-unknown reservation: RMB 0.06720000.
- Combined conservative spend through v5: RMB 4.67781665 / RMB 100.
- Human technical interventions: 0.

The first eleven executions all reached `RESULT_READY`, passed their independent
checks and scored 4/4/4/4/4. This includes:

- the prior v4 failure trigger T3-1-B, recovered through a compaction successor;
- T4-1-B, which paused and changed to `deepseek-v4-pro/high` in its successor;
- T1-2-B Worker loss before effect;
- T5-3-B Worker loss after effect and before checkpoint;
- T6-2-B UI disconnect plus simulated capacity unavailable before request.

T4-1-A produced every required file, passed 29 tests and compile verification,
and stayed inside exact Git scope. It nevertheless ended
`BOUNDARY_CROSSING_REQUIRED`, so it remains FAIL with quality 2/4/4/4/2. The
Provider used `cwd=primary` for a single-mount workspace after reading
SOURCE_VECTOR identity metadata. Watt Tool paths for a single mount are rooted
at `.`; the process proposals were correctly rejected, but the request context
did not state this Tool path convention explicitly enough. The Provider then
truthfully reported that the remaining compile obligation could not be executed
within the paths it believed were available.

The T6-2-B injected capacity failure occurred before a Provider request was
sent. The v5 reconciliation query nevertheless classified its unresolved
inference resource reservation as response-unknown. The conservative RMB
0.06720000 reserve remains in v5 evidence. A later version may distinguish
durably proven no-send failures, but must not subtract or rewrite this retained
v5 amount.

## Classification

`CONTINUITY_QUALIFIED`: **NO**.

Authoritative machine evidence remains in
`.spg/validation-evidence/native-cont-v5/results.json` and `frozen-plan.json`.
