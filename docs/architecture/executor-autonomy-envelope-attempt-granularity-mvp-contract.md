# Executor Autonomy Envelope / Attempt Granularity MVP Contract

## 1. Contract Result

```text
SPG_EXECUTION_GRANULARITY_CALIBRATION_REQUIRED
    CONFIRMED

Calibration decision
    B — BOUNDED GRANULARITY CALIBRATION REQUIRED

MVP-SPG-GRANULARITY-1A
    BEHAVIORAL CONTRACT DEFINED / ADMITTED
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-SPG-GRANULARITY-1B
    CLOSED / PASS
    ARCHITECTURE LEAD FINAL EVIDENCE REVIEW = PASS
    FRESH REAL MULTI-TURN EXECUTOR PROOF PASS
```

The fundamental SPG architecture remains sound. The calibration target is the
Executor execution grant, not a redesign of Work, Plan Steering, PWU, Attempt,
Verification, Candidate governance, or Runtime Commit.

The governing principle is:

> **Govern the execution envelope, not every Executor move.**

Bounded does not mean tiny. A Provider Turn is not a production-governance
unit. Internal technical iteration belongs inside one continuous Attempt while
the admitted envelope remains valid. Independent Verification remains external.

1A defines the behavioral contract; 1B implements its bounded Slice behind the
existing Executor capability. Fresh real Provider evidence closed the
calibration Finding; that checkpoint did not itself declare MVP Core Closure.
Subsequent Dogfood #9/#10 evidence closes the Core without changing this
contract. See [Fresh Real
Multi-turn Executor Proof](../evidence/mvp-spg-granularity-1b-real-provider-proof.md).

## 2. PWU Semantics

A PWU is one bounded production mission governed by a stable:

- objective;
- Engineering Resource and repository identity;
- repository/source Baseline;
- Authority, Scope, constraints, allowed areas, and forbidden areas;
- Completion Contract;
- Verification obligations;
- risk, execution-budget, and sandbox policy;
- STOP conditions.

A PWU is not one model call, Provider Turn, tool call, file edit, test
execution, or self-refine iteration. It may contain repository inspection,
several implementation actions, multiple changed files, internal validation,
diagnosis, and repair when those activities serve the same stable production
mission.

PWU granularity follows the stability of the governed mission and envelope,
not the number of model or tool actions. A new PWU is appropriate when the
production objective, resource, repository, admitted Authority, Completion
Contract, Verification obligations, or production direction materially
changes—not merely because implementation required another edit or test.

This preserves the existing distinction between broad or long-lived Work and
bounded production in [Motive / Work / Plan Concept
Calibration](motive-work-plan-concept-calibration.md), and the one-PWU planning
boundary in [Single-PWU Production Planner Intelligence
Lite](single-pwu-production-planner-lite.md).

## 3. Attempt Semantics

An Attempt is one continuous execution grant against one PWU under a stable:

- PWU and execution generation;
- isolated Workspace and its continuity;
- Engineering Resource, repository, and Source Basis;
- Authority Envelope and Completion Contract;
- Executor binding and sandbox policy;
- bounded execution budget.

One Attempt may contain multiple internal Provider Turns, repeated tool calls,
and diagnose-fix-validate iterations. These are not separately authoritative
Runtime transitions. The Attempt remains one lineage and one execution grant
while its generation, Workspace, basis, contract, and budget remain valid.

A new Attempt is required when execution-authority continuity has materially
ended, including when:

- the prior Attempt terminally released its grant;
- its generation was fenced;
- Workspace continuity was lost or became untrustworthy;
- its Source Basis changed or became stale;
- governed recovery authorized re-execution;
- Provider or execution-strategy replacement requires new lineage;
- the admitted execution contract materially changed.

A failed test, another edit, an additional reasoning Turn, or a bounded
technical compatibility correction does not by itself require a new Attempt.
Existing recovery behavior remains authoritative after continuity is lost; the
new semantics must not disguise a recovery retry as continuation.

## 4. Internal Self-refine Boundary

The Executor owns HOW inside the admitted Attempt envelope. The following are
Executor-internal activities:

- repository inspection and local implementation planning;
- multiple edits and tool calls;
- internal test execution and intermediate checks;
- diagnosis and repair;
- bounded Provider continuation;
- compatibility corrections and local revalidation.

These activities do not individually create a PWU, Attempt, Steering Step,
Human Attention record, Candidate, or trusted Verification result. They may
emit non-authoritative operational progress, but they do not acquire Truth or
Authority merely by being reported.

Internal self-refine ends before any action that would widen Scope, change
Resource or repository, enter a forbidden area, materially change the
Completion Contract, assume a Human-owned product/architecture/risk decision,
or mutate a side effect outside the admitted policy.

## 5. Continuation Eligibility

Another internal Turn is eligible inside the same Attempt only when all of the
following remain true:

1. The same PWU and execution generation remain current.
2. The same isolated Workspace remains continuous and trustworthy.
3. The Engineering Resource, repository, and Source Basis remain exact.
4. The Authority, Scope, constraints, allowed areas, and forbidden areas are
   unchanged.
5. The Completion Contract and Verification obligations are unchanged.
6. No forbidden-area or forbidden-change violation is known.
7. No Human-owned decision or Authority expansion is required.
8. The Attempt is not stale, fenced, cancelled, or superseded.
9. Configured turn, elapsed-time, and observable token/cost budgets remain.
10. No terminal STOP condition, repeated-failure threshold, or no-progress
    threshold has fired.

Eligibility must be rechecked by the execution host before each continuation.
The Executor may reason about progress, but it cannot waive or widen these
conditions. If a condition is not provably true, continuation stops fail
closed.

## 6. Return-control / STOP Boundary

The aggregate Executor result must distinguish at least these meanings:

### `RESULT_READY`

The Executor believes it has produced the best candidate result permitted by
the current Completion Contract. Control returns to SPG for independent
Observation, Completion Evaluation, and Verification. This is a provider
claim, not trusted completion.

### `UNABLE_TO_COMPLETE`

The Executor cannot satisfy the contract inside the admitted envelope. SPG
records truthful failure or blocking Reality; it does not infer permission to
widen the contract.

### `BOUNDARY_CROSSING_REQUIRED`

Completion appears to require Scope expansion, Resource/repository change,
forbidden access, a materially different Completion Contract, or a Human-owned
product, architecture, risk, or cost decision. Execution stops before the
boundary is crossed.

### `BUDGET_EXHAUSTED`

A configured turn, elapsed-time, token, or cost bound has been reached. SPG
records the bounded stop without treating partial work as satisfaction.

### `EXECUTION_CONTINUITY_LOST`

Workspace, generation, Source Basis, process, or session continuity is no
longer trustworthy. Existing recovery assessment and new-Attempt semantics
apply.

Cancellation, shutdown, stale basis, fencing, sandbox denial, repeated failure,
and no progress are also STOP causes and must map conservatively to one of the
above return-control meanings. No return-control outcome creates Candidate,
Authorization, or Commit authority by itself.

## 7. Dispatch / Provider-turn Semantics

The target MVP shape is:

```text
PWU
  → Attempt
    → one governed outer Dispatch / execution grant
      → bounded internal Provider and tool self-refine
    → one aggregate Executor result / Provider Report
```

The durable Dispatch remains the SPG grant issued before provider execution.
The aggregate Provider Report remains an untrusted claim tied to that exact
Dispatch, Attempt, generation, binding, and time interval. Internal Turns are
implementation details of the Executor capability and do not each become an
SPG lifecycle fact.

The current `ExecutorCapabilityContract.dispatch(...)` shape can remain the
outer boundary. The first implementation should extend the configured Executor
and Codex adapter behind that interface rather than introduce an internal-Turn
domain state machine. Existing one-Turn adapters remain valid implementations
that return after their first terminal result.

Durable resume at an exact internal Turn after process restart is deferred. If
continuity cannot be proven after restart, the Attempt returns
`EXECUTION_CONTINUITY_LOST` and uses normal recovery/new-Attempt governance.

## 8. Complete Executor Envelope

The materialized Executor input must expose the complete admitted facts needed
for autonomous execution:

- PWU objective and identity;
- Engineering Resource and repository identity;
- exact Source Baseline/ref and Workspace identity;
- exact targets and allowed Scope;
- forbidden areas and forbidden changes;
- all inherited and artifact/change constraints;
- complete Completion Contract;
- required outputs, changes, and markers;
- blocking conditions;
- Verification obligations and commands/subjects where admitted;
- sandbox and external side-effect policy;
- turn/time/token/cost budget dimensions that are configured and observable;
- cancellation, stale-basis, boundary-crossing, repeated-failure, no-progress,
  and other STOP conditions.

The current renderer already supplies objective, production-plan content,
artifact/change target information, paths, constraints, and change-contract
verification. It does not generically render every Completion Contract field,
notably required markers, generic forbidden changes, and blocking conditions.
1B closes that rendering gap without fabricating missing facts or duplicating
Authority.

Budget information must come from admitted configuration. Current Repository
Reality provides a bounded Provider timeout and sandbox selection; it does not
yet provide admitted turn, token, cost, no-progress, or repeated-failure
policies. Those require explicit small configuration/contract extensions and
must not be invented as fixed production numbers.

## 9. PLAN-1B Calibration

`ProductionPlanProposal.ordered_steps` are non-authoritative execution-strategy
hints unless a step restates a governed requirement already owned by the
objective, target/change contract, Authority Envelope, Completion Contract, or
Verification obligations.

PLAN-1B may express:

- the production objective and desired outcome;
- exact target/change contract;
- admitted boundary and constraints;
- Done criteria;
- Verification obligations;
- useful high-level strategy hints.

It must not become a second implementation brain that requires SPG to prescribe
repository exploration, every edit, every test, or every correction. Generic
advice does not acquire Authority merely by appearing in `ordered_steps`.

The field and existing API representation remain for compatibility. 1B renders
the steps explicitly as advisory, and the Executor may choose a different
internal sequence while satisfying the same governed contract.

## 10. Verification Preservation

Executor internal tests and self-checks are not trusted Verification.

After `RESULT_READY`, the existing external sequence remains unchanged:

```text
independent repository Observation
  → Completion Evaluation
  → independent Verification
  → Candidate
  → Human Authorization where required
  → Repository Integration
  → Runtime Commit
```

No internal Turn may mark the PWU Produced or Satisfied, seal a Candidate,
authorize integration, or advance the Trusted Baseline. The implementation
must continue to evaluate immutable observed evidence against the admitted
Completion Contract and exact Verification subject.

## 11. Plan Steering Preservation

The responsibility boundary remains:

```text
Plan Steering     WHAT NEXT
SPG               UNDER WHAT GOVERNED EXECUTION ENVELOPE
Executor          HOW
Verification      DID THE OBSERVED RESULT SATISFY THE CONTRACT
```

Ordinary inspection, implementation, test failure, diagnosis, repair, and
local revalidation do not invoke Plan Steering. Control returns to Steering
when governed Reality requires a material production-direction decision, the
current Step is complete or blocked, a new production mission must be formed,
or the existing envelope cannot lawfully contain the required work.

The PRODUCE admission boundary, PLAN-1B `ONE_PWU_FIT` check, Steering-to-SPG
bridge, and Steering-level Work completion semantics remain unchanged.

## 12. Bounded-autonomy Policy

MVP bounded autonomy must support configurable dimensions for:

- maximum internal Provider Turns;
- elapsed execution time;
- token and cost budget when the provider reports them reliably;
- no-progress detection;
- repeated same-failure detection;
- sandbox and external side-effect policy;
- cancellation and orderly shutdown;
- stale Source Basis, generation, and Workspace checks.

The implementation must not claim enforcement of token or cost limits when
those measurements are unavailable. It must always enforce the configured
time bound already present, sandbox policy, generation/basis checks available
at the execution boundary, and a finite internal-Turn bound. No numeric default
is admitted by this contract; defaults must be selected from implementation
and provider Reality in the next Slice.

The loop terminates on result readiness, inability, boundary crossing, budget
exhaustion, continuity loss, cancellation, or a configured no-progress/repeated
failure rule. Unlimited autonomous looping is prohibited.

## 13. Observability Boundary

Internal self-refine must not be an invisible black box, but operational
progress is not production-governance truth. A minimum future projection may
include:

- Executor active;
- inspecting/planning;
- implementing;
- validating;
- self-refining;
- blocked/stopped;
- approximate internal iteration count;
- a safe current bounded-activity summary.

These may be ephemeral events or aggregate report metadata. They do not create
new PWUs, Attempts, Steering Steps, Candidates, or Runtime transitions. 1B adds
only aggregate metadata needed to prove bounded iteration; UI redesign and
durable per-Turn history remain deferred.

`SEMANTIC_EXECUTION_OBSERVABILITY_GAP` remains **CONFIRMED / PARTIALLY
MITIGATED / OPEN**. This contract clarifies the boundary but does not close the
product observability finding.

## 14. Semantic Provider Regression Semantics

The real Semantic Provider integration incident supplies the acceptance
semantics, not a production-specific hard-coded task:

```text
mission: make the real semantic Provider integration pass

diagnose schema incompatibility
  → modify within the admitted repository scope
  → real validation
  → diagnose the next compatibility issue
  → modify
  → real validation
  → PASS
```

The objective, Source Basis, Authority, constraints, Completion target, and
Verification obligations remain stable throughout. Expected governance is:

```text
PWU = 1
Attempt = 1
outer Dispatch / aggregate Provider Report = 1 / 1
internal Provider Turns may be greater than 1
Human technical intervention = 0
Authority expansion = 0
independent final Verification remains external
```

The 1B regression remains deterministic and provider-neutral. A separate fresh
real proof confirms that the same admitted model works with two actual Provider
Turns and independent Verification. The historical semantic-provider closure
also remains evidence in [Semantic Provider Integration — Bounded Self-refine
Closure](../evidence/dogfood/semantic-provider-integration-self-refine-closure.md).

## 15. Repository Compatibility Map

| Location / responsibility | Classification | Required treatment |
|---|---|---|
| `domain/executor.py` — `ExecutorCapabilityContract` | **REUSE** | Keep one outer `dispatch` capability boundary. |
| `application/execution.py` — Dispatch, report, independent Observation | **REUSE** | Keep one durable Dispatch and one aggregate Provider Report; do not model internal Turns here. |
| `providers/codex_sdk_executor.py` — one ephemeral Thread/Turn | **SMALL EXTENSION** | Host a bounded internal continuation loop while preserving exact workspace, sandbox, timeout, and final aggregate result. |
| `infrastructure/configured_executor.py` — composition and instruction rendering | **SMALL EXTENSION** | Render the complete envelope, policy, STOP conditions, and advisory status of Plan steps. |
| `infrastructure/codex_executor_binding.py` / dedicated child boundary | **SMALL EXTENSION** | Carry admitted loop policy and aggregate safe iteration metadata without exposing secrets. |
| `domain/execution.py` — Dispatch/result/report types | **SMALL EXTENSION** | Add the narrowest return-control classification and aggregate metadata needed; avoid per-Turn domain facts. |
| Attempt lifecycle and persistence | **REUSE** | One continuous grant remains one Attempt; existing fencing and lineage remain authoritative. |
| ORCH | **REUSE** | Continue sequencing governed facts; do not drive internal implementation moves. |
| Completion and Verification | **REUSE** | Preserve independent Observation, Completion Evaluation, and Verification after aggregate execution return. |
| PLAN-1B proposal/API | **REUSE** | Preserve ordered steps for compatibility; define/render them as non-authoritative hints. |
| Attempt recovery | **REUSE** | Continue to require a new Attempt after continuity loss or governed retry authorization. |
| Durable per-internal-Turn resume/history | **DEFER** | No internal-turn state machine or new persistence in the MVP Slice. |
| UI progress redesign | **DEFER** | Preserve the open observability finding. |

No current type creates an unavoidable conflict. `ExecutorDispatchResult` can
remain the aggregate outer result if its outcome/metadata are extended
narrowly. If explicit return-control types are added, they must remain provider
claims and must not replace `ProviderReportedOutcome`, Completion, or
Verification truth.

## 16. Implementation Slice Recommendation

MVP-SPG-GRANULARITY-1B is the bounded Executor Autonomy implementation, not an
SPG redesign. Its focused validation proves:

1. One PWU and one Attempt can contain multiple internal Provider Turns.
2. Diagnose-fix-validate iterations do not create new PWUs or Attempts.
3. The complete Authority, Completion, Verification, budget, and STOP envelope
   reaches the Executor.
4. A finite configurable policy bounds continuation.
5. Boundary expansion stops before unauthorized action.
6. Internal validation does not replace independent Verification.
7. One outer Dispatch and aggregate report are sufficient.
8. Existing one-Turn Executor behavior remains compatible.
9. ORCH remains the governance coordinator rather than an implementation
   planner.
10. Ordinary repair loops do not invoke Plan Steering.

The implementation uses the admitted narrow seam: an Executor-hosted loop
behind the existing capability contract, complete envelope rendering, and
focused provider-neutral tests. The existing aggregate result/report carries
the bounded outcome, so no database migration is introduced. Exact restartable
internal-Turn recovery remains explicitly outside the Slice.

## 17. SOT Updates

This contract admits:

```text
SPG_EXECUTION_GRANULARITY_CALIBRATION_REQUIRED
    RESOLVED BY FRESH REAL MULTI-TURN EXECUTOR EVIDENCE

Calibration decision
    B — BOUNDED GRANULARITY CALIBRATION REQUIRED

Govern the execution envelope, not every Executor move.
Bounded does not mean tiny.
Provider Turn is not a production-governance unit.
Executor self-refine belongs inside a continuous Attempt while the governed
envelope remains stable.
Independent Verification remains external.

MVP-SPG-GRANULARITY-1A
    BEHAVIORAL CONTRACT DEFINED / ADMITTED
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-SPG-GRANULARITY-1B
    CLOSED / PASS
    ARCHITECTURE LEAD FINAL EVIDENCE REVIEW = PASS
    FRESH REAL MULTI-TURN EXECUTOR PROOF PASS
```

This contract did not itself declare MVP Core Closure. The later
[Watt MVP Core Closure](../evidence/mvp-core-closure.md) does not reclassify any
historical Dogfood, Runtime, Attempt, Provider evidence, or Trusted Baseline.

## 18. Risks / STOP Conditions

Implementation must stop for Architecture Lead review if it would require:

- unlimited or unobservable autonomous looping;
- allowing the Executor to widen Authority, Scope, Resource, repository, risk,
  or Completion Contract;
- treating internal validation or Provider success as trusted Verification;
- collapsing Observation, Verification, Candidate, Authorization, Integration,
  or Runtime Commit into the Executor;
- reusing an Attempt after generation, basis, or Workspace continuity is lost;
- turning every internal Turn/tool action into a governed SPG state transition;
- adding a durable internal-turn state machine or distributed execution;
- invoking Plan Steering for ordinary technical repair;
- weakening Candidate Authorization or external side-effect governance;
- introducing Multi-PWU, DAG, ECF, Guardian changes, a generic Agent framework,
  advanced retry, new Human gates, or UI redesign;
- rewriting historical Runtime or Provider evidence.

The principal delivery risks are hidden cost/runaway loops, stale-basis work,
loss of Attempt lineage, Authority ambiguity in Plan hints, accidental
self-verification, and inadequate progress visibility. The bounded policy,
fail-closed continuation checks, external Verification, and aggregate
operational metadata are the minimum mitigations.
