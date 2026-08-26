# SPG Runtime Verification and Benchmark Strategy

- **Record date:** 2026-08-26
- **Status:** Future verification requirements and benchmark candidates — NOT IMPLEMENTED / NOT EXECUTED
- **Architecture:** [Baseline v0.1](system-architecture-baseline-v0.1.md), [State Foundation Closure](spg-state-foundation.md), and [Reconciliation & Recovery Closure](spg-reconciliation-recovery.md)
- **Related evaluation direction:** [Production Benchmarks](production-benchmarks.md)

This document records a future verification strategy derived from frozen Runtime invariants, failure modes, and governance boundaries, together with capability-based provider evaluation and production economics. It adds no test, benchmark, model-routing, adaptive-decomposition, pricing, or billing implementation, and no SPG Lite MVP commitment. It does not start C. Completion & Trust or D. Side-effect Governance.

## 1. Verification Principle and Traceability

> Every frozen Runtime invariant, failure mode, and governance boundary should eventually map to at least one executable verification mechanism.

Possible future mechanisms include:

- Deterministic unit / invariant tests.
- Property / state-machine tests.
- Integration tests.
- Fault-injection tests.
- Scenario benchmarks.
- Human-evaluated semantic benchmarks where deterministic checking is insufficient.

Future verification records should trace each source invariant or boundary to its scenario, observable outcome, and verification mechanism. An unverified invariant must not be reported as passed merely because its architecture is CLOSED. Closure means design agreement; verification status is separate.

The following is a **future coverage map**, not an executable test suite or a claim of coverage:

| Source boundary / principle | Future verification direction |
|---|---|
| A: immutable Baselines, Working / Trusted separation, exact Candidate, Commit authority | Deterministic invariants and property/state-machine tests |
| A: before/after Baseline switch failure boundary | Integration and crash fault-injection tests |
| B principles 1–6: classification, validity, lowest sufficient recovery, valid-work preservation | Scenario / state-machine tests; semantic review for material relevance |
| B principles 7–10: observation loss, Attempt identity, retry safety, fencing | Fault-injection and identity / authority invariants |
| B principles 11–14: impact propagation, revalidation, authorized destination, supersession | Dependency-aware scenarios and authority-boundary tests |
| B principles 15–19: recovery anchor, responsibility, idempotence, orphan facts, recovery completion | Repeated-restart and orphan-artifact scenarios, state-machine properties |
| B principle 20 and distributed governance principles | History-preservation and policy/authority tests across Human and provider inputs |
| Provider consolidation / model decoupling | Equivalent governed production objectives across providers while keeping identical governance rules; focused PWU checks where comparable |

All 20 A invariants, all 20 B principles, and each frozen failure mode remain individual eventual traceability obligations. These grouped examples do not replace that obligation or close detailed C/D design.

## 2. Benchmark Purpose

Runtime benchmarks evaluate whether the **software production system** remains coherent and governed under imperfect, inconsistent, interrupted, stale, or misleading Executor behavior.

The subject is not merely whether a particular model produces good code. Models and Executors are replaceable test participants; the governed production system is the benchmark subject.

Within those governance boundaries, capability-specific evaluations describe each provider's contribution to trusted outcomes. They supplement, not replace, Runtime invariant verification. The system consumes Production Capabilities, not intelligence prestige or a single global model score.

## 3. Future Runtime Benchmark Taxonomy

### A. State Invariant Tests

Future cases include:

- A committed Baseline cannot be mutated.
- Working State cannot silently become Trusted State.
- A fenced Attempt cannot change authoritative PWU state.
- A Candidate must reference its expected source Baseline.
- Acceptance of Candidate revision N does not authorize revision N+1.

These test already recorded invariants without choosing a database representation or implementing a Commit protocol.

### B. Failure-Injection Tests

Future cases include:

- Executor timeout.
- Network loss.
- Runtime crash during execution.
- Runtime crash before Baseline pointer switch.
- Runtime crash after Baseline pointer switch.
- Delayed / zombie Executor result.
- Duplicate execution.
- Partial artifact write.

Observations should distinguish physical execution reality, current execution authority, recorded historical facts, and admitted production state. Observation loss must not be used as proof that an Executor stopped.

### C. Production Scenario Benchmarks

Future cases include:

- A Baseline advances during active execution.
- An unrelated Baseline change preserves valid work.
- A material architecture change makes active work stale.
- Replan carries forward still-valid PWUs.
- Cancellation occurs while an Executor remains active.
- A Candidate becomes stale before Commit.
- Two changes have no Git conflict but are semantically incompatible.

The last scenario is a benchmark candidate, not an implementation commitment for a Semantic Conflict Engine. Semantic assessment may require human evaluation until an appropriate mechanism exists.

### D. Executor Robustness / Autonomy Benchmarks

Compare equivalent governed production objectives across models/providers under comparable contracts, validity bases, outcome requirements, and authority constraints. Focused PWU comparisons remain useful diagnostics, but end-to-end comparisons may involve different PWU granularity and counts. Candidate observations include:

- Contract adherence.
- Task-identity accuracy.
- Expected artifact satisfaction.
- Verification pass rate.
- Retry rate.
- Rework rate.
- Stale-work handling.
- Human intervention rate.
- Latency.
- Model / API cost.
- Total production cost.

Results may later inform Model Routing and Autonomy Policy. No model-specific thresholds, brand-based autonomy levels, or routing implementation are defined here.

Sections 5–7 refine the capability-relative dimensions, comparison unit, production economics, and future feedback relationships. None of these candidate observations freezes a metric formula or weight.

## 4. Real Incident-derived Regression Benchmark Candidate

**Status:** Real incident-derived candidate, based on the user-reported Codex execution incident; not a test reproduced or executed in this documentation task.

| Dimension | Reported incident |
|---|---|
| Authorized PWU | Record SPG Runtime Findings documentation |
| Actual Executor behavior | Read repository documents only |
| Actual repository mutation | None |
| Executor report | Task completed successfully |
| Reported task identity | Unrelated prior YiJue terminology task summary |

Expected future governed-system behavior:

| Boundary | Expected response |
|---|---|
| Execution Attempt result | Record the reported result and observed execution facts |
| Task identity | Detect mismatch with the authorized PWU |
| Expected artifact delta | Detect missing documentation changes |
| PWU Produced transition | REJECTED |
| Trusted Baseline | Unchanged |
| Follow-up | Recovery / re-execution required through the governed path |

**Executor self-reported completion cannot establish PWU completion.** A successful message is not a substitute for task identity, required output, or an admitted state transition.

This expected rejection preserves the already-recorded partial-output and production-identity boundary. It does not define the full Completion Contract, Artifact Manifest, PWU completion algorithm, or C. Completion & Trust design.

Codex is named only to preserve incident provenance. The same scenario and expected boundary should apply to any Executor/provider that exhibits equivalent behavior; it is not a model-brand qualification verdict.

## 5. Model-Decoupling Benchmark Principle

> Model decoupling must be validated through system-level benchmark consistency, not merely through compatible APIs.

A model/provider may be considered production-compatible only if the governed production system can safely absorb its behavioral variance. Compatibility does not imply identical capability, reliability, latency, or cost across models.

Future benchmark results may influence:

- Allowable PWU types.
- Maximum autonomous execution depth.
- Verification requirements.
- Human attention requirements.
- Retry / rework policy.
- Cost/performance routing.

Autonomy must not be statically encoded by model brand or price. Stronger models may earn wider policy-bounded autonomy without acquiring unrestricted authority to self-accept or Commit production reality.

The same physical provider may supply planning, implementation, analysis, and review while retaining separate logical contracts, responsibilities, and authority checks. Benchmark comparisons must preserve those rules rather than bypass them for a preferred provider.

### 5.1 Capability Performance Profile

**Future concept — NOT IMPLEMENTED:** A Capability Performance Profile is a benchmark- and production-history-backed description of how a specific model/provider performs when supplying a specific Production Capability.

The profile concerns **Provider × Capability**, interpreted against Task / PWU characteristics, Context, and applicable governance policy. One provider may have materially different profiles for Production Planning, Backend Implementation, Documentation, Architecture Analysis, and Verification. Neither a global intelligence score nor provider marketing claims are authoritative evidence of role-specific production performance.

Illustrative observations for a Backend Implementation profile include first-pass success, retry rate, rework rate, verification pass rate, human intervention rate, median execution time, token consumption, Trusted Production Cost, safe PWU granularity, and safe autonomy range. These are possible profile contents, not a frozen schema or scoring scale.

Profiles should be grounded in controlled benchmarks, production telemetry, and governed historical evidence. Observations and future estimates should remain distinguishable, with the evaluated task conditions and evidence limitations visible; unsupported estimates must not appear as demonstrated capability.

### 5.2 Production-Relevant Performance Dimensions

The following are **future evaluation dimensions**, not selected metrics, weights, thresholds, or model rankings:

| Dimension | Candidate observations |
|---|---|
| Execution Efficiency | Time to complete governed PWUs, execution latency, throughput |
| Token / Model Cost | Tokens consumed, API / provider execution cost |
| First-Pass Success | First-attempt completion rate, expected-output satisfaction rate |
| Rework / Retry Burden | Retry and rework frequency, average attempts per satisfied PWU |
| Task Decomposition Requirement | Safe PWU granularity supported, degree of subdivision required, PWUs per equivalent production objective |
| Planning / Design Quality | Decomposition quality, dependency correctness, assumption accuracy, architecture consistency, downstream replanning caused by poor planning |
| Contract Adherence | Task identity accuracy, scope adherence, required artifact satisfaction, instruction compliance |
| Verification Burden | Verification failure rate, additional checks required, Guardian / assurance workload |
| Human Attention Requirement | Intervention, clarification, escalation frequency, manual review requirement |
| Recovery Burden | Interruptions, stale work, recovery incidents, production divergence introduced |
| Safe Autonomy | Safe autonomous execution depth and amount of policy-bounded work without Human Authority intervention |

Completion-related observations use the applicable governed obligations; they do not define new PWU completion semantics or treat Executor self-report as satisfaction. Detailed C. Completion & Trust design remains unstarted.

### 5.3 Equivalent Governed Production Objectives

**Confirmed evaluation principle; future benchmark execution:** Compare providers on equivalent governed production objectives and accepted outcomes, not only isolated prompts, identical token budgets, or single-call quality.

For the objective “produce Trusted Change X,” one provider may require many small PWUs, repeated attempts, and more Human interventions; another may require fewer, larger PWUs with less rework. Both must meet comparable outcome, Context, risk, Contract, verification, and authority requirements. Differences in orchestration and support burden belong in the comparison rather than being excluded by requiring identical PWU counts.

The comparison unit is the end-to-end governed production outcome. Record the conditions and supporting effort so that a provider does not appear more efficient because it received unaccounted human work or weaker trust requirements. The example is qualitative, not a benchmark result or ranking of any provider.

### 5.4 Capability Performance and Governed Autonomy

**Confirmed governance principle; future evidence-backed allocation:** Stronger demonstrated production performance may justify a wider Autonomy Envelope, but only through evidence and applicable policy, never a static assignment by model price, brand, or marketing tier.

The same provider may demonstrate high reliability in Documentation, supporting larger PWUs, lower additional verification burden, and wider autonomous execution. Lower demonstrated reliability in Architecture Change may require smaller PWUs, stronger verification, and more Human Authority Points. These are conditional examples, not assigned levels or thresholds.

Routing and Autonomy Policy should eventually operate on **Capability × Task / PWU characteristics**. Wider autonomy cannot remove mandatory safety, assurance, acceptance, or Commit gates, transfer Guardian authority, or allow a provider to authorize its own production reality. Reducing avoidable verification work is not permission to bypass required evidence.

## 6. Future Production Economics Measurement

**Trusted Production Cost** is the total cost required to produce an accepted **Trusted Production Change**, rather than the model API cost of one request. It refines the existing [Cost per Trusted Change](SPG_Core_Architecture_Model.md#cost-per-trusted-change) concept; it does not introduce a new production-state object or acceptance mechanism.

```text
Trusted Production Cost
  = Model / Executor Cost
  + Planning / Decomposition Cost
  + Verification / Assurance Cost
  + Retry Cost
  + Rework Cost
  + Human Attention Cost
  + Recovery Cost
  + Delay Cost
  + Failure Propagation Cost
```

This is a conceptual cost decomposition, not a frozen accounting formula. Future measurement must account consistently for shared or overlapping effort, including governance coordination, without double-counting the same work. No monetary conversion, rate, or weighting is selected.

| Qualitative comparison only | Provider A | Provider B |
|---|---|---|
| Model / API cost | Lower | Higher |
| Retries and rework | Higher | Lower |
| Human attention and verification burden | Higher | Lower |
| Total Trusted Production Cost | May be higher | Potentially lower despite higher model cost |

These are illustrative behavior profiles, not measurements or an inherent ordering of providers. **The cheapest model call is not necessarily the cheapest production capability.** Higher price does not itself prove higher capability or lower total cost.

### 6.1 Autonomy as an Economic Output

A stronger or more expensive provider may create value through safe autonomy as well as artifact quality: fewer Human interventions and clarification cycles, fewer retries, less rework, fewer verification rounds, larger safe PWUs, and longer autonomous production runs. Model cost should therefore be evaluated with autonomy value and Human Attention Cost, not independently of them.

These possible benefits require capability-specific evidence and policy permission. They are not promises that a higher-priced provider always saves money or can waive governance gates.

### 6.2 Trusted Change Efficiency

**Candidate future metric family:** Trusted Change Efficiency evaluates the resources and coordination needed for an equivalent accepted Trusted Production Change. Candidate dimensions are:

- Trusted Change Lead Time.
- Trusted Change Total Cost.
- PWUs per Trusted Change.
- Execution Attempts per Trusted Change.
- Human Interventions per Trusted Change.
- Verification Cycles per Trusted Change.
- Replans per Trusted Change.
- Token Cost per Trusted Change.
- Autonomous Production Ratio.

No formulas, denominators, aggregation rules, scoring weights, or thresholds are frozen. The conceptual cost breakdown above identifies burdens to study; it is not an implemented metric. Neither autonomy depth nor fewer PWUs alone establishes better production performance without a trusted outcome.

## 7. Future Benchmark Feedback and Transparent Selection

The intended evidence relationship is:

```text
Controlled benchmarks + Production telemetry + Governed historical evidence
        ↓
Capability Performance Profile
        ↓
Production Planner decomposition
        ↓
Model / Capability Routing
        ↓
Autonomy Policy
        ↓
Verification Policy
        ↓
Production Strategy
        ↓
User-facing cost / autonomy / speed trade-off
```

This is a future decision-support relationship, not an execution pipeline or a transfer of policy authority. Existing risk, authority, and verification constraints also bound upstream planning and routing. Evidence may inform policy decisions; it cannot override policy or award authority by itself.

The [future Benchmark-Backed Model / Production Strategy Selection](future-capabilities.md#benchmark-backed-model--production-strategy-selection) uses these profiles to explain expected model cost, total trusted cost, completion time, PWU granularity, observed first-pass success, retry / rework burden, Human intervention, verification burden, and estimated safe autonomy.

Future price differences should correspond to observable production value, not opaque branding or unsupported “Cheap / Balanced / Best” labels. Benchmark evidence may support price explanations and user choice; it does not define a price-setting algorithm, billing implementation, subscription plan, or guarantee of future outcomes.

Consistent with **Replaceable Intelligence, Durable Governance**, capability differences affect performance, granularity, safe autonomy, cost, verification burden, and Human attention, not Production Contracts, State semantics, Authority, Guardian's trust model, or governance invariants. Provider consolidation does not collapse those boundaries.

## 8. Status and Scope Guard

Confirmed principles include capability-oriented evaluation, equivalent-outcome comparison, evidence- and policy-bounded autonomy, trusted production economics, and transparent value-based selection/pricing. They preserve the linked A/B invariants and governance boundaries; they are design principles, not claims of measured provider performance or implemented capabilities.

Capability Performance Profiles, adaptive decomposition, routing, policy feedback, strategy selection, and a capability marketplace remain **Future Capabilities / Architecture Directions**. Performance dimensions and Trusted Change Efficiency remain **candidate metrics**. All verification requirements and benchmark cases, including the incident-derived candidate, remain future work. Test fixtures, executable assertions, fault injectors, model thresholds, infrastructure mechanisms, and scoring implementation remain unselected and unimplemented. No actual prices, commercial tiers, or vendor rankings are defined.

Architecture Baseline remains **v0.1** and SPG Lite MVP scope is unchanged. A is CLOSED; A1/A2 are CLOSED; A3 PASSED. B is CLOSED; B1/B2/B3 are CLOSED; B4 PASSED. C is NEXT, NOT STARTED; D is NOT STARTED. The exact next valid design step is **Runtime Architecture Refinement → C. Completion & Trust**. This architecture / product-strategy side refinement neither reopens B nor begins C or D.
