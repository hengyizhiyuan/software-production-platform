# Future Capabilities

## Decision Capability Evolution

The provider-independent Decision Capability Contract is a current architecture principle. Provider implementations and integrations described here are Future Capabilities and are not implemented in the MVP.

```text
Software Production Platform
        ↓
Decision Capability Contract
        ├── Minimal Decision Capability Provider
        ├── YiJue Decision Engine
        ├── Enterprise Internal Decision Engine
        └── Third-party Decision Provider
```

YiJue may become an advanced Decision Intelligence Provider. It is not an internal module of the Software Production Platform.

### Decision Capability Boundary

Decision Capability answers **What should we do?** It may accept a Decision Request containing Question, Context, Constraints, Options, Required Outcome, and Risk Level. It may return a Decision Artifact containing Recommendation, Reasoning Summary, Alternatives, Risks, Assumptions, Confidence, and Human Review Requirement.

The contract records the capability boundary now; no concrete API, adapter, or provider implementation is defined.

## Capability Relationship

Future AI-native organizational capabilities may remain layered and independently owned:

```text
Decision Intelligence Capability
        ↓
Provider implementations, including YiJue Product

Production Intelligence
        ↓
Software Production Platform

Assurance Intelligence
        ↓
Guardian

Context Intelligence
        ↓
ECF
```

These systems collaborate while preserving Ownership Separation, Source of Truth Separation, and Lifecycle Independence.

## Production Planner Boundary

Production Planner is responsible for:

- Project Intelligence
- Production Intelligence
- Iteration Management
- Task Orchestration

It is not responsible for enterprise strategic decisions, product direction selection, major value judgments, or replacing Decision Intelligence Capability. A future major Decision Point may invoke a Decision Intelligence Provider, including YiJue, through the Decision Capability Contract.

## Design Intelligence Capability Evolution

This is a long-term architecture vision, not an MVP requirement. Production Planner is a **Production Planning Capability**, independent of any one Agent implementation.

A Role may have different implementations while its Role Contract remains stable:

```text
Role: Production Planning

MVP:      Single AI Model
Future:   Multi-role Decision System
Advanced: Human + AI Decision Council
```

### Decision Intelligence Integration Vision

YiJue (Consumer Product / Application) may provide a future Decision Intelligence Provider implementation that Production Planner may invoke through a capability contract. YiJue does not replace Production Planner or implement Production Planning Capability.

```text
Production Planning Capability
        └── Production Planner
                └── may invoke Decision Intelligence Capability (Future)
                        └── Provider implementations, including YiJue Product
```

### Decision Intelligence Interface

The platform defines a provider-independent Decision Intelligence Interface at the architecture level. A concrete API and provider integration remain future implementation work.

Contract input:

- Human Intent
- Background
- Constraints
- Expected Outcome

Contract output:

- Decision Artifact Candidate

SPG consumes the Decision Artifact Contract, not provider internals. This architectural contract does not assert that the MVP implements an interface API.

### Intelligence Pattern Selection

Future AI-native organizations may select an intelligence organization pattern according to problem complexity:

```text
Problem Complexity
        ↓
Select Intelligence Pattern
        ↓
Single AI
or
Multi-role AI
or
Human-AI Council
```

The future does not depend on a single super Agent.

### System Relationship

YiJue and the Software Production Platform are complementary systems, not competitors:

```text
YiJue
How to think better
        ↓
Software Production Platform
How to build better
        ↓
Guardian
How to trust better
```

A broader production relationship is:

```text
Decision Intelligence
        ↓
Intent Formation
        ↓
Production Planning
        ↓
Execution
        ↓
Verification
        ↓
Assurance
        ↓
Continuous Evolution
```


## Engineering Portfolio Intelligence

Engineering Portfolio Intelligence is a future enterprise capability direction, not an MVP requirement. It may provide CTOs, technical leaders, and enterprise administrators with a unified view across multiple projects, including:

- Overall project state
- Risk
- AI execution status
- Resource usage
- Assurance status
- Production health

This direction is recorded without defining implementation details.


## Software Evolution Governance

AI Coding Executors can significantly increase software production speed, but rapid change can cause Feature Drift, Architecture Drift, Design Intent Loss, and Hidden Dependency Conflict.

Software Evolution Governance is a long-term capability direction for keeping design consistency, architecture boundaries, Feature completeness, and historical decision constraints effective during continuous change.

## Engineering Change Intelligence (Tentative)

Engineering Change Intelligence is a long-term capability direction, not an MVP requirement. It may support:

### Feature Awareness

Understanding current system capabilities, Feature state, and Feature boundaries.

### Change Impact Analysis

Analyzing which Features, modules, architecture boundaries, and historical decisions may be affected by a change.

### Architecture Drift Detection

Detecting whether current implementation has diverged from the design baseline or violated approved architecture constraints.

### Evolution History

Recording why a design was chosen, which alternatives were rejected, and which constraints must not be broken.


## Engineering Branching

Engineering Branching is a long-term direction, not an MVP feature. Traditional Git manages code branching; AI-native production may require broader branching across design, decisions, tasks, context, code, verification, and evidence.

```text
Baseline
  ├── Branch A
  └── Branch B
```

The intended evolution is Stage 1: Snapshot + Restore; Stage 2: Branch Creation; Stage 3: AI-assisted Merge.

## Intelligent Executor Routing

The platform may eventually select suitable executors based on Capability × Task / PWU characteristics, risk, authority, observed reliability, total trusted cost, latency, and quality requirements. This is capability-based executor routing, not only model routing.

Future selection should use [Capability Performance Profiles](spg-runtime-verification-benchmarks.md#51-capability-performance-profile), not one global intelligence score or fixed model-name hierarchy. The same provider may be well suited to Documentation but need narrower PWUs and stronger verification for Architecture Change. Strong demonstrated capability may support larger PWUs and wider policy-bounded autonomy; provider price or brand does not establish either.

Routing must remain compatible with general-purpose frontier models, smaller specialized models, enterprise private models, customer-provided models, future local models, and specialized capability providers. The globally strongest model is not necessarily the economically optimal provider for every Production Capability. No provider is hard-coded as superior, and no automatic routing is implemented in the MVP.

## Runtime Profile and Provider Management Evolution

The [Runtime Profile architecture](runtime-profile-provider-deployment.md) reserves future Provider Registry, Capability Descriptor, profile validation, enterprise-private bindings, provider/model compatibility adapters, provider-management control surface, and provider-placement/data-residency policy.

These are Future Capabilities, not first-FVS requirements. Capability Descriptor records technical support, while Capability Performance Profile records observed governed production performance; the two must not be merged. The future control surface configures persisted bindings and does not become an independent Source of Truth for SPG domain semantics.

Global, Mainland, and enterprise-private deployments remain profiles of one product architecture and one primary codebase. Distributed cross-region execution, automatic discovery/routing, Provider Marketplace, residency Policy Engine, and Kubernetes are not implemented in the MVP.

## AI Software Production Benchmark

AI Software Production Benchmark is a long-term capability direction. This document does not define its implementation details.

Its purpose is to measure how different AI models and executors perform inside the software production system, evaluating the complete production outcome rather than model capability alone.

### Executor Capability Benchmark

Future evaluation compares providers for specific Production Capabilities, including Planning, Architecture Analysis, Implementation, Documentation, Verification, Context Preparation, Reconciliation, Migration Planning, and Test Generation. A model is not a Capability; one provider may supply several with different observed performance.

The [Runtime Benchmark Strategy](spg-runtime-verification-benchmarks.md) is the detailed evaluation reference for Capability Performance Profiles, candidate performance dimensions, equivalent governed production objectives, Trusted Production Cost, and the Trusted Change Efficiency metric family. Evidence comes from controlled benchmarks, production telemetry, and governed history, not provider marketing claims. No scoring scale, weights, concrete rankings, or benchmark implementation are defined.

### Workflow Benchmark

The benchmark may evaluate the impact of the AI-native production workflow by comparing:

```text
Traditional: User → Prompt → Model → Output

Platform: Intent → Context → Role → Task → Executor → Verification → Assurance → Accepted Artifact
```

Potential dimensions include lead time, rework rate, human intervention, defect rate, and trusted delivery throughput.

### Model Evolution Benchmark

The benchmark may measure whether improvements in AI models translate into measurable software production improvements, including:

- Task completion speed
- Quality improvement
- Cost reduction
- Change in assurance confidence

### Platform Stability Benchmark

The benchmark may verify that model replacement does not destroy engineering consistency, including:

- Context understanding consistency
- Decision consistency
- Artifact consistency
- Governance compliance

### Assurance Benchmark

The platform may integrate with Guardian to measure assurance effectiveness, finding quality, trusted change throughput, and assurance cost efficiency.

This records the integration direction only and does not design Guardian internals.

## Benchmark-Backed Model / Production Strategy Selection

**Future Product Capability / Architecture Direction — NOT IMPLEMENTED; not part of the SPG Lite MVP.** Users may eventually compare models or select a Production Strategy through transparent, evidence-backed production characteristics.

The system consumes capabilities, not intelligence prestige. A useful selection answers: for this production objective, which capability configuration gives the best combination of trusted outcome, speed, safe autonomy, and total cost?

Potential user-facing information includes:

- Expected model / provider execution cost.
- Expected Trusted Production Cost per accepted Trusted Production Change.
- Expected completion time and PWU granularity.
- Observed first-pass success.
- Expected retry and rework burden.
- Expected Human intervention frequency.
- Expected Verification burden.
- Estimated safe autonomy level under the applicable policy.

Unexplained labels such as “Cheap,” “Balanced,” or “Best” are insufficient. Future displays should distinguish observed evidence from estimates, expose relevant benchmark / production conditions and limitations, and avoid implying guaranteed outcomes. Comparisons use equivalent governed production objectives; they do not assume identical token budgets, PWU counts, or orchestration effort.

### Price Should Correspond to Observable Production Value

**Confirmed transparency principle for future pricing:** Differences in model, strategy, or autonomy pricing should be explainable through benchmark- and production-backed value. A higher model execution cost might be accompanied by less observed Human intervention, less rework, shorter trusted change lead time, or larger safe PWUs. Those benefits need evidence; they cannot be inferred from price or branding alone.

**No Model Prestige Pricing:** The platform purchases a Production Capability contribution, not a model's full abstract intelligence identity. Generic model ranking or prestige alone cannot justify user-facing production price. Model/API cost and total Trusted Production Cost must remain distinguishable, including Human Attention Cost and autonomy value.

This records a product principle, not a price-setting algorithm or a commitment to charge differently. No real percentages, prices, billing rules, subscription tiers, or plans are defined.

### Production Strategy Rather Than Raw Model Selection

A user may eventually select a production-economic strategy while the system internally routes different Capability Providers. The following are **illustrative configurations only**, not offered products, subscription tiers, guaranteed behaviors, or predefined provider assignments:

| Conceptual strategy | Illustrative trade-off |
|---|---|
| Economy | Lower model/API cost; smaller PWUs, stricter verification, and more Human attention may be needed |
| Balanced | Optimize total production economics across model cost, planning, verification, rework, Human attention, and other trusted-production costs |
| High Autonomy | Stronger demonstrated capability providers may support larger PWUs, fewer Human interventions, and deeper safe autonomous runs despite higher model cost |

Every configuration retains required governance, assurance, and acceptance gates. Additional verification burden may differ; mandatory trust requirements do not become purchasable exceptions. The same provider may receive different autonomy envelopes for different Capabilities.

The [future benchmark feedback relationship](spg-runtime-verification-benchmarks.md#7-future-benchmark-feedback-and-transparent-selection) connects Capability Performance Profiles to Planner decomposition, Model / Capability Routing, Autonomy Policy, Verification Policy, Production Strategy, and user-facing cost / autonomy / speed choices. It informs decisions within existing authority boundaries; it neither implements policy feedback nor allows benchmark results to grant authority by themselves.

### Future Capability Marketplace / Strategy Selector

A benchmark-backed production capability marketplace or strategy selector could make provider choice transparent and economically meaningful. Provider flexibility includes frontier, specialized, enterprise-private, customer-provided, local, and other capability providers; the best global model is not assumed to be the best provider for every role.

This is a Future Capability, not a current product commitment or MVP feature. **Replaceable Intelligence, Durable Governance** remains intact: provider differences may change performance, granularity, cost, safe autonomy, verification burden, and Human attention, but not Production Contracts, State semantics, Authority, Guardian's trust model, or governance invariants.

## Scope Boundary

These benchmark directions are not current MVP requirements. They should be developed only after sufficient production experience has established the relevant evidence and evaluation needs.

Capability profiles, adaptive decomposition, routing, benchmark-backed strategy selection, and the marketplace remain future directions. This introduces no implementation, pricing plan, MVP expansion, or Baseline increment. Baseline remains v0.1. The [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md) is CLOSED with Coding Readiness PASS, but these deferred capabilities are not promoted and no implementation slice is authorized here.






## Software Production Pattern Library

This is a Future Capability and Architecture Direction, Not Implemented in the MVP.

A Software Production Pattern Library is analogous to a manufacturing process-route library. It does not primarily store code. It may preserve:

- Production objectives
- Production flows
- Task decomposition approaches
- Capability combinations
- Verification approaches
- Risk patterns
- Improvement history

This is a Production Intelligence Asset. YiJue may preserve Decision Intelligence Assets describing how to make better decisions; the platform may preserve Production Intelligence Assets describing how to produce software reliably.

## Production Workflow Philosophy

The future workflow uses a Hybrid Model:

```text
Production Policy + Production Pattern + AI Adaptive Planning
```

- **Policy** defines rules that cannot be violated, such as a Security Gate.
- **Pattern** preserves a verified production route, such as a Feature Development Pattern.
- **AI Adaptive Planning** adjusts the route based on Project Context, Risk, and Current State.

This is a Future Capability and Architecture Direction, Not Implemented in the MVP.

## Engineering Conflict Evolution

AI-native conflict is broader than a Git Merge Conflict. Future conflict understanding may include:

```text
Conflict
├── Text Conflict
├── Code Conflict
├── Contract Conflict
├── Architecture Conflict
├── Behavior Conflict
└── Intent Conflict
```

The long-term concern is semantic engineering consistency, not only textual mergeability. This is a Future Capability and Architecture Direction, Not Implemented in the MVP.

## Engineering Branching

Engineering Branching is a Future Capability and Architecture Direction, Not Implemented in the MVP. A branch may represent an independent engineering state space containing:

- Intent
- Context
- Decision
- Design
- Task
- Code
- Evidence

Its purpose is to support alternative exploration, parallel production, and controlled integration. Project State should not be conceptually bound to one chat window or one execution environment.


