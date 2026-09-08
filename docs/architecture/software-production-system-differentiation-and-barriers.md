# Software Production System Differentiation and Architectural Barriers

## 1. Status and scope

```text
Document type
    ARCHITECTURE PRINCIPLE / STRATEGIC DIRECTION / EVIDENCE-BASED RATIONALE

Implementation authority
    NONE

Market-leadership claim
    NONE
```

This document explains why Watt is designed as an AI-native software
production system rather than a collection of isolated AI features. It records
architectural rationale, current evidence, future direction, and hypotheses
that still require evaluation.

It does not claim that individual mechanisms are impossible to reproduce, that
Watt has an established market moat, or that every capability described here
is implemented. Durable differentiation is an intended system property that
must continue to be demonstrated through governed production evidence.

## 2. Core thesis

The intended architectural differentiation of AI-native software production
does not come from one model, Agent, prompt, workflow, or user interface. It
comes from organizing replaceable intelligence into a production system that
can remain:

- directionally coherent;
- governed by explicit Human Authority;
- bounded during execution;
- independently observable and verifiable;
- reconstructable across sessions and Providers;
- recoverable after interruption or failure;
- responsive to new Reality without rewriting history;
- capable of accumulating trusted engineering knowledge.

The system-level loop is:

```text
Human Intent
    -> Governed Design
    -> Production Planning
    -> Bounded Execution
    -> Verification
    -> Runtime Reality
    -> Feedback Evolution
```

A chat interface, code generator, Agent loop, task list, or tool orchestrator
may implement one part of this path. None alone establishes the authority,
truth, lineage, feedback, and recovery semantics needed by the complete loop.

## 3. Isolated features versus system capability

The following comparison is architectural analysis, not a measured market
survey:

| Isolated capability | Relative replication difficulty | Why it is insufficient alone |
| --- | --- | --- |
| Chat entry | Low | Captures interaction but does not establish governed Work Reality |
| Code generation | Low | Produces candidate output but not trusted production truth |
| Agent dispatch | Low | Starts activity but does not define Authority or completion |
| Task list | Low | Shows intended activity but not current engineering Reality |
| UI projection | Low | Presents facts but must not own or manufacture them |

System capability depends on coherent semantics across:

- Truth ownership;
- Context continuity;
- Human Authority;
- Reality feedback;
- Evidence lineage;
- Recovery semantics.

These concerns cross module and lifecycle boundaries. Their difficulty lies
less in implementing each object than in preserving their relationships under
change, failure, replacement, and long-running use.

## 4. Multiplicative production capability model

Use the following as a qualitative architecture model:

```text
Production Capability
    = Planning
    x Context Fidelity
    x Execution Discipline
    x Assurance
    x Reality Feedback
```

This is not a current metric, benchmark result, or literal production formula.
It expresses a constraint: severe weakness in any one factor can dominate the
whole system even when the other factors are strong.

Examples:

- strong execution against the wrong context produces the wrong result faster;
- strong planning without bounded execution cannot control side effects;
- generated artifacts without assurance do not become trustworthy outcomes;
- verification without Reality feedback cannot steer the next action;
- current Reality without Human Authority cannot silently redefine the Motive.

The design objective is therefore balanced system throughput, not maximization
of model output alone.

## 5. Core capability relationships

### 5.1 Reality-driven Plan Steering

Plan Steering is not task-list generation. It answers `WHAT NEXT` by comparing
the long-lived Work objective and admitted Plan with current governed Reality:

```text
Current Reality
    -> Plan Steering
    -> next appropriate governed step
```

Its role is to preserve direction while allowing evidence-based revision. It
resists both mechanical execution of a stale plan and local optimization that
drifts away from the Motive. Watt's bounded Reality-driven Plan Steering MVP is
implemented and closed; advanced autonomous replanning remains outside that
closure.

See [Reality-driven Plan Steering Principles](reality-driven-plan-steering-principles.md)
and the [MVP Behavioral Contract](reality-driven-plan-steering-mvp-contract.md).

### 5.2 Production Work Unit

A PWU is not merely a small task. It is the bounded production-unit contract
that allows a long-running Work to progress through independently governable
increments.

The intended principle is:

> Execution continuity without execution monolithicity.

In Chinese:

> 保持生产认知连续性，而不要求执行过程成为不可分割的单体。

A single long Executor run can retain local context and adaptation, but it also
increases opacity, interruption cost, recovery ambiguity, failure radius, and
Provider lock-in. A PWU-oriented path instead aims for:

```text
PWU-1
    -> Reality update
    -> governed context reconstruction
    -> PWU-2
    -> Reality update
    -> ...
    -> PWU-N
```

Persisted Work, Plan, context, artifacts, evidence, and Reality must carry the
continuity that would otherwise be hidden in one Executor session. This should
make production pausable, recoverable, replaceable, verifiable, and auditable
without discarding the useful learning of prior increments.

Current Watt implements governed PWU and Attempt boundaries. The claim that
segmented PWU execution can achieve materially equivalent outcomes to a long
continuous run is an architectural hypothesis requiring the
[PWU Execution Continuity Benchmark](production-benchmarks.md#pwu-execution-continuity-benchmark).

### 5.3 Future ECF

Future ECF is not ordinary retrieval-augmented generation and is not a rule to
query all knowledge for every interaction. Its strategic purpose is to provide
the smallest sufficient governed engineering context for an important
decision or production activity.

```text
Important decision or production activity
    -> decision-scoped context routing
    -> minimum sufficient governed facts
    -> context assembly with provenance and freshness
```

The intended capability layers are:

1. **Truth Maintenance** — what is true, why it is true, who admitted it, and
   which version is applicable;
2. **Context Routing** — which governed facts the current role and decision
   require;
3. **Context Assembly** — a bounded, purpose-specific projection with identity,
   provenance, and freshness.

Watt currently implements Context Package Lite for governed execution. Full ECF
and decision-scoped context intelligence remain future capabilities. This
document does not authorize ECF implementation or transfer context ownership
to SPG.

See [ECF Integration](../context/ecf-integration.md) and the
[SPG Lite Domain Contract Baseline](spg-lite-domain-contract-baseline.md).

### 5.4 Future Guardian

Guardian is intended as an Assurance capability, not merely a code-review
tool. Its strategic pressure is:

> Assurance throughput must scale with AI production throughput.

As AI production volume rises, Human review cannot be assumed to scale
linearly. Future Guardian capabilities may organize Evidence, Gates, Findings,
coverage, confidence, and challenge so that faster production does not imply
uncontrolled quality loss.

Watt already separates Executor claims, independent Observation, Completion,
Verification, Human Acceptance, and Runtime truth. A complete Guardian system
is not implemented by those foundations and is not authorized by this record.

See [Completion and Trust](spg-completion-trust.md) and the
[Integration Boundary](integration-boundary.md).

### 5.5 Human Authority and Reality feedback

Human Authority defines Motive, material direction, risk tolerance, scope
expansion, and final accountability. AI capabilities may interpret, recommend,
plan, execute, verify, and optimize only within their admitted boundaries.

Reality feedback closes the loop. Provider output alone is not Reality, and a
different model preference is not a sufficient reason to change the Plan.
Observed artifacts, Verification, Runtime state, Human decisions, Findings,
and accepted outcomes provide the governed basis for continuation or revision.

## 6. Why the components form a system rather than a feature bundle

The key relationships are contractual:

```text
Human Authority constrains Design and Plan
Plan Steering selects WHAT NEXT from Reality
PWU bounds one admitted production increment
Context supplies the exact governed basis
Executor performs HOW inside the envelope
Verification qualifies evidence
Runtime records applicable trusted Reality
Feedback returns new Reality to Work and Plan evolution
```

Removing a boundary does not merely remove a feature. It changes the meaning
of the remaining facts. For example, an artifact without its source baseline,
context, completion obligations, verification, and authority lineage cannot be
treated as an equivalent trusted production result.

The intended architectural barrier is therefore the accumulated coherence of
these relationships and their evidence, not secrecy around an isolated
implementation technique.

## 7. Practice evidence and lessons

### Case 1 - Guided Design gap discovery

**Observed context:** WIC, governed production, Plan Steering, and Control Room
projections each had validated foundations. A practical question remained:
how would Watt guide the design of a new operations-management platform step by
step rather than jump from a vague Motive to production?

**Gap discovered:** the system lacked an explicit Guided Design process that
could structure important questions, preserve one current focus, record
governed results, explain readiness, and form a reviewable production proposal.

**Lesson:** locally correct infrastructure does not prove that the Human-facing
product loop is complete. Product-level scenarios can expose a missing
coordination capability between otherwise valid modules.

**Current Reality:** Guided Design Core now implements a Design Schema, an
append-only Design Agenda, Steering-owned current focus, governed semantic
results, explicit readiness, and production-proposal review. Focused validation
and real Provider proof pass; Human Product Acceptance remains pending.

Evidence: [Guided Design Core](guided-design-core.md) and
[Focused Validation](../evidence/guided-design-core-focused-validation.md).

### Case 2 - Reviewed checkpoint versus Runtime activation

**Observed context:** Control Room implementation existed in repository Reality
while the running application and Current Trusted Baseline still represented an
older governed state. Application availability did not make the reviewed
checkpoint active.

**Incorrect assumption:**

```text
Reviewed Git checkpoint
    -> Runtime activation
```

**Required governed relationship:**

```text
Reviewed Git checkpoint
    -> eligible Trusted Baseline admission
    -> exact Runtime activation
```

If the reviewed checkpoint is not eligible in an existing Runtime lineage, a
fresh isolated Runtime may bootstrap it as its own initial Trusted Baseline;
the system must not manufacture lineage or directly replace Runtime state.

**Lesson:** architecture assumptions do not override engineering Reality.
Repository revision, Trusted Baseline, active package/static fingerprints,
lineage, and clean checkout must agree before `ACTIVE_AT_TRUSTED_BASELINE` can
be claimed.

Evidence: [Control Room Acceptance Preparation](../evidence/control-room-slice-4-human-acceptance-preparation.md)
and [Trusted Baseline / Active Runtime Convergence](trusted-baseline-active-runtime-convergence-lite.md).

### Case 3 - Human Authorization Work preview gap

**Observed context:** Control Room Human Product Acceptance showed that the
Human could distinguish expression, interpretation, and governed Reality, but
the pre-admission experience did not provide a complete governed Work proposal
preview before Authority transfer.

**Finding:** `PRE_AUTHORIZATION_WORK_PREVIEW_REQUIRED`.

**Lesson:** understanding alignment and Work authorization are different Human
decisions. The future experience should make objective, outcome, scope,
constraints, expected artifact, production boundary, and impact visible before
the Human admits Work.

Guided Design implements production-proposal review for its exact transition,
but the broader Work Formation Review remains an open high-priority product
improvement.

Evidence: [Work Formation Review Before Admission](../product/work-formation-review-before-admission.md)
and [Control Room Human Acceptance](../evidence/control-room-slice-4-human-product-acceptance.md).

### Case 4 - PWU continuity benchmark proposal

**Question:** can segmented, governed PWU execution preserve the useful
continuity of one long Executor run while improving pause, recovery,
replacement, verification, and auditability?

This question is not yet answered by implementation claims alone. The future
benchmark compares a long continuous Executor run with PWU-segmented execution
against equivalent governed objectives and completion obligations.

**Lesson:** granularity is not only a scheduling choice. It affects context
reconstruction, failure radius, Provider replaceability, evidence quality, and
the ability to recover truthfully. The architectural hypothesis must be tested,
not promoted as a proven advantage.

See the [PWU Execution Continuity Benchmark](production-benchmarks.md#pwu-execution-continuity-benchmark).

## 8. Current capability, future direction, and hypothesis boundary

| Item | Classification |
| --- | --- |
| Governed production Runtime, PWU/Attempt boundaries, Completion, Verification, Runtime Commit | Implemented foundations |
| Bounded Reality-driven Plan Steering MVP | Implemented / closed |
| Guided Design Core | Implemented / focused validation pass / Human acceptance pending |
| Context Package Lite | Implemented foundation |
| Full ECF | Future capability / not implemented |
| Full Guardian Assurance system | Future capability / not implemented |
| Production Execution Package / Passport | Future high-priority direction / not implemented |
| Multiplicative capability model | Architecture reasoning model / not a measured metric |
| PWU segmented-versus-continuous equivalence | Architecture hypothesis / benchmark not run |
| Durable system-level differentiation | Strategic intent requiring continuing evidence |

## 9. Final principle

Watt's objective is not to create a smarter Coding Agent. It is to create a
software production system in which AI can participate reliably in complex,
long-running engineering work.

```text
Ordinary Agent framing
    AI capability
        -> task execution

Watt system framing
    Human Intent
        -> Governed Reality
        -> AI Production System
        -> Trusted Software Outcome
```

The durable value sought by this architecture is the ability to preserve
intent, authority, context, evidence, and truthful evolution across the whole
production lifecycle while models and execution mechanisms remain replaceable.

## 10. Non-goals

This record does not:

- authorize implementation of ECF, Guardian, Production Passport, or a new
  benchmark harness;
- add an MVP feature, schema, API, lifecycle state, or product surface;
- claim deterministic model output or guaranteed cross-Provider equivalence;
- claim a measured commercial moat or competitor incapability;
- reinterpret future capabilities as current Watt Reality.
