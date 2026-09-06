# MVP-SPG-GRANULARITY-1B — Focused Validation Evidence

## Result

```text
MVP-SPG-GRANULARITY-1B
    CLOSED / PASS
    ARCHITECTURE LEAD FINAL EVIDENCE REVIEW = PASS
    FRESH REAL MULTI-TURN EXECUTOR PROOF = PASS

SPG_EXECUTION_GRANULARITY_CALIBRATION_REQUIRED
    RESOLVED BY FRESH REAL MULTI-TURN EXECUTOR EVIDENCE
```

Initial focused validation used a strict fake Codex Thread and an isolated
disposable PostgreSQL database. The later fresh proof used two real Provider
Turns inside one Attempt and is recorded in [Fresh Real Multi-turn Executor
Proof](mvp-spg-granularity-1b-real-provider-proof.md). Historical Dogfood
Runtimes and their Provider evidence were not used as mutable test state and
were not modified.

## Implementation Reality

One outer `ExecutorCapabilityContract.dispatch` now permits the configured
Codex adapter to run bounded internal Turns on one ephemeral Thread. The exact
PWU, Attempt, generation, Workspace, Source Basis, materialized input
fingerprint, sandbox, and total time budget remain fixed. A continuation
revalidates the static dispatch identity and exact Git worktree/HEAD basis while
allowing produced changes in the isolated Workspace.

The loop ends with one of `RESULT_READY`, `UNABLE_TO_COMPLETE`,
`BOUNDARY_CROSSING_REQUIRED`, `BUDGET_EXHAUSTED`, or
`EXECUTION_CONTINUITY_LOST`. The result is an Executor claim. One aggregate
Provider Report records safe operational metadata; no internal Turn is a
durable SPG lifecycle fact.

The default internal-Turn bound is three, matching the admitted principal
diagnose-correct-revalidate regression, and remains configurable. The existing
Provider timeout is enforced as a total loop budget. Exact repeated activity
summaries stop with `REPEATED_NO_PROGRESS`. Reliable token/cost enforcement,
durable per-Turn recovery, and UI progress remain deferred.

## SPG-GRAN Evidence

| Obligation | Evidence |
|---|---|
| SPG-GRAN-01 | A strict fake Provider performs three Turns on one Thread for one PWU/Attempt. |
| SPG-GRAN-02 | PostgreSQL integration retains exactly one `production_work_units` row. |
| SPG-GRAN-03 | PostgreSQL integration retains exactly one `execution_attempts` row. |
| SPG-GRAN-04 | Exactly one outer `execution_dispatches` row is persisted. |
| SPG-GRAN-05 | Exactly one aggregate `provider_execution_reports` row is persisted with `internal_turn_count=3`. |
| SPG-GRAN-06 | Rendered input includes Resource, Repository/ref, Baseline, PWU/Attempt/generation, scope, constraints, Completion and execution policy. |
| SPG-GRAN-07 | Generic `required_markers` are rendered. |
| SPG-GRAN-08 | Generic `forbidden_changes` are rendered. |
| SPG-GRAN-09 | Generic `blocking_conditions` are rendered. |
| SPG-GRAN-10 | Maximum-Turn, total-time and repeated-no-progress guards terminate continuation. |
| SPG-GRAN-11 | `BOUNDARY_CROSSING_REQUIRED` stops without a follow-up Turn or test mutation. |
| SPG-GRAN-12 | Failed continuation validation returns `EXECUTION_CONTINUITY_LOST` before a second Turn. |
| SPG-GRAN-13 | Aggregate success creates no Completion or Verification record; the same PostgreSQL scenario then invokes independent Completion and Verification and records exact PASS evidence. |
| SPG-GRAN-14 | ORCH sees only the outer Dispatch/report and does not inspect or schedule internal Turns. |
| SPG-GRAN-15 | Focused Steering compatibility passes without creating a Steering action for ordinary repair. |
| SPG-GRAN-16 | A plain completed legacy one-Turn response remains `RESULT_READY`; deterministic and immediate-production paths remain compatible. |

## Trust and Scope Guard

`RESULT_READY` maps only to a Provider success claim. It does not mark a PWU
Produced or Satisfied and creates no Candidate, Authorization, Integration
Effect, or Runtime Commit. SPG independently observes the isolated Workspace
after the aggregate return, then retains its existing Completion, Verification,
Candidate, Human Authorization, integration, and Runtime Commit boundaries.

Boundary crossing is fail-closed: the instruction requires the Executor to stop
before expanding Scope, changing Resource/repository, entering forbidden areas,
changing the Completion Contract, or assuming a Human-owned decision. Even a
false Provider claim has no external production side-effect authority; the
Workspace remains isolated and independent Observation/Verification still
adjudicate actual paths and content.

## Scope Compliance

1B adds no migration, per-Turn persistence, resume-after-crash machinery,
internal Turn state machine, distributed execution, Multi-PWU/DAG, generic
Agent framework, ECF, Guardian change, retry redesign, Human gate, or UI
redesign. ORCH and Plan Steering responsibilities remain unchanged.

`SEMANTIC_EXECUTION_OBSERVABILITY_GAP` remains **CONFIRMED / PARTIALLY
MITIGATED / OPEN**. Aggregate activity and iteration metadata improve the
execution seam but do not close product-level progress observability.

## Focused Validation

- Affected Executor, execution/observation, ORCH, Work/API, Steering, and
  compatibility suites: **219 passed, 2 skipped**. The skipped cases are the
  explicitly opt-in real-Provider probes.
- After strengthening the independent-Verification assertion, the complete
  affected Codex SDK integration file was rerun successfully (47 collected;
  its real-Provider probe remained opt-in).
- Fresh PostgreSQL integration proved three internal Turns on one Thread with
  one PWU, one Attempt, one Dispatch, and one aggregate Provider Report, then
  independently admitted Completion and Verification PASS.
- Alembic repository head and disposable-database current revision both equal
  `20260905_22 (head)`; no migration was added.
- Compile/import, `uv lock --check`, and `git diff --check`: **PASS**.
- Initial focused-validation Provider Turns: **0**. Fresh closure proof:
  **2 real Turns on one Thread**.
