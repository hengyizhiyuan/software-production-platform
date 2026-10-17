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
and evidence independence. Sections 13 and 14 are the canonical current rules
for probabilistic model behavior, module adaptation and development prioritization.

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

### Stochastic-native capability review

This existing Mission Contract review applies to substantial development or
maintenance at a probabilistic intelligence boundary, including a deterministic
consumer that does not call an LLM. Apply the canonical
[module contract](#143-contract-beyond-schema) and
[admission, review, maintenance and qualification checks](#145-default-development-and-maintenance-process).
These extend the fixed
[Program ADR-0002 review requirement](https://github.com/hengyizhiyuan/software-production-system/blob/1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1/docs/06-governance/GOVERNED_AI_ENGINEERING_LOOP.md#stochastic-native-capability-review)
within existing Owner responsibilities. Record applicable answers in the
existing mission/review; ordinary deterministic tasks need not formalize the
entire checklist. This adds no approval actor, template system or runtime gate.

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

Human Governor direction, 2026-10-17: prioritize a usable production journey.
At admission, preserve the complete admitted brief and enforce source, scope
and effect authority. Passing unchanged requirements to an existing artifact
Verification Owner does not require another model to decompose and review their
meaning first. Such a handoff is pending evidence, never semantic approval or
completion. Interpretive transformation still needs its existing Owner's
validation. Check implementation requirements against the actual candidate;
keep continuous effect prohibitions armed from admission and final independent
Verification, Guardian and Human acceptance at their applicable boundaries.
Internal protocol/recovery failures belong to the system, not a request for the
Human to repeat an unchanged goal. The approved continuity work applies this
at ordinary bounded implementation boundaries: exact Human-selected paths and
new reversible implementation surfaces may be frozen with artifact validation
still pending; optional compiler implementation questions remain advisory while
the complete Human clauses remain obligations. A captured managed import with
no existing repository product-policy declarations may use its admitted Work
and exact Source Owner records; absence alone does not manufacture mandatory
product invariants or decisions. Existing repository declarations retain their
policy. A single page and its stylesheet/script are one implementation unit.
Human Governor direction, 2026-10-17 (runnable-preview-first mission): ordinary
bounded multi-file implementations remain one coherent production unit; file
names alone do not establish independently verifiable capabilities. Explicit
independent baseline/dependency requirements and observed execution sizing may
justify decomposition. Assess current content once per exact candidate and
reuse its exact binding evidence across Fact, Work constraint and inventory
projections, including negative results. Existing authoritative repository policy
is checked against the artifact directly; do not invent an additional Work-clause
binding as a prerequisite. Internal verification protocol, evidence or ownership
failures stop at the responsible system Owner without regenerating unrelated
business code. Stop scheduling sibling work when a required branch cannot finish.
The existing Preview Owner may expose a bounded exact observed static snapshot
after cheap source/scope checks and before semantic qualification, for an
admitted implementation or explicitly authorized recovery. Its availability
establishes no Verification PASS, Guardian approval, delivery or Human acceptance.
Future Preview readiness is checked against the actual served exact Candidate,
never treated as current content evidence or permission to accept/deliver it.

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

## 14. AI-Native Module Adaptation and Development Review

### 14.1 Authority, definition and applicability

**Human Governor approved — 2026-10-12; current Watt architecture and development
norm.** This section refines the fixed Program ADR-0002 referenced in §13.1;
it does not replace it or transfer any formal Owner responsibility. Sections
13–14 in this document are the sole Watt project-level normative body. Other
entries link here. Publication and Runtime conformance are separate facts.

**AI 原生模块是指：在自身责任边界内，内生具备适应概率性智能输入或输出的能力，并能够通过适用的解释、约束、验证、反馈、恢复或如实终止机制，维持可信工程结果的软件模块。**

The defining property is adaptation to probabilistic intelligent products inside
the module's own responsibility. Direct LLM integration is neither sufficient
nor necessary. A deterministic consumer, validator or relay of such products
must account for applicable semantic variation, incompleteness, ambiguity and
error. Merely accepting a schema-valid model response does not meet this norm.

This does not require every component to perform open semantic reasoning. Hashes,
transactions, exact file/source identity and permission checks may remain strictly
deterministic. Their job is to preserve their assigned invariants and expose
truthful results to the responsible semantic Owner; they are not intelligent
convergence modules. A task outside probabilistic boundaries can use ordinary
deterministic engineering without the full review below.

### 14.2 Adaptation belongs to the module or its existing Owner

A consuming module cannot assume that probabilistic products always arrive in
one fixed semantic expression or that first-pass correctness is guaranteed.
Its module contract must place the applicable interpretation, equivalence
assessment, missing/conflicting-information detection, validation, feedback,
bounded recovery and truthful outcome with that module or its existing lawful
Owner. Producer and consumer responsibilities remain distinct and traceable.

Use existing Owner-specific Self-Refine / Self-Converge, Feedback, Repair or
permitted regeneration when applicable. Shared parsing, validation, budget or
trace utilities can be reused. Business meaning, recoverability, qualification
and termination remain Owner responsibilities. Existing typed ports are not an
excuse to transfer semantics to a new general adapter.

Probabilistic behavior alone does not justify a unified Intent Adapter,
Stabilization Layer, global Self-Refine Coordinator, additional governance Owner
or parallel lifecycle. Before proposing a new mechanism, establish the concrete
capability gap against existing SOT and approved responsibility boundaries.

Adaptation may repair a candidate interpretation, check plan or lawful temporary
representation. It cannot rewrite Human Intent or admitted Engineering Reality,
change original values/order/Scope/qualifiers, fabricate source/evidence, expand
Effect Permit, bypass Verification/Guardian, convert UNKNOWN to PASS, repeat an
uncertain effect or reset budgets. Use §13's A/B/C classification before choosing
runtime recovery or engineering evolution. An exhausted trial remains exhausted;
evidence-backed system repair is a separate development responsibility.

### 14.3 Contract beyond Schema

For each applicable boundary, describe the following in its existing contract,
mission or review, with links to its current SOT and exact Reality:

| Contract dimension | Required design answer |
| --- | --- |
| Lawful variability | Which semantic-equivalent meanings/expressions, candidate methods or implementation paths are admissible? What ambiguity must remain explicit? |
| Preserved invariants | Which accepted facts, identities, source/version/provenance, original constraints, authority, effect permissions and independent gates cannot change? |
| Recoverable deviations | Which errors may the existing Owner repair, with what feedback, basis/lineage, remaining budget and certainty about previous effects? |
| Rejection or return | Which errors require refusal, waiting, truthful termination or return to a specific upstream lawful Owner? A budget stop alone does not prove the Human must alter the product goal. |
| Consumption eligibility | Which real Owner evidence qualifies the output for its next phase? Separate candidate generation, schema validity, semantic validity, Verification, Assurance and Human authorization. |
| Failure closure | How are unresolved information, unsuccessful recovery and budget exhaustion expressed without losing original obligations, receipts or UNKNOWN? |

These are design obligations, not mandatory new database fields, a universal
state machine or a fixed retry count. Keep the existing Owner's applicable budget
and side-effect semantics. Schema-valid does not imply semantically correct;
a different format does not by itself prove a different meaning. Exact protocol,
identity and authority requirements remain enforceable; lawful normalization or
repair must satisfy them before promotion.

Bind future lifecycle obligations to their actual later Gate and evidence Owner;
do not fabricate future authorization at a current stage. Continuous prohibitions
must be protected from their applicable current phase. Preserved constraint text
alone is not proof of an effective gate. Downstream adaptation consumes admitted
facts; it does not independently reinterpret raw Human wording to replace them.

### 14.4 Application within existing module responsibilities

The following applies at the Owner/version actually selected by Repository
Reality. It is a design responsibility map, not an implementation or qualification
claim and not a revision of any external Owner's formal contract.

| Module / existing Owner | Applicable endogenous adaptation and preserved boundary |
| --- | --- |
| WIC | Interpret and clarify open needs; expose ambiguity, assumptions and material information gaps; use the existing interaction/clarification responsibility. Preserve Human authority and the [WIC response contract](wic-response-contract.md). |
| IRK / Engineering Semantic Truth | Within intent admission and semantic validation, handle legitimate expression variation and bounded convergence while preserving provenance, exact basis and constraints. Admitted semantic facts remain authoritative and immutable under [Engineering Semantic Truth](engineering-semantic-truth.md); no default intervening interpretation layer. |
| Plan Steering / Planning / PWU | Handle candidate plan variation, dependencies, feedback and lawful plan evolution within governed production. Steering retains WHAT NEXT, planning/PWU retain their [existing production contract](spg-lite-domain-contract-baseline.md), and proposals do not silently alter admitted goals. |
| Executor | Detect recoverable execution errors, environment inconsistency, lack of progress and irrecoverable states. Recovery respects existing Attempt/context/budget/effect lineage and the [autonomy envelope](executor-autonomy-envelope-attempt-granularity-mvp-contract.md); capability never grants authority. |
| Verification | Distinguish lawful expression variation from real contract violations. Produce exact, attributable failed predicates and applicable feedback for candidate methods; use the correct content, Diff, source or governance evidence Owner. Genuine defects stay FAIL; Verification cannot grant Acceptance. |
| ECF | Within its existing context responsibility, assess sufficiency, source, version, authority/freshness, UNKNOWN and permitted projection/trimming. Preserve protected facts and cite actual sources. [ECF context integration](../context/ecf-integration.md) and Program ownership remain authoritative; a document link is not Runtime injection. |
| Guardian | Independently judge whether evidence and conclusions hold under existing assurance contracts. Missing/invalid evidence must block; convergence cannot cause Guardian or the producer to invent proof or lower its gate. Existing [Program ownership](program-architecture-decisions.md) remains intact. |
| Trace Analysis | Where the applicable existing trace/analysis responsibility is present, separate observed events, inference and suggestions; retain source/version references, uncertainty and limits of incomplete evidence. An unverifiable explanation remains UNKNOWN, not a reconstructed historical fact or permission. This norm creates no Trace Owner or service. |

Existing bounded-recovery mechanisms must be reused according to their actual
qualified scope. Presence of Self-Refine code, a model call or a new document
does not prove that any listed module fully meets this norm. Gaps need specific
subsequent Reality Audit evidence within the next authorized mission.

### 14.5 Default development and maintenance process

#### Task admission

Before substantial work on a probabilistic boundary, the existing Mission
Contract / capability review (§5.2) must answer:

1. What non-deterministic inputs, results or semantic changes will this module face?
2. Which variation is lawful, and which incompleteness or ambiguity must remain explicit?
3. Which engineering facts and governance boundaries must stay deterministic?
4. Which existing Owner supplies validation, feedback, recovery and termination?
5. If capability is missing, where is the smallest justified repair within an existing module?
6. What independent/non-prelisted evidence will demonstrate generality beyond one Case?

Ordinary deterministic work need not formally answer all six questions. The
Human Governor and AI collaborator use the existing authorized mission; no
separate Architecture Lead approval role is introduced.

#### Architecture and implementation review

Check for unjustified assumptions of perfect first-pass output; false rejection
of lawful semantic variation; aliases, keyword branches, fixed templates or
Case-specific rules substituting for semantic intelligence; unnecessary new
layers; transfer of uncertainty to an Owner that does not own it; duplicate
Self-Refine/governance; and bypass of Authority, Evidence or Guardian.

Justify necessary deterministic schemas, closed capability contracts and exact
checks by their real responsibility. Do not treat them as substitutes for open
semantic judgment or require identical model reasoning/steps/code.

#### Maintenance and Bug repair

First inspect actual Trace, authoritative Owner state, exact source/version and
failed predicates. Distinguish normal candidate variance, an existing feedback
or recovery mechanism failing its promise, a proven capability gap, and correct
governance refusal. Apply §13.2 before editing platform code. Evidence that
recovery cannot execute its declared contract is a system defect, not merely a
reason to ask the model again.

Find a shared cause before individual patches. Reject the cycle of a failed
example followed by another dedicated rule and another large regression.
Use §13.3 priorities and §13.4 proportionate validation. This principle does not
classify every model deviation as a Bug or every validator refusal as correct.

#### Qualification and closure

Apply the existing qualification/Mission boundary with non-prelisted positives,
lawful equivalent variants, necessary error/refusal cases, bounded recovery and
exhaustion/termination, plus representative real production evidence where
applicable. Preserve source, Owner, phase, authority and evidence identities.
Independent Holdout stays independent and cannot tune the implementation.

A fixed sample PASS, schema-valid generation or a document update cannot prove
generic capability. Qualification also does not demand infinitely many trials
or error-free output for every possible model response. Report qualified scope,
remaining obligations and UNKNOWN; independent Assurance and actual Human
Acceptance keep their own gates. [Golden Journey governance](watt-regression-protection-and-golden-journey-governance.md)
provides the existing protection and closure entry.
