# Watt Multi-PWU Production Qualification — 2026-09-26

## Baseline and boundary

Before this change, `ProductionPlanProposal.ordered_steps` was durable but
`RuntimeService.create_initial_runtime_spine` admitted one PWU per Run. The
Run's initial source baseline was also the only PWU source admitted by the
preparation, execution, completion, verification, candidate and commit gates.
The native capacity scheduler already leased distinct PWUs, but a Work did not
own a persisted dependency graph or automatically activate successor PWUs.

The current implementation keeps Steering as the Work's `WHAT NEXT` authority,
PWU as meaningful production responsibility, Executor as `HOW`, independent
Verification as the acceptance gate, and Human authorization at the existing
candidate/delivery boundary. It adds no permission from a planning suggestion.

## Implemented production reality

- `ProductionPlanGraph` persists semantic groups separately from an executable
  PWU/Join DAG on versioned Plan revisions. Parallel overlapping writes are
  rejected unless an explicit Join reconciliation policy protects them.
- Each PWU has a scoped completion/task/change contract, exact input baseline,
  exact verified output, parent baseline vector, and its own Attempt evidence.
  Estimated target effort is compared with a PWU envelope; a coherent unit with
  no safe split point returns `NEEDS_REFINEMENT` instead of being time-sliced.
- Serial successors consume the predecessor's verified output. Parallel roots
  keep the same exact ancestor input and isolated workspaces; branch completion
  does not advance the Work integrated baseline. A Join PWU consumes every
  verified parent, composes their trees in Plan order, records conflicts, and
  still runs the normal production/verification/admissibility chain.
- An unchanged conflict tree is `NOT_ADMISSIBLE`; a subsequent bounded Attempt
  can change and verify the integration tree. The verified Work integrated
  baseline advances at serial checkpoints and after Join, never on unjoined
  branch completion.
- Final Candidate, Human authorization, repository compare-and-swap and Runtime
  Commit are bound to the Work's original authoritative source revision, while
  the final PWU and all Plan PWUs prove their exact internal input/output
  lineage. The Candidate fingerprint includes the graph's verified outputs.
- Re-planning preserves the superseded Plan and completed PWUs, marks
  unstarted future PWUs `SUPERSEDED`, and starts the replacement graph from the
  verified integrated checkpoint. Attempted/in-flight units and authority
  expansion cannot silently disappear. Work/API/Control Room project active
  Plan revision, hierarchy, dependencies, PWU states and blockers.

## Qualification evidence

| Case | Real evidence |
| --- | --- |
| Q1 serial | `test_three_serial_pwus_inherit_exact_verified_predecessor_baselines`: B0 → A → B → C; each input equals preceding verified output; replay of output publication is idempotent. |
| Q2 parallel | `test_two_ready_pwus_of_one_work_receive_distinct_concurrent_worker_leases`: same Work and source vector, two READY roots, two active worker leases. The real runtime test uses separate Git workspaces. |
| Q3 fan-in and successor | `test_real_parallel_branch_outputs_join_only_after_verification`: BA and BB remain branch outputs; Join consumes their exact vector; D starts only from verified Join output. |
| Q4 deterministic integration | The same test checks both disjoint files in the integrated tree and exact final Candidate/authorized repository integration/Runtime Commit. |
| Q5 mechanical conflict | `test_join_conflict_requires_changed_verified_resolution_tree`: real Git add/add conflict, unchanged conflict tree rejected as inadmissible, successor Attempt resolves it, independent Verification precedes trusted baseline. |
| Q6 unresolved meaning | `test_multi_pwu_semantic_join_conflict_reenters_human_steering`: disjoint Git changes compose cleanly but independent Verification reports incompatible Product Intent. Join stops without an autonomous retry, Work baseline stays at the ancestor, and a conversational Steering decision appears in Human Actions. Textual conflicts also retain both interpretations without choosing a winner; exhausted bounded recovery projects attention. |
| Q7 completion order | The fan-in test runs with A-first and B-first; both produce the same admitted integrated content and fixed dependency semantics. |
| Q8 restart/resume | The fan-in test reconstructs `RuntimeService` after the first branch, reads its published output, completes the second branch and Join, and confirms output publication/reconciliation are idempotent. Existing native lease recovery tests remain in regression. |
| Q9 re-plan | `test_serial_baseline_progression_and_replan_preserve_completed_history`: Plan v1, completed A, superseded unstarted B/C, Plan v2 with exact A checkpoint input. API test checks active revision projection. |
| Q10 scoped context/authority | The Work test inspects each root's exact change targets, empty broad allowed areas and PWU-specific Task Contract scope; context package assembly filters to node references or one essential source. |
| Q11 automatic continuation | Real Work and runtime tests advance READY roots and successor inputs without a Human next-PWU action. Human acts at final Candidate authorization. |
| Q12 hierarchy | Planner test checks semantic groups and a separate executable DAG; the production graph is stored with the Plan revision. |
| Q13 sizing | Planner tests check a 3,000-second candidate split into coherent 1,500-second PWUs under a 1,800-second envelope; an oversized inseparable family requests refinement. |
| Q14 parallel safety | Shared-interface change surfaces become serial; graph validation rejects unprotected overlapping parallel writes. Explicit overlap requires a Join reconciliation policy. |

## Regression and limits

Final full backend regression including Q6: 1,403 collected, 1,400 passed,
three skipped, no failures. Frontend JavaScript: 75/75 passed.
Python compile and `git diff --check`: passed. PostgreSQL upgraded to the
single Alembic head `20260926_51`; the required graph, lineage and tree-identity
columns exist. A downgrade past the multi-PWU migration is refused when the
database contains multiple PWUs, revised Plans or verified successor lineage.
Legacy single-PWU migration round trips remain possible. A round trip through
an older schema cannot preserve the later optional Git tree identity; the
legacy revision, repository namespace and trusted pointer remain exact.
Two skipped tests require the unavailable qualified local container image
`watt-engineering-semantic-human-retest-app:latest`. Cross-repository
integration tests ran against the available sibling production-foundation
checkouts; one optional ECF preview contract is absent at that checked-out
revision and is the third skip, not a claimed pass.
Human end-to-end acceptance of this new multi-PWU capability has not been
recorded.

```text
WORK_AUTOMATICALLY_DECOMPOSES_TO_MULTIPLE_PWUS = PASS
PRODUCTION_PLAN_IS_VERSIONED = PASS
SEMANTIC_HIERARCHY_AND_PWU_DAG = PASS
EXACT_SERIAL_AND_PARALLEL_BASELINE_LINEAGE = PASS
EXPLICIT_MULTI_PARENT_JOIN_AND_VERIFIED_RECONCILIATION = PASS
MULTIPLE_READY_PWUS_CAN_EXECUTE_CONCURRENTLY = PASS
AUTOMATIC_SUCCESSOR_PROGRESS_AND_BOUNDED_REPLAN = PASS
HUMAN_AUTHORIZATION_BOUNDARY = PASS
FULL_MULTI_PWU_RUNTIME_QUALIFICATION = PASS
BACKEND_REGRESSION = PASS_1400_OF_1403_WITH_3_ENVIRONMENT_SKIPS
FRONTEND_REGRESSION = PASS_75_OF_75
HUMAN_ACCEPTANCE = PENDING
```
