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

**Current collaboration amendment — Human-approved, 2026-10-11:** Watt
development is conducted by the Human Governor and the AI collaborator. A
separate Architecture Lead actor or approval step is no longer required.
The AI collaborator retains architecture-boundary review, Repository Reality
analysis and implementation responsibilities; material authority, scope and
acceptance decisions remain Human-owned. Earlier role descriptions below
record the previous collaboration model. They do not create a current waiting
gate. Guardian and independent qualification reviewers retain their product
and evidence independence. Section 13 is the canonical current rule for
probabilistic model behavior and development prioritization.

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

## 13. AI Non-Determinism Principle and Execution Discipline

### 13.1 Authority and objective

This Watt development rule applies the Program's Accepted
[ADR-0002 at version 1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1](https://github.com/hengyizhiyuan/software-production-system/blob/1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1/docs/04-decisions/ADR-0002-STOCHASTIC-NATIVE-ENGINEERING.md).
The Program owns the architecture invariant; this section defines Watt's
execution responsibilities without replacing the ADR or any Owner contract.

Watt MUST assume that LLM output is probabilistic, first-pass correctness is
not guaranteed and bounded candidate failure is expected. Its objective is to
reliably absorb uncertainty and converge toward acceptable production results.
Eliminating every possible model error is not a prerequisite for production.

Reuse determinism for identity, provenance, version, contract, authority,
effect permits, evidence integrity and admission gates. Use intelligence for
open semantic interpretation and candidate methods. Lawful equivalent outputs
need not share wording, reasoning, task order or implementation. Necessary
content, constraints, evidence and permissions remain strict.

Generation yields a Candidate. Existing Owner validation, bounded convergence
and governed admission decide whether it can advance. This principle creates
no new runtime role, coordinator, retry budget or authority.

### 13.2 Runtime recovery versus system evolution

| Failure class | Evidence needed | Default response |
| --- | --- | --- |
| A — Runtime Model Variance | The required meaning is expressible under the existing contract, inputs and authority are intact, and the candidate differs, omits a required component or violates a repairable output contract. | Existing Owner-specific Self-Refine, repair, regeneration or permitted retry on the same exact basis and remaining budget. Optional information cannot become a new mandatory gate. |
| B — System Capability Defect | A lawful requirement cannot be represented, a consumer rejects a demonstrably lawful binding, actual evidence cannot reach its Owner, or recovery loses identity, budget or effect continuity. | A minimal common-root engineering correction in the existing Owner, followed by affected regression and production qualification. A model failure alone is not this proof. |
| C — Governance Blocker | Authority is absent, a required source/version/evidence is invalid or unavailable, or engineering reality/effect integrity is compromised. | Block the corresponding admission or acceptance. Recover authentic evidence or await its lawful Owner; do not regenerate authority or turn UNKNOWN into PASS. |

A single observation may cross boundaries. For example, a wrong Review verdict
is candidate variance if the existing validation and feedback can reject and
repair it; accepting that verdict despite demonstrably invalid evidence is a
system or governance defect. Classify the actual failed predicate and the
current authoritative state, rather than the visible error label.

Before changing platform code, establish whether a lawful result is
expressible and the existing bounded recovery received actionable feedback.
Correct a shared loss of feedback or consumer capability when proven; do not
encode the answer to one example. Candidate rejection does not itself mean
that admitted Engineering Truth has been corrupted.

Retry and regeneration remain subject to existing transport-result certainty,
attempt and cumulative budgets. They cannot repeat uncertain effects, erase
prior attempts, create authority, rewrite facts or weaken Guardian. A failed
bounded trial remains failed; it does not prohibit subsequent engineering
repair justified by new evidence.

### 13.3 Error prioritization

| Priority | Meaning | Execution rule |
| --- | --- | --- |
| P0 | The admitted production journey cannot progress safely to its required boundary. | First determine the exact blocker and restore the lawful production loop. |
| P1 | A proven reusable representation, evidence, Owner or recovery capability is missing. | Fix the smallest common seam needed by the journey, without a parallel system. |
| P2 | Reliability, cost, breadth or quality improvement beyond the required qualified behavior. | Record and schedule after blocking capability is restored, unless it is an existing acceptance obligation. |
| P3 | Cosmetic wording, local diagnostic presentation or optional metadata. | Defer during critical capability work unless it prevents correct diagnosis or recovery. |

Priority does not authorize unsafe promotion. A required evidence or authority
gate remains blocking regardless of development priority. Do not require
theoretical completeness or a perfect first candidate before attempting the
authorized representative production journey.

### 13.4 Proportionate regression

* Local change: validate the changed invariant and its immediate failure paths.
* Grouped changes: run focused contract and persistence regression across the
  affected Owners and recovery boundaries.
* Architecture or responsibility change: run the broader applicable regression
  and representative real production qualification.
* Stable delivery revision: perform its required exact-source/image gates once;
  repeat an affected gate only for an identified regression or new source input.
* Documentation-only changes do not invalidate a frozen runtime image. Record
  the application revision separately from a later evidence/document commit.

Use the [existing regression governance](watt-regression-protection-and-golden-journey-governance.md)
to protect common invariants at the lowest-cost reliable layer. Test count,
diagnostic detail and repeated historical replays are not production outcomes.
Do not run a large suite after every minor adjustment or require another live
historical diagnostic when current qualification can test the same boundary.

### 13.5 Production closure and mission review

The development target is the governed loop:

```text
Intent → Context → Contract → Candidate → Verification → Acceptance
```

Each stage uses actual source, evidence and its lawful Owner. Verification and
Guardian remain independent of the generating model. Human Acceptance remains
a real Human decision; a mission may stop at a specified Candidate/Assurance
boundary with later Human gates pending. Neither fixtures nor document changes
complete that loop.

Every material model-capability task must identify permitted variance,
immutable engineering/authority boundaries, the existing validation and
bounded-recovery Owner, its termination conditions, static-special-case risk,
and the representative real and negative qualification needed. Do not expand
the mission merely to eliminate remaining possible model errors.
