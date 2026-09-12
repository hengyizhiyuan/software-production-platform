# Watt-native Executor Continuity Benchmark v7 — Frozen Result

Date: 2026-09-12

Plan digest: `3a5bc92249a10f7ee646ab832ff4012d4b9fc29f4258e6fb9ea60db8d9ecb9ac`.

V7 passed T5-1-B and T3-1-B, then stopped on T4-1-B. The other 33
executions were not started.

## Result

- PASS: 2/3; FAIL: 1/3.
- Known Provider spend: RMB 0.20785984.
- Response-unknown reservation: RMB 0.
- Combined conservative spend through v7: RMB 5.23686778 / RMB 100.
- Human technical interventions: 0.

T4-1-B reached `RESULT_READY`, passed 33 pytest cases and compile verification,
changed only the three exact required paths, and used both the primary and
preassigned `deepseek-v4-pro/high` replacement profiles. It had six known
Provider responses and no unknown response.

The frozen v7 quality evaluator nevertheless counted zero submitted tests and
assigned tests score 2, producing one material defect. Inspection shows twelve
`test_*` method definitions inside three pytest test classes. The evaluator
walked only the AST module body, so it omitted class methods. V7 remains FAIL;
the evidence and score are not rewritten.

## Classification

`CONTINUITY_QUALIFIED`: **NO**.

Authoritative machine evidence remains in
`.spg/validation-evidence/native-cont-v7/results.json` and `frozen-plan.json`.
