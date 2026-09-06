# 工律 / Watt Product North Star

## Status and authority

**PRODUCT ARCHITECTURE SOURCE OF TRUTH — HUMAN GOVERNOR CALIBRATED / APPROVED**

This compact North Star governs product-shape decisions. It does not replace
the system Architecture Baseline, subsystem contracts, implementation Reality,
or historical evidence. Detailed designs may refine it but must not silently
remove its product-shape essentials.

## 1. Product identity

```text
Chinese product brand          工律
Internal development codename  Watt
Formal English product brand   UNDECIDED / DEFERRED
Previous internal codename     TNGA
TNGA -> Watt migration         APPROVED / DUE AS A SEPARATE BOUNDED TASK
```

Historical TNGA references remain truthful in their original context until the
separate repository-wide migration. Watt is fundamentally an **AI-native
Software Production System**: it organizes Human intent, engineering judgment,
machine intelligence, governed production, independent evidence, and baseline
evolution into a trustworthy, continuously evolving loop.

```text
Human defines intent.
AI amplifies capability.
System ensures trust.
```

Watt is not defined by a Coding Agent, chatbot, model wrapper, static project
management system, or any single Software Factory business/operating model.
Its production capabilities may later support internal production, a
SaaS/platform product, software-factory operating models, or other production
organizations. Models, providers, Agents, sessions, and deployment profiles
are replaceable capability implementations; none defines Watt or owns
Production Truth.

Source basis: [Platform Charter](../foundation/platform-charter.md),
[Problem Definition](../foundation/problem-definition.md),
[System Architecture Baseline v0.1](system-architecture-baseline-v0.1.md), and
[MVP Architecture](mvp-architecture.md).

## 2. Human–Watt relationship

A Human may arrive without a complete task. Before any Work exists they may
chat, explore, express an incomplete Motive, add context gradually, correct
earlier statements, and answer Watt's clarification questions. Watt must
progressively interpret and refine that input. Conversation alone does not
create a Work:

```text
FIRST UTTERANCE != WORK CREATION API

Human Interaction
    -> interpretation and information collection
    -> refinement and shared understanding
    -> Work Admission Readiness
    -> governed Work creation/admission
```

After Work admission, the Human relationship continues. Additional context,
corrections, constraints, requests, preferences, feedback, and questions are
interpreted against current governed Work/Plan Reality. They are neither
ignored because production started nor treated as immediate truth or Executor
instructions.

Watt should absorb ordinary interpretation, planning, technical execution, and
self-correction work. The Human is a Governor and collaborator, not a technical
debugger, retry mechanism, or manual `Continue` button. Material intent,
direction, scope, constraint, risk, and acceptance decisions return through a
legitimate Human Authority boundary.

The continuing interaction surface is a product-shape requirement. Its visual
form is not: a ChatGPT-style UI, dashboard, or specific conversation layout is
not an architecture invariant.

## 3. Conversation, shared understanding, and truth

Conversation is source material and provenance, not execution Authority.
Something said most recently is not admitted, true, or highest priority merely
because it appeared in chat.

```text
Human Input
    -> Candidate Interpretation / Fact / Constraint / Request / Correction
    -> Impact Assessment
    -> Shared Understanding
    -> governed admission where applicable
    -> versioned Work / Decision / Plan Reality
```

Watt must expose a compact Shared Understanding sufficient for the Human to
calibrate at least:

- Watt's current interpretation of the Motive and desired outcome;
- admitted important context/facts, constraints, and significant requests;
- unresolved material questions;
- the latest interpreted change and its expected impact;
- what is merely candidate versus what is actually governed.

This is the product manifestation of `Conversation != Truth`. An Interaction
Record answers *what was communicated*; Interpretation answers *what Watt
currently infers*; governed Work Reality answers *what was admitted*; Runtime
and production records answer *what happened and is authoritative*.

Only admitted, versioned, traceable artifacts, contracts, facts, constraints,
decisions, context, and Baseline references may authorize execution. AI
inference, confidence, textual confirmation, a diagram, or a prototype does not
create Authority. Advanced multimodal
[Interpretation Externalization](interpretation-externalization-and-multimodal-alignment.md)
remains a future differentiation capability, not a mandatory Work gate.

## 4. Motive, Work, PWU, Plan, and feedback

### Motive

Motive is what the Human genuinely wants to make happen. It starts with Human
expression and is progressively refined into governable intent. Its first
wording need not be complete, executable, or authoritative.

### Work and Work Reality

Work is the current internal governed representation of a Motive. A Work may be
narrow or broad, short-lived or long-lived, and may yield code, documentation,
design, evidence, analysis, Runtime/product state, or multiple related trusted
artifacts. Work Reality is its versioned authoritative product/engineering
intent: admitted outcome, relevant context, constraints, requests, scope,
decisions, and provenance. It evolves through governed revisions, never by
overwriting truth with the latest conversation.

At Product level, a long-lived Work represents the governed state of an
evolving realization relationship around a Motive, not one production ticket.
Goal remains an optional weak aggregation; Project/Initiative is not a required
parent.

### PWU and production cycle

PWU, not Work, is the bounded production unit. A production cycle is one exact,
independently governed SPG path from production admission through execution,
observation, Verification, Candidate governance, and Runtime Commit. One
long-lived Work may contain multiple cycles, each bound to Reality at its own
admission.

```text
Production Cycle COMPLETE
    != Motive satisfied
    != terminal Human–Work relationship ended
```

### Plan

A Plan is a reconstructable, living, governed progression structure for a Work.
It answers what should happen next and why from governed Reality. It preserves
direction unless changed Reality justifies a traceable revision and references,
rather than duplicates, authoritative facts. A single-PWU Production Plan is
not the complete long-lived Steering Plan.

### Feedback

Human feedback, user testing, Verification, Runtime findings, engineering
findings, and production outcomes may all affect a Work. Their authoritative
facts remain owned by their source domains. Watt interprets their relevance,
admits any resulting Work change through governance, and lets Plan Steering
reassess what happens next.

Source basis: [Motive / Work / Plan Concept Calibration](motive-work-plan-concept-calibration.md),
[Reality-driven Plan Steering Principles](reality-driven-plan-steering-principles.md),
and [Work Interaction & Closed-loop Refinement Contract](work-interaction-closed-loop-refinement.md).

## 5. Closed-loop software production

Watt's core abstraction is a continuing feedback-driven relationship, not
`requirements -> code -> done`:

```text
Human interaction
    -> interpretation / shared understanding / governed refinement
    -> governed Work Reality
    -> design and Reality-driven Plan Steering
    -> exact production admission and bounded PWU execution
    -> independent observation and Verification
    -> Human Authority where required
    -> trusted Baseline / active Runtime / product Reality
    -> feedback and impact assessment
    -> governed Work evolution
    -> Plan reassessment and next appropriate production cycle
    -> ... until the Motive is currently satisfied
```

Implementation and Runtime Reality may challenge earlier requirements, design
assumptions, Plan ordering, or completion claims. **Roadmap guides production;
Reality governs roadmap.** New model output alone is not new Reality.

When the current objective is satisfied, Interaction may continue. Input that
still serves the same Motive may cause governed continuation; a materially new
demand should normally produce a new Work recommendation so the completed
boundary remains truthful. A lightweight Product Experience may default to
“continue in new Work” after notice and an opportunity to object. That default
must not silently inherit Authority or admit production, and its exact countdown
or visual treatment is not architecture truth.

## 6. Human Authority and trust

Human Authority governs intent, direction, material scope and constraints,
major trade-offs, risk/exception acceptance, and final governance where policy
requires it. It does not erase observed facts, waive lineage or consistency,
grant an Executor unlimited privilege, or turn Provider confidence into
acceptance.

No actor owns Production Truth alone. Models may propose; Executors may produce;
Verification/Guardian owns assurance evidence; Humans exercise distinct
Authority; and Runtime adjudicates transitions through contracts and policy.
Generated is not trusted, Verification is not Acceptance, Authorization is not
Commit, and Trusted Baseline is not necessarily Active Runtime.

## 7. Product invariants

1. A chat message is not authoritative execution truth.
2. First utterance does not automatically create or admit a Work.
3. Candidate interpretation must remain distinguishable from governed Reality.
4. The Human can calibrate what Watt interpreted and what Watt admitted.
5. Motive is Human product intent; its first wording may be incomplete.
6. Work is not inherently atomic, short-lived, or equivalent to one PWU.
7. PWU is the bounded governed production unit; a Provider Turn is not.
8. Work admission is distinct from exact production admission.
9. A Plan must be reconstructable without conversation/session continuity.
10. Models reason over the Plan; models do not own the Plan.
11. Preserve the admitted Plan unless changed Reality justifies revision.
12. New input must not silently replace the active objective or mutate an
    executing Production Contract.
13. Provider success is not Production Truth; Verification is independent.
14. Production-cycle completion does not automatically close the Work
    relationship.
15. Human Authority cannot be replaced by model confidence or bypass Runtime.
16. Runtime/Verification Reality may challenge design and change what happens
    next.
17. Operational optimization must not mutate governed objective, Authority,
    contracts, or historical truth.
18. Model, provider, Agent, session, host, and Runtime Profile replacement must
    not by itself redefine direction or trust semantics.

## 8. Product status and completeness guardrail

```text
Governed Production + Reality-driven Plan Steering Core
    CLOSED / PASS

Work Interaction & Closed-loop Refinement Core
    ARCHITECTURE DEFINED / IMPLEMENTATION NOT STARTED

Watt Product MVP
    NOT CLOSED
```

The historical `WATT MVP CORE — CLOSED / PASS` decision remains truthful for
its proved capability boundary: long-lived admission, Steering, semantic
design, governed production, independent Verification, exact Human Candidate
Authorization, Runtime Commit, activation, and Human-operated acceptance. Its
broad label created scope-compression risk; it must not be used alone to claim
complete Product-MVP closure.

Before major architecture closure, Product-MVP closure, deployment, or
productization, perform a lightweight **North Star Consistency Check**:

1. name the exact capability/product boundary being closed;
2. map evidence to the Human–Watt relationship and feedback loop;
3. list essentials present, partial, or intentionally deferred;
4. confirm implementation limits were not promoted into product principles;
5. preserve open/deferred semantics instead of hiding them behind a broad
   closure label.

Source basis: [Watt MVP Core Closure](../evidence/mvp-core-closure.md),
[Dogfood #9](../evidence/dogfood/long-lived-motive-dogfood-9-production-loop-closure.md),
and [Dogfood #10](../evidence/dogfood/long-lived-motive-dogfood-10-human-acceptance.md).

## 9. Product-shape essentials and legitimate deferrals

The following may be implemented incrementally but cannot be silently removed:

- continuing natural-language Motive formation before Work;
- visible Shared Understanding and conversation-to-contract;
- continuing interaction and governed Work evolution after admission;
- long-lived Work distinct from bounded PWUs;
- reconstructable, anti-drift, Reality-driven Plan Steering;
- closed-loop feedback admission and reassessment;
- Human-as-Governor with controlled autonomy;
- independent evidence, truth lineage, and Baseline/Runtime distinction;
- provider/model/session independence and no single-actor truth.

Legitimate later-stage implementations include full ECF/Guardian, advanced
multimodal Interpretation Externalization, Multi-PWU/DAG and advanced
replanning, sophisticated capacity/scheduling/routing/economics, durable
supervision and fleets, HA/distribution, comprehensive Evidence UI,
multi-user/organization governance, semantic branching/merge, provider
marketplace/residency automation, broader Runtime Verification, complete
maintenance-lineage recovery, and Linux deployment/promotion.

## 10. Open decisions

- Formal English product brand.
- Exact interaction UI and default-transition timing.
- Which raw Interaction Records are retained, redacted, or ephemeral.
- Which Work-admission profiles are required for each future Work shape.
- Future YiJue-backed deliberation contract, if separately admitted.

These open decisions do not weaken the product invariants above and authorize
no implementation by themselves.
