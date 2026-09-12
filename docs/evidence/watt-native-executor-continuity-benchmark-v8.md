# Watt-native Executor Continuity Benchmark v8 — Qualified Result

Date: 2026-09-12

Plan digest: `6bcd04af0d4eef2d951767c6d1e20ae3930e259b49da0202eae7fe4c939b481a`.

## Gate result

- 18 paired trials / 36 executions completed in frozen order.
- A: 18/18 PASS; B: 18/18 PASS; total: 36/36 PASS.
- Every execution reached `RESULT_READY`, passed all independent checks, and scored 4/4/4/4/4.
- Every pair has B-minus-A quality delta 0.0, satisfying the no-more-than-0.25 equivalence gate.
- V8 known Provider spend: RMB 1.61292174.
- V8 response-unknown reserve: RMB 0.06720000.
- Combined conservative v1-v8 spend: RMB 6.91698952 / RMB 100.
- Human technical interventions: 0.

`CONTINUITY_QUALIFIED`: **YES**.

This result is accepted as final continuity evidence for the Watt-native
Executor technical closure. Human Product Acceptance is deferred by Human
governance and is neither performed nor implied by this benchmark. See the
[final technical closure](watt-native-executor-technical-closure.md).

## Paired outcomes

| Pair | A/B outcome | A/B quality | A/B known cost RMB | A/B elapsed seconds | B successors | B repeated inference/effect digests |
|---|---|---|---:|---:|---:|---:|
| T1-1 | PASS/PASS | 4.0/4.0 | 0.03064168/0.03061274 | 68.225/65.924 | 0 | 0/1 |
| T1-2 | PASS/PASS | 4.0/4.0 | 0.03786326/0.03844508 | 60.279/65.558 | 0 | 0/0 |
| T1-3 | PASS/PASS | 4.0/4.0 | 0.03171370/0.04158502 | 53.425/62.393 | 0 | 0/1 |
| T2-1 | PASS/PASS | 4.0/4.0 | 0.02663898/0.02693578 | 45.868/55.147 | 0 | 0/1 |
| T2-2 | PASS/PASS | 4.0/4.0 | 0.02583706/0.02698506 | 45.519/89.950 | 0 | 0/1 |
| T2-3 | PASS/PASS | 4.0/4.0 | 0.01980680/0.02380184 | 39.927/46.504 | 1 | 0/1 |
| T3-1 | PASS/PASS | 4.0/4.0 | 0.02558394/0.02008344 | 43.952/40.240 | 1 | 0/1 |
| T3-2 | PASS/PASS | 4.0/4.0 | 0.02505754/0.06551298 | 42.620/70.358 | 1 | 0/1 |
| T3-3 | PASS/PASS | 4.0/4.0 | 0.01972056/0.02561306 | 35.435/48.436 | 1 | 0/1 |
| T4-1 | PASS/PASS | 4.0/4.0 | 0.03972264/0.05711828 | 75.243/60.025 | 1 | 0/0 |
| T4-2 | PASS/PASS | 4.0/4.0 | 0.12019106/0.02369432 | 246.114/65.379 | 0 | 0/0 |
| T4-3 | PASS/PASS | 4.0/4.0 | 0.03897412/0.03684572 | 62.206/56.910 | 0 | 0/1 |
| T5-1 | PASS/PASS | 4.0/4.0 | 0.04878980/0.05005052 | 92.666/98.332 | 0 | 0/0 |
| T5-2 | PASS/PASS | 4.0/4.0 | 0.09678270/0.15346172 | 158.876/119.046 | 1 | 0/0 |
| T5-3 | PASS/PASS | 4.0/4.0 | 0.05350966/0.05001638 | 92.338/94.552 | 0 | 0/2 |
| T6-1 | PASS/PASS | 4.0/4.0 | 0.03949882/0.07771340 | 58.481/131.771 | 0 | 0/2 |
| T6-2 | PASS/PASS | 4.0/4.0 | 0.04729384/0.03433526 | 100.351/104.772 | 0 | 0/0 |
| T6-3 | PASS/PASS | 4.0/4.0 | 0.03871894/0.06376604 | 56.049/92.270 | 2 | 0/3 |

## Replacement-model executions

| Execution | Task type | deepseek-v4-pro known requests | Outcome | Quality |
|---|---|---:|---|---:|
| T4-1-B | new managed repository | 2 | PASS (`RESULT_READY`) | 4.0 |
| T3-2-B | constrained refactor | 4 | PASS (`RESULT_READY`) | 4.0 |
| T5-2-B | coordinated two repositories | 5 | PASS (`RESULT_READY`) | 4.0 |

## Continuity and overhead findings

- A known cost total: RMB 0.76634510; B known cost total: RMB 0.84657664.
- A elapsed total: 1377.573s; B elapsed total: 1367.566s.
- Median B-minus-A elapsed difference: 5.473s; aggregate B-minus-A difference: -10.007s.
- Successor executions: 9. Repeated inference request digests: 0.
- Repeated Tool semantic-input digests: 40 across all executions. These include repeated reads/checks; independent Git scope and tests found no duplicated unauthorized mutation.
- One T4-2-A Provider response remained unknown. Its RMB 0.06720000 reserve is retained; a new successor continued from the no-effect frontier and passed without replaying the unknown request.
- Six observed decision/tool-schema rejections were repaired by the single-correction path; none initiated an unvalidated Tool effect.
- All prescribed B injections were consumed, including pause/resume, Worker loss frontiers, quota/capacity, compaction, Human correction, stale publication, UI disconnect, two-repository partial convergence and model replacement.

Authoritative machine evidence: `.spg/validation-evidence/native-cont-v8/results.json` and `frozen-plan.json`.
