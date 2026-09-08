# AI-native Development Execution Principles

## 1. Status and purpose

```text
Document type
    ARCHITECTURAL / DEVELOPMENT PRINCIPLE

Purpose
    Define Human Governor, Architecture Lead AI, and AI Executor
    responsibility and collaboration boundaries

Implementation authority
    NONE
```

This document defines how substantial Watt capabilities should be developed
with AI. It is a development-governance principle, not a new Watt Runtime
module, domain role, lifecycle, schema, or feature contract.

The terms `Architecture Lead AI` and `AI Executor` describe responsibilities in
the development collaboration. `Architecture Lead AI` does not revive the
retired `Design Lead AI` product-component name and does not imply final Human
Authority. Implementations remain replaceable.

## 2. Autonomous execution within governed boundaries

Watt does not seek safety by removing useful AI autonomy. It seeks to make
complex autonomous execution safe enough to govern by defining an explicit
production and development envelope.

> Human defines WHY, WHAT, and the material boundaries. The AI Executor
> determines HOW inside the admitted envelope.

The governing rule is:

```text
Autonomy
    bounded by Intent, Authority, Scope, Constraints,
    Completion Conditions, Verification, and STOP conditions
```

Bounded does not mean that the Human prescribes every command, edit, test, or
repair. The Executor may inspect Reality, elaborate an implementation approach,
edit, test, diagnose, and self-correct while the mission and authority envelope
remain valid.

Autonomy also does not create Authority. Technical capability, tool access, or
an Executor convention cannot authorize a branch, commit, push, repository
integration, Runtime transition, external side effect, scope expansion, or
product decision that the admitted envelope does not permit.

See the [Executor Autonomy Envelope Contract](executor-autonomy-envelope-attempt-granularity-mvp-contract.md)
and [Executor Authority Drift Dogfood Evidence](../evidence/dogfood/executor-authority-drift-branch-creation.md).

## 3. Responsibility model

### 3.1 Human Governor

The Human Governor is responsible for:

- Product Intent and Motive;
- Product North Star;
- material value and architecture trade-offs;
- risk tolerance and risk acceptance;
- Authority boundaries and material changes to them;
- final product acceptance and accountability.

The Human Governor is not expected to perform routine technical scheduling or
specify every implementation detail. Human Agency First means meaningful
control at Authority and judgment boundaries, not Human-in-the-loop for every
Executor move.

### 3.2 Architecture Lead AI

The Architecture Lead AI is responsible for:

- reconstructing and preserving the long-term objective;
- identifying the capability being built rather than optimizing only the local
  task;
- defining and checking architecture, ownership, and Authority boundaries;
- shaping a bounded Mission Contract;
- reviewing repository and Runtime Reality against the intended outcome;
- detecting when local engineering success diverges from the Product North
  Star;
- returning unresolved product, architecture, risk, or Authority judgments to
  the Human Governor.

It does not own Product Intent, risk acceptance, or final accountability. It
does not replace Plan Steering or SPG inside the Watt product architecture. It
also should not prescribe every low-level implementation operation to the
Executor when the Mission Contract already provides a sufficient envelope.

### 3.3 AI Executor

Inside an admitted Mission Contract, the AI Executor is responsible for:

- inspecting Repository Reality before action;
- elaborating the technical implementation approach;
- implementing the bounded change;
- running authorized focused validation;
- diagnosing and repairing in-scope failures;
- maintaining relevant documentation;
- producing evidence and a truthful completion report;
- preparing an authorized checkpoint when checkpoint authority is explicit.

The Executor owns `HOW` within the envelope. It does not own the Product North
Star, silently change the mission, relax acceptance conditions, fabricate
evidence, or acquire production/repository Authority merely because it can
perform an operation.

An Executor-prepared checkpoint is not automatically a Trusted Baseline, active
Runtime, remote push, or accepted product outcome. Those transitions retain
their existing governance and Reality requirements.

## 4. Rejected collaboration extremes

### 4.1 Uncontrolled autonomy

```text
Vague Human goal
    -> unrestricted AI execution
    -> high-quality wrong system
```

This mode fails because Product Intent, capability boundaries, acceptance
scenarios, and Authority are not sufficiently governed. Technical quality
cannot compensate for solving the wrong problem.

### 4.2 Human micro-management

```text
Human prescribes one step
    -> AI executes
    -> Human inspects
    -> Human prescribes the next step
    -> repeat
```

This mode makes the Human a command scheduler, fragments Executor context,
introduces translation loss, spends tokens restating local state, and prevents
the Executor from using continuous repository learning inside a stable mission.

The problem is not small tasks themselves. Small bounded steps are useful when
the mission or Authority genuinely changes. The failure is unnecessary
micro-orchestration inside an otherwise stable envelope.

## 5. Recommended collaboration model

```text
Product / Architecture Alignment
    -> Mission Contract
    -> AI Executor Autonomous Execution
    -> Evidence / Reality Review
    -> Human Acceptance
```

### 5.1 Product and architecture alignment

The Human Governor and Architecture Lead AI establish:

- the Product Intent and North Star relationship;
- the capability boundary;
- known constraints and non-goals;
- Human-owned decisions and risk boundaries;
- a representative acceptance scenario;
- the evidence required to evaluate success.

### 5.2 Mission Contract

A Mission Contract is the bounded development agreement given to the
repo-grounded Executor. At minimum it should make explicit:

- objective and expected outcome;
- repository and current Reality basis;
- included and forbidden scope;
- architecture and Authority boundaries;
- acceptance scenario and pass conditions;
- allowed validation and side effects;
- STOP/escalation conditions;
- checkpoint, commit, push, or external-action authority when applicable.

This is a semantic development contract. It is not a newly authorized Watt
domain object, database table, API, or Runtime lifecycle.

### 5.3 Autonomous implementation

The Executor should receive enough context and authority to complete the stable
mission without a Human or Architecture Lead dictating every technical move.
It should stop when Reality invalidates the contract or a judgment/Authority
boundary is reached, not simply because another local edit or test is needed.

### 5.4 Evidence and Reality review

Architecture Lead review compares the observed repository/runtime result with
the Mission Contract and Product North Star. A passing test suite is evidence,
not proof that the intended product capability exists. Review must check
scope, boundaries, behavior, evidence, and actual Reality.

### 5.5 Human acceptance

Human acceptance determines whether the result satisfies the intended product
outcome and value judgment. Engineering completion and Human Product Acceptance
remain separate facts.

## 6. PWU as governed continuity

A Production Work Unit is not merely a task-decomposition unit. Its deeper
purpose is to preserve useful production continuity while retaining governance
and recoverability.

> Execution continuity without execution monolithicity.

Chinese expression:

> 生产连续，但执行不必连续。

PWU boundaries support:

- **Decomposition** — avoid one unbounded black-box mission;
- **Pause** — preserve production state when execution stops;
- **Recovery** — reconstruct from governed Reality and context;
- **Replacement** — change Executor, model, Provider, or host without making
  hidden session memory authoritative;
- **Verification** — evaluate evidence at meaningful production beats.

The goal is not to maximize the number of PWUs. It is to choose boundaries
where the production mission, Authority envelope, completion obligations, or
Reality materially changes while preserving autonomous continuity inside each
stable envelope.

## 7. PWU, ECF, Executor, Verification, and Guardian

The future system direction is:

```text
Mission
    -> PWU
    -> future ECF Context Assembly
    -> Executor
    -> Verification
    -> Reality Update
    -> next PWU
```

Persisted governed Reality and context reconstruction should allow independent
PWUs to preserve the material continuity of a long execution without requiring
one permanent model session.

Current Watt provides PWU/Attempt boundaries, Context Package Lite,
independent Observation, Completion, and Verification foundations. Full ECF is
future context capability; full Guardian is future Assurance capability.

Guardian should not be modeled as friction that blocks every small Executor
move:

```text
Production throughput
    -> proportionate Assurance Gates
    -> trusted outcome
```

Assurance should concentrate Evidence, Findings, coverage, quality, and
challenge at the boundaries where trust is established. It must remain
independent of Executor self-claims while avoiding unnecessary per-action
approval that destroys useful execution continuity.

This section records architecture direction only. It does not authorize ECF or
Guardian implementation.

## 8. PWU Continuity Benchmark

The future benchmark compares:

```text
Long Continuous Agent Run
    versus
PWU-segmented governed execution
```

Evaluation dimensions include:

- Intent Fidelity;
- Engineering Quality;
- Context Loss;
- pause and Recovery;
- Executor/model/Provider replacement;
- independent Verification and evidence lineage.

The validation goal is to determine whether PWU segmentation can preserve the
material advantages of continuous execution while improving recoverability,
verifiability, and governance. This is an architectural hypothesis, not a
current result.

The authoritative evaluation direction is recorded in the
[PWU Execution Continuity Benchmark](production-benchmarks.md#pwu-execution-continuity-benchmark).

## 9. Lessons learned

### 9.1 Guided Design: structure is not facilitation

The Guided Design work exposed that static process structures alone do not
create Design Leadership behavior. A Design Schema, Agenda, current focus, and
readiness model can organize questions, yet the product must also facilitate
the design journey: expose why a question matters, help clarify incomplete
intent, synthesize prior decisions, challenge gaps, and guide the Human toward
a reviewable production proposal.

The lesson is:

> A system capability must define expected behavior, not only static
> structure.

Current Guided Design Core provides a reconstructable, governed multi-step
process and production-proposal review. Focused validation and real Provider
proof pass, while Human Product Acceptance remains pending. Whether the
complete Design Facilitation experience is sufficient must be decided by that
acceptance evidence; it is not proven by schema or tests alone.

See [Guided Design Core](guided-design-core.md) and its
[Focused Validation Evidence](../evidence/guided-design-core-focused-validation.md).

### 9.2 Runtime activation: architecture assumptions do not replace Reality

The Runtime activation case established:

```text
Reviewed Commit
    != Current Trusted Baseline
    != Active Runtime
```

A reviewed repository checkpoint does not become trusted or active merely
because it exists. Baseline admission must be lawful for the current lineage,
and Runtime activation must independently prove the exact revision, tree,
package/static fingerprints, and clean checkout.

The lesson is:

> AI must obey current engineering Reality; architecture intent cannot be used
> to pretend an unavailable transition already exists.

When the existing Runtime cannot lawfully admit a reviewed checkpoint, the
correct response is to report the boundary or create a separately authorized
isolated Runtime—not to fabricate baseline lineage or manually replace active
state.

See [Trusted Baseline / Active Runtime Convergence](trusted-baseline-active-runtime-convergence-lite.md)
and [Control Room Acceptance Preparation Evidence](../evidence/control-room-slice-4-human-acceptance-preparation.md).

## 10. Future development rule

For substantial capability development, prefer:

```text
Human Governor + Architecture Lead AI
    define Product Intent
    define Capability Boundary
    define Acceptance Scenario
    define Pass Conditions and Authority
        -> Mission Contract
        -> AI Executor autonomous implementation
        -> Evidence / Reality Review
        -> Human Acceptance
```

Do not default to either:

- infinitely decomposed Human-directed micro-tasks; or
- a large, vague, unbounded wish delegated to an autonomous AI.

Choose the largest mission that has a stable, explicit, reviewable envelope.
Split or stop when the objective, Authority, risk, constraints, acceptance
conditions, or relevant Reality materially changes.

## 11. Relationship to Watt product architecture

These development roles do not replace Watt's product capabilities:

| Development collaboration responsibility | Watt product boundary |
| --- | --- |
| Human Governor | Retains Product Intent, Authority, risk, acceptance, accountability |
| Architecture Lead AI | Development-time architecture and Reality review; not a new Runtime component |
| Mission Contract | Development governance artifact; not a new Work/PWU/domain model |
| AI Executor | Implements `HOW` in the admitted development envelope |
| Watt Plan Steering | Owns product Runtime `WHAT NEXT` from governed Reality |
| Watt SPG | Owns governed production execution semantics |

The same principles should shape Watt's future product behavior, but this
document does not directly change WIC, Guided Design, Plan Steering, SPG,
Executor, Verification, Runtime, or Human Authority semantics.

## 12. Current and future boundary

```text
Current architecture principle
    Govern the execution envelope, not every Executor move
    Human-at-Authority-Points, not Human-in-the-loop-everywhere
    Executor capability does not imply Production Authority
    Evidence and Reality review precede acceptance

Current implemented foundations
    bounded multi-turn Executor Attempt
    PWU/Attempt and Context Package Lite
    independent Observation, Completion, Verification, Runtime truth
    Reality-driven Plan Steering and Guided Design Core

Future validation
    PWU Continuity Benchmark
    complete Design Facilitation Human Product Acceptance

Future capabilities
    full ECF
    full Guardian Assurance system
```

No implementation, MVP scope expansion, or new product architecture is
authorized by this record.
