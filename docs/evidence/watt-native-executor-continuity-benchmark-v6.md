# Watt-native Executor Continuity Benchmark v6 — Frozen Result

Date: 2026-09-12

Plan digest: `728300efe599788491ccea81d3f9bdcf66d212a83664d02f2e4131b691ea5656`.

V6 stopped on its third execution. T5-1-B and T3-1-B passed. T4-1-B
failed, and the remaining 33 executions were not started.

## Result

- PASS: 2/3; FAIL: 1/3.
- Known Provider spend: RMB 0.14239129.
- Response-unknown reservation: RMB 0.20880000.
- Combined conservative spend through v6: RMB 5.02900794 / RMB 100.
- Human technical interventions: 0.

The v6 Tool path convention worked: no single-mount proposal used the former
invalid `primary` cwd. T4-1-B applied its prescribed pause and replacement, then
continued as a `deepseek-v4-pro/high` successor. The successor's fourth
Provider request ended with no complete response observed. The request remains
response-unknown and was not replayed. Its RMB 0.20880000 conservative reserve
is retained.

Before that unknown boundary, the workspace contained all required files. Its
own test suite exposed one unresolved lowercase-prefix case and external
verification therefore failed 1 of 19 tests. The trial ended
`UNABLE_TO_COMPLETE` and scores 0/4/4/0/0. These facts remain FAIL regardless of
the transport outcome.

## Classification

`CONTINUITY_QUALIFIED`: **NO**.

V6 exposed a recovery defect outside the Provider profile: a transport-unknown
request has no admitted Tool effect, and the latest workspace/checkpoint remains
a valid execution frontier, but the worker converted the transport outcome
directly to terminal `UNABLE_TO_COMPLETE`. A subsequent version may park this
state and create a successor from retained evidence, while preserving the
unknown request and never replaying it.

Authoritative machine evidence remains in
`.spg/validation-evidence/native-cont-v6/results.json` and `frozen-plan.json`.
