# Watt-native Executor Continuity Benchmark — Frozen Result

Plan digest: `e57d664eb9dbe2988949c0cecf1bb37ab010ecdaf07808dc1921d93bcac91c57`.

The frozen run contains 18 A/B pairs and 36 executions. Failed trials remain in place. This report does not amend the frozen task set, verification commands, profiles, order, or rubric.

## Gate result

- A: 8/18 PASS.
- B: 8/18 PASS.
- Total: 16/36 PASS.
- Known Provider spend: RMB 2.26231347.
- Reserved uncertain spend: RMB 1.43280000.
- Conservative spend upper bound: RMB 3.69511347 / RMB 100.
- `CONTINUITY_QUALIFIED`: **NO**. All 18 B executions were required to pass; 10 failed.
- Engineering-quality equivalence is not scoreable: the frozen spec contains category maxima but no scoring anchors. No post-output scoring rule was invented.

## Execution outcomes

| Execution | Type | Arm | Terminal | Frozen checks | Result | Requests known/unknown | Cost known/reserved (RMB) | Checkpoints | Duplicate request/effect digests | Injections consumed |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| T5-1-B | T5 | B | BUDGET_EXHAUSTED | FAIL | FAIL | 46/1 | 0.45751473/0.06720000 | 43 | 0/126 | two_repo_partial_convergence |
| T3-1-B | T3 | B | BUDGET_EXHAUSTED | PASS | FAIL | 30/0 | 0.13855328/0.00000000 | 30 | 0/42 | compaction_failure |
| T4-1-B | T4 | B | UNABLE_TO_COMPLETE | PASS | FAIL | 8/1 | 0.14659498/0.20880000 | 10 | 0/10 | graceful_pause_after_first_checkpoint, model_replacement |
| T1-3-A | T1 | A | RESULT_READY | PASS | PASS | 4/0 | 0.02797617/0.00000000 | 4 | 0/0 | none |
| T5-3-B | T5 | B | UNABLE_TO_COMPLETE | FAIL | FAIL | 6/0 | 0.06385344/0.00000000 | 5 | 0/2 | worker_loss_after_effect_before_checkpoint |
| T5-1-A | T5 | A | UNABLE_TO_COMPLETE | FAIL | FAIL | 6/0 | 0.06232352/0.00000000 | 6 | 0/4 | none |
| T2-3-A | T2 | A | RESULT_READY | PASS | PASS | 6/0 | 0.04370800/0.00000000 | 6 | 0/2 | none |
| T5-3-A | T5 | A | STOPPED | FAIL | FAIL | 0/1 | 0.00000000/0.06720000 | 0 | 0/0 | none |
| T1-2-B | T1 | B | RESULT_READY | PASS | PASS | 7/0 | 0.06120921/0.00000000 | 6 | 0/2 | worker_loss_before_effect |
| T3-1-A | T3 | A | RESULT_READY | PASS | PASS | 4/0 | 0.02240820/0.00000000 | 4 | 0/1 | none |
| T6-2-B | T6 | B | RESULT_READY | PASS | PASS | 8/0 | 0.07926930/0.00000000 | 8 | 0/5 | simulated_provider_capacity_before_request, ui_disconnect |
| T4-1-A | T4 | A | RESULT_READY | PASS | PASS | 7/0 | 0.06210463/0.00000000 | 7 | 0/3 | none |
| T1-3-B | T1 | B | RESULT_READY | PASS | PASS | 8/0 | 0.06084642/0.00000000 | 8 | 0/4 | ui_disconnect |
| T3-3-A | T3 | A | RESULT_READY | PASS | PASS | 8/0 | 0.04120722/0.00000000 | 8 | 0/4 | none |
| T3-2-A | T3 | A | RESULT_READY | PASS | PASS | 4/0 | 0.01941668/0.00000000 | 4 | 0/1 | none |
| T4-3-B | T4 | B | RESULT_READY | PASS | PASS | 6/0 | 0.04414256/0.00000000 | 5 | 0/2 | worker_loss_during_test |
| T3-3-B | T3 | B | RESULT_READY | PASS | PASS | 4/0 | 0.01811524/0.00000000 | 5 | 0/1 | material_human_correction |
| T6-1-A | T6 | A | UNABLE_TO_COMPLETE | PASS | FAIL | 10/1 | 0.10369901/0.06720000 | 10 | 0/10 | none |
| T6-3-B | T6 | B | UNABLE_TO_COMPLETE | PASS | FAIL | 5/1 | 0.04686349/0.06720000 | 6 | 0/4 | compaction_failure, material_human_correction |
| T1-2-A | T1 | A | UNABLE_TO_COMPLETE | PASS | FAIL | 5/1 | 0.03958461/0.06720000 | 5 | 0/1 | none |
| T1-1-A | T1 | A | UNABLE_TO_COMPLETE | PASS | FAIL | 2/1 | 0.01619874/0.06720000 | 2 | 0/0 | none |
| T3-2-B | T3 | B | UNABLE_TO_COMPLETE | PASS | FAIL | 5/1 | 0.07492513/0.20880000 | 6 | 0/2 | model_replacement |
| T2-2-B | T2 | B | RESULT_READY | PASS | PASS | 3/0 | 0.01571163/0.00000000 | 3 | 0/0 | simulated_provider_capacity_before_request |
| T2-2-A | T2 | A | UNABLE_TO_COMPLETE | PASS | FAIL | 7/1 | 0.04052505/0.06720000 | 7 | 0/5 | none |
| T2-1-B | T2 | B | UNABLE_TO_COMPLETE | PASS | FAIL | 3/1 | 0.01387035/0.06720000 | 2 | 0/1 | worker_loss_after_effect_before_checkpoint |
| T1-1-B | T1 | B | UNABLE_TO_COMPLETE | PASS | FAIL | 6/0 | 0.04612944/0.00000000 | 6 | 0/2 | graceful_pause_after_first_checkpoint |
| T2-1-A | T2 | A | UNABLE_TO_COMPLETE | PASS | FAIL | 10/0 | 0.09564061/0.00000000 | 9 | 0/8 | none |
| T5-2-A | T5 | A | UNABLE_TO_COMPLETE | FAIL | FAIL | 1/1 | 0.00421577/0.06720000 | 1 | 0/0 | none |
| T6-2-A | T6 | A | UNABLE_TO_COMPLETE | FAIL | FAIL | 1/1 | 0.00324473/0.06720000 | 1 | 0/0 | none |
| T6-1-B | T6 | B | RESULT_READY | PASS | PASS | 7/0 | 0.05034409/0.00000000 | 7 | 0/4 | graceful_pause_during_test |
| T5-2-B | T5 | B | UNABLE_TO_COMPLETE | FAIL | FAIL | 1/1 | 0.00421913/0.20880000 | 2 | 0/0 | model_replacement |
| T4-3-A | T4 | A | RESULT_READY | PASS | PASS | 13/0 | 0.12611272/0.00000000 | 13 | 0/5 | none |
| T6-3-A | T6 | A | UNABLE_TO_COMPLETE | PASS | FAIL | 7/0 | 0.07586553/0.00000000 | 6 | 0/2 | none |
| T4-2-B | T4 | B | UNABLE_TO_COMPLETE | FAIL | FAIL | 6/0 | 0.03637312/0.00000000 | 5 | 0/3 | stale_worker_late_publication |
| T4-2-A | T4 | A | RESULT_READY | PASS | PASS | 5/0 | 0.04537671/0.00000000 | 5 | 0/2 | none |
| T2-3-B | T2 | B | RESULT_READY | PASS | PASS | 9/0 | 0.07417003/0.00000000 | 9 | 0/5 | quota_after_useful_edit |

## Paired comparison

| Pair | A | B | A/B checks | A/B known cost (RMB) | A/B elapsed seconds | B successors |
|---|---:|---:|---:|---:|---:|---:|
| T1-1 | FAIL | FAIL | PASS/PASS | 0.01619874/0.04612944 | 24.854/57.484 | 0 |
| T1-2 | FAIL | PASS | PASS/PASS | 0.03958461/0.06120921 | 58.963/94.963 | 0 |
| T1-3 | PASS | PASS | PASS/PASS | 0.02797617/0.06084642 | 36.473/100.111 | 0 |
| T2-1 | FAIL | FAIL | PASS/PASS | 0.09564061/0.01387035 | 185.722/232.174 | 0 |
| T2-2 | FAIL | PASS | PASS/PASS | 0.04052505/0.01571163 | 96.848/55.215 | 0 |
| T2-3 | PASS | PASS | PASS/PASS | 0.04370800/0.07417003 | 70.497/140.822 | 1 |
| T3-1 | PASS | FAIL | PASS/PASS | 0.02240820/0.13855328 | 26.647/492.467 | 2 |
| T3-2 | PASS | FAIL | PASS/PASS | 0.01941668/0.07492513 | 19.207/93.382 | 1 |
| T3-3 | PASS | PASS | PASS/PASS | 0.04120722/0.01811524 | 75.114/19.593 | 1 |
| T4-1 | PASS | FAIL | PASS/PASS | 0.06210463/0.14659498 | 80.527/131.718 | 1 |
| T4-2 | PASS | FAIL | PASS/FAIL | 0.04537671/0.03637312 | 65.008/46.679 | 0 |
| T4-3 | PASS | PASS | PASS/PASS | 0.12611272/0.04414256 | 234.257/64.323 | 0 |
| T5-1 | FAIL | FAIL | FAIL/FAIL | 0.06232352/0.45751473 | 86.127/1745.760 | 2 |
| T5-2 | FAIL | FAIL | FAIL/FAIL | 0.00421577/0.00421913 | 66.866/68.365 | 1 |
| T5-3 | FAIL | FAIL | FAIL/FAIL | 0.00000000/0.06385344 | 6491.726/288.489 | 0 |
| T6-1 | FAIL | PASS | PASS/PASS | 0.10369901/0.05034409 | 200.101/60.203 | 0 |
| T6-2 | FAIL | PASS | FAIL/PASS | 0.00324473/0.07926930 | 67.133/166.248 | 0 |
| T6-3 | FAIL | FAIL | PASS/PASS | 0.07586553/0.04686349 | 136.090/69.282 | 2 |

## Replacement executions

| Execution | Task type | V4 Pro known requests | V4 Pro response-unknown requests | Outcome |
|---|---|---:|---:|---|
| T4-1-B | new_managed_repository_software | 6 | 1 | FAIL (UNABLE_TO_COMPLETE) |
| T3-2-B | constrained_refactor | 4 | 1 | FAIL (UNABLE_TO_COMPLETE) |
| T5-2-B | coordinated_api_client_two_repositories | 0 | 1 | FAIL (UNABLE_TO_COMPLETE) |

## Qualification findings

- All three preassigned replacement B executions created a `deepseek-v4-pro/high` successor and sent a real request across three task types.
- Eight of 18 recovery-arm executions reached ResultReady and passed every frozen check. Ten B failures therefore fail the zero-tolerance outcome gate.
- Every T5 run failed. The frozen combined pytest command imports two repositories that both define a top-level `tests` package; collection fails before executing either suite. The two suites pass when run independently, but the frozen command was retained unchanged.
- Provider decisions were intermittently inadmissible after working output passed independent checks. These remain terminal failures; no failed real Provider request was automatically retried.
- No benchmark execution recorded a Human technical intervention. Harness defects were repaired without changing task content or accepted outcomes, and their history remains in the ledger.
- Median raw B-minus-A elapsed difference across available pairs: 34.315 seconds. Raw elapsed includes prescribed waits; detailed per-execution basis is in the JSON ledger.
- Intent/constraint retention is evidenced only where frozen independent checks pass. A full independent criterion-to-output trace and blinded 0–4 scoring remain unavailable because the frozen contract omitted scoring anchors.

Authoritative machine-readable evidence: `.spg/validation-evidence/native-cont/results.json` and `frozen-plan.json`.
