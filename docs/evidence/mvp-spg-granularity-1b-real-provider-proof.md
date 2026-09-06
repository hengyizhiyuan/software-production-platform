# MVP-SPG-GRANULARITY-1B — Fresh Real Multi-turn Executor Proof

## Result

```text
MVP-SPG-GRANULARITY-1B
    CLOSED / PASS
    ARCHITECTURE LEAD FINAL EVIDENCE REVIEW = PASS
    FRESH REAL MULTI-TURN EXECUTOR PROOF = PASS

SPG_EXECUTION_GRANULARITY_CALIBRATION_REQUIRED
    RESOLVED BY FRESH REAL MULTI-TURN EXECUTOR EVIDENCE
```

The proof used disposable PostgreSQL, Runtime facts, Git repository/worktree,
and Codex state. Historical `watt-motive-dogfood-1` through `-6` Runtimes were
not reused or modified.

## Real Scenario

One documentation PWU changed only
`docs/codex_real_execution_probe.md` from the admitted `BEFORE` marker to the
admitted `AFTER` marker. The execution contract required the Executor to use a
first Turn for inspection and the exact edit, return `CONTINUE`, then use a
second Turn to re-read the exact diff, execute `git diff --check`, repair only
in scope if needed, and return `RESULT_READY` after revalidation.

This is one production mission and one stable execution envelope. The two
phases are Executor-owned HOW activity, not separate PWUs, Attempts, Dispatches,
or Steering Steps.

## Exact Real Evidence

```text
Provider Thread
    01a0747b-034b-7892-b752-f16203cef2d5

Terminal Turn
    01a0747d-0a0f-7db3-8ce2-9a5b2eae5e67

PWU / Attempt / outer Dispatch / aggregate Provider Report
    1 / 1 / 1 / 1

internal_turn_count
    2

self_refine_occurred
    true

terminal_executor_outcome
    RESULT_READY

executor_stop_reason
    EXECUTOR_RESULT_READY
```

Turn 1 inspected the clean isolated repository and made the sole admitted
marker edit, then returned `CONTINUE` without claiming completion. Turn 2
re-read the exact diff, confirmed the single path, ran `git diff --check`, and
returned `RESULT_READY`. No Human Continue, retry, or repair instruction was
used.

## Envelope Continuity

```text
Attempt / Workspace
    de4a07f7-fcd9-4bef-b84b-8a6dc7395a97

Source revision before / after
    2c4bd344c828e2b6dbb36d57df9e70b055125898
    2c4bd344c828e2b6dbb36d57df9e70b055125898

Authoritative repository status before / after
    clean / clean

Materialized Execution Input
    1c0c2423-f7bc-506a-9236-caa3440db5ec

Input fingerprint
    8167d703932e15422f218d161bd0f66955d87dfa4fd13c04bc7e9edbed9ed784
```

The objective, generation, Resource/repository, Source Basis, exact target,
forbidden-change rule, Completion Contract, sandbox, total budget, and
Workspace identity remained fixed. Observation found exactly one `MODIFIED`
path and the authoritative ref did not move. No Authority widening, rebase,
commit, push, Candidate, Authorization, Integration Effect, or Runtime Commit
occurred.

## Independent Trust Establishment

The aggregate Provider Report was persisted before Completion or Verification;
both counts were zero at that boundary. SPG then independently observed the
Workspace and admitted:

```text
Completion Evaluation
    7283ae96-42c0-551b-8df4-df211c2d5810
    PRODUCED

Verification Record
    64fd4f01-2b59-5507-b6ad-5950dea01ad0
    PASS

Provider Report is Verification
    false
```

The Executor's internal `git diff --check` remained advisory. Trusted
Verification was a separate governed fact over the independently observed
subject.

## Self-refine Iterations

1. The first disposable attempt reached the old host probe's 120-second total
   timeout in Turn 1 and returned `BUDGET_EXHAUSTED` without repository change.
   The probe was aligned with the already admitted 600-second product E2E
   budget; no architecture or production semantics changed.
2. The next fresh attempt produced the required real two-Turn result and
   independent Verification PASS, then exposed one stale test assertion that
   still expected the PWU to remain `PROPOSED` after Completion. The assertion
   was corrected to the authoritative `PRODUCED` condition.
3. A third fresh Codex state and zero-fact Runtime produced the terminal PASS
   evidence above: `1 passed in 158.90s`.

These were bounded technical proof iterations. They required no Human
technical intervention and introduced no new Attempt inside any individual
run.

## Negative and Compatibility Evidence

The deterministic focused suite retains fail-closed coverage for boundary
crossing, stale/changed continuation basis, generation/Workspace continuity,
budget exhaustion, and repeated no-progress. It also retains normal legacy
one-Turn `RESULT_READY` behavior. The post-proof focused selection collected 62
tests: **61 passed, 1 skipped**. The skipped case was the opt-in real probe in
that deterministic rerun.

## Preserved Findings

`SEMANTIC_EXECUTION_OBSERVABILITY_GAP` remains **CONFIRMED / PARTIALLY
MITIGATED / OPEN**. Reliable token/cost accounting, durable per-internal-Turn
recovery, and UI progress redesign remain outside this Slice. MVP Core Closure
is not declared by this proof.
