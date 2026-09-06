# Duration & Capacity Semantic Foundation

## Status and Authority

**DCP-1: SEMANTIC FOUNDATION DEFINED / ADMITTED**

**Runtime implementation: NOT STARTED**

This document is the authoritative semantic foundation for future
duration-aware PWU sizing and capacity-aware production planning. It records
architecture vocabulary, responsibility boundaries, and evolution constraints.
It does not authorize a queue, scheduler, worker pool, concurrency limiter,
duration heuristic, prediction model, automatic decomposition, or migration.

Watt MVP Core remains **CLOSED / PASS**. DCP-1 is post-Core architecture work
and does not reopen or weaken any closed production-governance boundary.

## 1. Architecture Direction

Duration and capacity planning is expected to evolve from static advisory
estimation into continuously recalculated, Reality-driven operational planning:

```text
Work / PWU Shape
  × Executor Capability Profile
  × Execution Environment
  × Operational Reality
  × Historical Reality
      → time-varying execution and trusted-result estimates
      → capacity-aware operational planning
```

The two kinds of truth have different stability:

```text
Governed Production Truth
    = comparatively stable

Operational Plan
    = dynamically recalculable
```

Changing load, queue pressure, availability, latency, or estimates may change
an ETA, queue position, dispatch time, compatible Executor choice, or capacity
allocation. It must not silently mutate the governed Objective, Authority,
Scope, Completion Contract, Verification obligations, Candidate semantics,
Human Authority boundary, or Runtime Commit semantics. A required change to
those facts returns to the legitimate governance or Steering path.

## 2. Responsibility Boundaries

The future capability preserves the following ownership split:

| Responsibility | Ownership |
|---|---|
| Estimate likely workload or duration | Estimator advises |
| Govern the production envelope and PWU | SPG governs |
| Decide when scarce execution capacity may be granted | Future Capacity/Scheduling capability |
| Decide how to perform the admitted production mission | Executor executes |
| Establish independent trust | Verification verifies |
| Record what actually happened | Measurement records |
| Supply future calibration evidence | Governed Reality |

SPG must not become an implementation brain, resource scheduler, Executor
manager, runtime load balancer, or prediction engine. Capacity scheduling must
not gain authority to rewrite governed production contracts. Provider or model
identity is evidence/configuration, never Authority.

## 3. Two Related but Separate Problems

### 3.1 Duration-aware PWU Sizing

PWU sizing asks how large a governed production mission should be. Its primary
constraints are:

- semantic cohesion;
- authority coherence;
- independent verifiability;
- recoverability;
- bounded blast radius.

Preferred execution horizon and capacity efficiency are secondary
optimizations:

```text
Natural production boundary > duration preference
```

A cohesive, independently verifiable fourteen-minute PWU must not
automatically become two seven-minute PWUs merely to satisfy a preferred time
slot. Bounded does not mean tiny.

### 3.2 Capacity-aware Production Planning and Scheduling

Capacity planning asks when an already-governed production demand may receive
scarce execution capacity and, eventually, which compatible execution profile
may serve it. Queueing, concurrency budgets, resource availability, priority,
fairness, cost/latency policy, and deadlines are adjacent to SPG but are not
owned by SPG itself.

Current Watt has no governed queue or Capacity Scheduler. DCP-1 reserves the
boundary without assigning a final module name or claiming implementation.

## 4. ProductionMeasurement

**ProductionMeasurement** is the conceptual, provenance-bearing description of
what actually happened during a governed production lifecycle. Measurement is
the first duration/capacity capability that should mature.

Its future semantics must be able to distinguish at least:

```text
queued
→ admitted
→ execution
→ verification
→ Human wait
→ integration
→ trusted completion
```

Three evidence classes must remain explicit:

| Class | Meaning | Example |
|---|---|---|
| Observed Fact | A timestamp or event directly recorded by an authoritative boundary | `ProviderReport.started_at`, `finished_at` |
| Derived Interval | A duration computed from compatible observed facts | machine execution interval derived from those timestamps |
| Estimate | An uncertainty-bearing forecast | predicted 3–10 minutes |

Derived intervals must identify their observed basis. Estimates must never be
reported as measurements, and missing measurements must never be fabricated.
The current persistence model has strong identity continuity but incomplete
phase clocks; DCP-1 does not prescribe a telemetry schema.

## 5. Multidimensional Duration Reality

There is no authoritative generic `task_duration`. Future measurement and
estimation semantics must keep at least these dimensions distinct:

- `queue_wait_duration`;
- `machine_execution_duration`;
- `semantic_provider_duration` where applicable;
- `executor_duration`;
- `verification_duration`;
- `human_wait_duration`;
- `integration_duration`;
- `total_cycle_duration`;
- `trusted_result_horizon`.

Different consumers legitimately optimize different dimensions:

| Consumer | Relevant Reality |
|---|---|
| Executor pool | machine-active resource occupation |
| Capacity Scheduler | resource occupation plus downstream availability |
| User | end-to-end trusted-result latency |
| Governance | Human and authority wait boundaries |

Human wait, queue wait, network/external dependency wait, machine-active
execution, and Verification must not be blindly combined. Executor time alone
is not trusted-production time: five minutes of execution followed by twenty
minutes of Verification is not a five-minute trusted production job. Future
planning may therefore distinguish Execution Horizon, Verification Horizon,
and Trusted-result Horizon without assuming one shared resource pool.

## 6. TaskShapeSnapshot

**TaskShapeSnapshot** is a versioned, provenance-bearing planning-time capture
of the authoritative shape of a candidate production mission. It uses only
facts that exist before execution and must not be reconstructed later using
post-execution knowledge.

Candidate inputs supported by current Reality include:

- objective and desired outcome;
- target kind;
- exact target-path count;
- CREATE/UPDATE counts where represented;
- allowed-scope size and forbidden-scope presence;
- Completion obligations;
- Verification obligation count;
- ordered planning-step count;
- Engineering Resource and repository identity;
- Source Baseline identity;
- admitted context-reference count;
- Executor capability profile when already known at that planning boundary.

The snapshot must remain attributable to its source facts and version. It must
not invent unsupported semantic taxonomies or post-hoc features such as
numeric frontend or migration complexity scores merely because paths or prose
appear suggestive.

## 7. DurationEstimate

**DurationEstimate** is an advisory, uncertainty-aware artifact. It may
eventually express concepts such as:

- estimate scope;
- horizon bucket or range;
- lower and upper bounds;
- confidence/uncertainty;
- evidence basis and observed Reality references;
- estimator version;
- applicable Executor capability/profile;
- sample support;
- creation time.

Cold-start output should prefer honest ranges such as `3–10 min`, `10–30 min`,
or `30–60 min` over false precision such as `8.37 min`.

A DurationEstimate is never:

- a timeout;
- a Completion Contract;
- a guaranteed SLA;
- an Authority boundary;
- Production Truth.

### 7.1 Intrinsic and execution-specific estimates

The architecture preserves a future distinction between:

- **Intrinsic Workload Estimate:** relative workload of the governed mission,
  independent of a particular execution resource where possible;
- **Execution Duration Estimate:** expected duration under a compatible
  Executor capability, model/tool configuration, environment/resource class,
  and operational condition.

No intrinsic-workload mathematics is defined by DCP-1. Long-term duration is a
distribution conditioned on PWU shape, capability profile, environment, and
operational Reality—not a fixed property of a PWU.

### 7.2 Planning and operational estimates

- **Planning Estimate:** created during production planning/sizing to advise
  early expectation and possible future capacity planning.
- **Operational Estimate:** recalculated near queue, dispatch, or runtime time
  from fresher availability, load, queue, network, Verification-pressure, and
  observed-progress Reality.

Operational recalculation may revise timing and resource expectations without
rewriting the governed production contract.

## 8. SizingAdvisory

**SizingAdvisory** is the conceptual evidence layer between DurationEstimate
and a governed SPG sizing/admission decision. Possible future outcomes include:

- `KEEP_AS_ONE_PWU`;
- `PREFER_DECOMPOSITION`;
- `INSUFFICIENT_EVIDENCE`;
- `OVERSIZE_BUT_COHESIVE`;
- `DECOMPOSITION_REQUIRED_FOR_GOVERNANCE_REASON`.

These names are architectural vocabulary, not implemented enum values.

```text
duration pressure != decomposition authority
```

A duration estimate may contribute evidence, but it cannot invent a governed
Multi-PWU structure. PLAN-1A, successor authority, baseline rebinding, and
Multi-PWU execution remain deferred. Current PLAN-1B `ONE_PWU_FIT` semantics
remain unchanged.

## 9. CapacityPolicy

**CapacityPolicy** is a conceptual source of operational/planning policy, not
an implemented scheduler. It may eventually express:

- preferred execution horizon;
- acceptable oversize tolerance;
- global and resource-class concurrency budgets;
- cost/latency mode;
- queue-pressure policy;
- deadline policy.

Limited planning-time policy signals may eventually advise SPG. Actual queue
admission, capacity grants, fairness, worker-pool control, cancellation, and
dispatch scheduling belong to a future Capacity/Scheduling capability.
CapacityPolicy supplies constraints and preferences; it does not own Runtime
truth or production Authority.

## 10. Rolling Reality-driven Operational Planning

The long-term control-loop direction is:

```text
initial plan
→ observe Reality
→ recalculate operational estimate
→ capacity decision
→ execute
→ observe
→ recalculate
→ trusted completion
```

It may operate at three time scales:

- **Slow loop:** historical Reality, cost, and capability performance calibrate
  policy;
- **Medium loop:** Work/PWU planning advises sizing and resource planning;
- **Fast loop:** queue pressure, load, Executor health, network, and
  Verification availability advise dispatch-time scheduling.

All loops remain subordinate to governed production semantics. They may alter
operational plans, not silently alter Authority or accepted outcomes.

## 11. Cold-start Evolution

The cold-start rule is:

```text
insufficient historical Reality
→ conservative prior plus explicit uncertainty
→ no fake precision

no measurement maturity
→ no autonomous duration-driven decomposition
```

Possible future maturity phases are architectural sequencing, not committed
implementation milestones:

0. measurement semantics only;
1. measurement-first collection;
2. `SHADOW` / `ADVISORY_ONLY` estimation;
3. duration-aware SPG sizing as secondary evidence;
4. durable Production Demand / Queue;
5. bounded Executor Pool / Capacity Admission;
6. historical calibration;
7. later priority, fairness, cost optimization, and autoscaling.

Current historical Dogfood Reality is heterogeneous and too small for honest
statistical estimation. Existing lifecycle timing can support measurement
calibration; it does not justify autonomous duration decisions.

## 12. Safety and Governance Boundaries

Existing Provider timeout, Executor timeout, internal-turn budget, self-refine
budget, and STOP semantics are hard safety/governance limits. They must not be
reused as preferred PWU horizon, target duration, or capacity-slot size.

```text
preferred duration = soft planning signal
safety timeout      = hard execution boundary
```

One PWU remains a bounded production mission. One Attempt remains a continuous
governed execution grant. One Dispatch remains a governed execution
activation. Internal Provider Turns remain Executor HOW/self-refine behavior.
Independent Verification remains the trust boundary.

Capacity optimization must not reduce trust or quality, omit Verification
cost, count self-refine Turns as separate governed work, or allow queue policy
to bypass Candidate Authorization or Runtime Commit.

## 13. Current Architecture Seams

Current seams reserve future integration without authorizing it:

- `ProductionPlanningRequest` contains authoritative planning inputs suitable
  for constructing a TaskShapeSnapshot;
- provider-neutral `ProductionPlanningService` is an advisory validation
  boundary;
- `ProductionPlanProposal` and one-PWU fit classification are the current
  sizing/admission vocabulary;
- Steering production admission forms an exact contract and runs PLAN-1B before
  creating Run/PWU Reality;
- Completion and change contracts continue to own scope and Verification
  obligations;
- Provider Report timestamps and durable lifecycle identities provide a partial
  measurement basis;
- orchestration scheduling and Dispatch admission are observable future
  capacity boundaries, but neither is currently a Capacity Scheduler.

Future design must not turn these seams into a second implementation engine or
pretend process-local progress is durable scheduling Reality.

## 14. Explicit Non-goals

DCP-1 implements none of the following:

- durable queue or Production Demand;
- scheduler, worker pool, capacity lease, token, or semaphore;
- concurrency limit, priority, fairness, cancellation, or autoscaling;
- cost optimizer;
- duration heuristic, statistical model, or ML prediction;
- Executor routing or automatic resource selection;
- dynamic PWU splitting or PLAN-1A Multi-PWU;
- ETA UI;
- migration or telemetry database schema;
- runtime behavior of any kind.

## 15. Architecture Consistency

DCP-1 preserves:

- Watt MVP Core closure;
- SPG's governance responsibility;
- Reality-driven Plan Steering;
- current PLAN-1B `ONE_PWU_FIT` behavior;
- Executor autonomy and bounded multi-Turn Attempt semantics;
- independent Completion and Verification;
- exact Candidate Authorization and Runtime Commit boundaries;
- deferred Multi-PWU governance.

No Architecture STOP condition is present. The known tension is intentional:
operational planning must become dynamic while governed production truth stays
stable. This document resolves the semantic ownership boundary, but leaves
measurement schema, estimator policy, queue ownership, and runtime capacity
admission for separately admitted design/implementation work.

## References

- [MVP Scope Calibration and Phase-2 Hardening Backlog](../roadmap/mvp-scope-calibration.md)
- [Production Intelligence Architecture](production-intelligence-architecture.md)
- [SPG Core Architecture Model](SPG_Core_Architecture_Model.md)
- [Single-PWU Production Planner Intelligence Lite](single-pwu-production-planner-lite.md)
- [Executor Autonomy Envelope / Attempt Granularity MVP Contract](executor-autonomy-envelope-attempt-granularity-mvp-contract.md)
- [Runtime Benchmark Strategy](spg-runtime-verification-benchmarks.md)
- [Reality-driven Plan Steering MVP Behavioral Contract](reality-driven-plan-steering-mvp-contract.md)
- [SPG State Foundation](spg-state-foundation.md)
- [Completion and Trust Semantics](spg-completion-trust.md)
- [Side-effect Governance](spg-side-effect-governance.md)
- [Watt MVP Core Closure](../evidence/mvp-core-closure.md)
