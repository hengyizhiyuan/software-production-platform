# Watt Development Roadmap and Progress Reality

Status: **PROGRAM-LEVEL NAVIGATION / CURRENT REALITY**

Last updated: **2026-09-10**

This document maintains one high-level view of Watt's current development
phase, completed capability foundations, active findings, near-term priorities,
and future capability backlog. It is a navigation and alignment document. It
does not replace the [architecture source of truth](../../AI_context.md), the
[MVP scope calibration](mvp-scope-calibration.md), architecture contracts, or
detailed product specifications.

## 1. Watt Development Philosophy

Watt aims to build an AI-native software production system in which Human
intent, AI reasoning, governed execution, and Engineering Reality remain
coherent across a long-running development lifecycle.

The current collaboration principles are:

- the **Human Governor** defines Product Intent, major decisions, Authority,
  risk acceptance, and final acceptance;
- the **Architecture Lead AI** maintains product and architecture alignment,
  defines bounded mission contracts, and reviews implementation Reality against
  the North Star;
- the **AI Executor** autonomously implements an admitted bounded mission,
  including repository inspection, engineering choices, tests, repair,
  documentation, and evidence;
- **Evidence and governed Reality drive evolution**. Model confidence,
  conversational momentum, and implementation completion are not substitutes
  for verified product Reality.

The intended execution pattern is:

```text
Product / Architecture Alignment
    -> Mission Contract
    -> Autonomous Execution Within Governed Boundaries
    -> Evidence / Reality Review
    -> Human Acceptance
```

See [AI-native Development Execution Principles](../architecture/ai-native-development-execution-principles.md).

## 2. Current Overall Status

### New mission: Work-to-Delivery with multiple repositories

**2026-09-10 — Work-to-Delivery first slice: IMPLEMENTED / AUTOMATED VALIDATION PASS / RUNTIME READY / HUMAN PRODUCT ACCEPTANCE PENDING.** Human confirmed multiple repositories in one runtime and clarified that implementation should continue. The [as-built design](../architecture/work-to-delivery-multi-repository-spg-proposal.md) covers repository-scoped baseline/recovery, Work before asset binding, Document Package delivery and explicit Human acceptance. See the [implementation and acceptance report](../validation/work-to-delivery-first-slice.md) for actual evidence and runtime access. Existing closed foundations retain their original scope.

### Existing collaboration checkpoint


```text
Current Phase:
    Human–Watt Collaboration Layer Validation

Status:
    IMPLEMENTED
    REAL PROVIDER PROOF PASS
    HUMAN PRODUCT ACCEPTANCE IN PROGRESS
```

The current implementation checkpoint proves the product and engineering path
through a real Provider. Human Product Acceptance remains the authority for the
quality and usefulness of the collaboration experience; it must not be inferred
from deterministic or Provider evidence.

### Completed capability foundations

| Foundation | Current Reality |
| --- | --- |
| Work Interaction & Closed-loop Refinement (WIC) | Core CLOSED / PASS; Interaction, interpretation, governed Work admission, Work evolution, satisfaction, continuation, and new-Work transition are separated truthfully. |
| Work Reality | Append-only governed Work Reality revisions, focus preservation, and Human Authority boundaries are implemented. |
| Reality-driven Plan Steering | MVP CLOSED / PASS; reconstructable Reality determines WHAT NEXT without transferring Goal Authority to a model. |
| Software Production Control Room | Human-facing projection foundation and WIC/production-intelligence integration are implemented and accepted without creating a new Truth owner. |
| Guided Design foundation | Schema selection, design agenda, stage, current focus, rationale, progress, readiness, and restart reconstruction are implemented. |
| Human–Watt Interaction Layer | Persisted Human/Watt conversation and Interaction Turn lifecycle are implemented. |
| Design Intent Framing Layer | A persisted advisory frame separates the object being designed from business context before Guided Design schema selection; focused deterministic validation and the bounded real `gpt-5.6-sol` correction proof passed; Human Product Acceptance remains pending. |
| Async Interaction Processing | Bounded asynchronous Turn processing and durable terminal outcome projection are implemented. |
| Conversation history | Human and Watt messages remain reconstructable without turning conversation into governed Work Truth. |
| Conversation Intelligence | WIC/domain semantics are separated from bounded context assembly and a dedicated configurable Human-facing Provider; 30-case benchmark and six mandatory real Provider modes pass; Human Product Acceptance remains pending. |
| Real Provider validation | The mandatory Chinese product-design scenario completed with `gpt-5.6-sol`; schema matching and Guided Design facilitation were reached with sanitized evidence. |

Detailed evidence is recorded in
[Human–Watt Collaboration Layer Focused Validation](../evidence/human-watt-collaboration-layer-focused-validation.md).

The shared Human-facing language plane is specified in
[Human–Watt Conversation Intelligence](../architecture/human-watt-conversation-intelligence.md),
with focused and real-Provider evidence in
[its validation record](../evidence/human-watt-conversation-intelligence-focused-validation.md).

## 3. Current Known Findings

These findings describe product-experience work revealed by current validation.
They do not invalidate the completed architecture foundations and must not be
silently promoted into new architecture or implementation scope.

### 3.1 Design Facilitation Experience Gap

Current Reality includes:

- Design Schema;
- Design Stage;
- Next Focus;
- focus rationale.

Human Acceptance observations indicate that the experience still needs
stronger:

- proactive design leadership;
- explanation of the overall design path;
- progress narrative;
- decision guidance at material design choices.

The target is not a longer questionnaire. Watt should help the Human understand
where the design is, why the current focus matters, and which decision would
move the Motive forward. Any implementation must preserve Design Reality,
Human Authority, and Plan Steering ownership.

Current refinement status: **V2.1 IMPLEMENTED / FOCUSED VALIDATION PASS / REAL
PROVIDER V2.1 PROOF PASS / HUMAN ACCEPTANCE PENDING**. The implementation now
supplies the ordered Design Schema to the Provider while requiring progressive
disclosure in the Human-facing response. It reuses known Interaction Reality,
briefly explains the approach and current stage, leads with useful direction or
trade-offs when supported, recommends one next design action, and asks at most
one material question. It no longer projects the complete design route into the
first persisted response. Engineering evidence resolves the identified
implementation gap; Human experience acceptance remains separately pending.

### 3.2 Streaming Experience Gap

Asynchronous processing, persisted Turn status, and a streaming delivery seam
exist. The current experience does not yet establish a truly incremental,
ChatGPT-level conversational response experience.

Further product work should evaluate:

- incremental visible response delivery;
- lower perceived latency;
- clear working, partial, completed, and failed states;
- continuity between streamed presentation and persisted final Reality.

Streaming presentation must not become a second message truth source or cause
partial model output to be mistaken for admitted Work Reality.

Current refinement status: **V2.1 IMPLEMENTED / FOCUSED VALIDATION PASS / REAL
PROVIDER V2.1 PROOF PASS / HUMAN ACCEPTANCE PENDING**. The Codex adapter
consumes real agent-message deltas, and the UI applies them directly to one
transient Watt message in conversation history. Completion replaces that
projection with the persisted message for the same Turn; deterministic and
real Provider evidence prove exact stream/final equality and no duplicate
response surface. The terminal message remains the only durable conversation
record; process-local deltas remain bounded UX state.

## 4. Current Priority Roadmap

The following order is the current program priority. Changing it requires an
explicit product or architecture decision rather than ordinary implementation
convenience.

### Priority 1 — External Design Intake Capability

**Current action:** documentation only.

```text
Status:
    FUTURE HIGH PRIORITY CAPABILITY
    NOT IMPLEMENTED
```

The next design step is to define how external design materials enter Guided
Design as bounded, attributable input without becoming automatic Design Truth.
No intake implementation, schema, Provider behavior, or new admission path is
authorized by this roadmap.

### Priority 2 — Human–Watt Collaboration Experience Improvement

Current Reality: response-quality refinement v2.2 is implemented with focused
validation and four-scenario real `gpt-5.6-sol` proof. Human Product Acceptance
remains pending.

Focus:

- stronger Design Facilitation behavior;
- clearer conversational experience;
- genuinely incremental streaming where justified;
- proactive guidance that remains inside governed boundaries;
- preservation of Human Authority and reconstructable Interaction Reality.

### Priority 3 — UX/UI Reconstruction

Goal: transform the current interface into a Human-facing AI collaboration
workspace, not merely restyle the existing screens.

Focus:

- conversation as an understandable collaboration surface;
- visible design path and progress;
- clear current focus and next meaningful decision;
- accessible governed Reality, Attention, and trust basis;
- progressive disclosure rather than dashboard overload.

This priority does not itself authorize a Workspace entity, a new state store,
or duplicated product truth.

### Priority 4 — TNGA to Watt Full Text Migration

Scope:

- documentation language;
- UI text;
- examples;
- cross-references;
- naming consistency.

Migration must preserve historical evidence where the original name is part of
the fact being recorded. It is a terminology consistency effort, not a domain
or persistence rename by default.

## 5. Future Capability Backlog

Items in this section are important future directions. They are not described
as current capability and are not authorized for implementation by this
document.

### 5.1 Production Execution Package Lite

**Purpose:** connect Human Intent, Work Reality, Plan/PWU, production contract,
context basis, Executor Attempt, produced artifacts, Verification evidence, and
Runtime Reality into a reconstructable execution lineage.

**Status:** future capability. See
[Production Execution Package Direction](../architecture/production-execution-package-direction.md).

### 5.2 PWU Deepening

**Purpose:** provide **execution continuity without execution monolithicity**.
PWUs should support bounded execution that can be paused, reconstructed,
verified, recovered, and continued across replaceable Executors and models
without losing the encompassing Work direction. A PWU should carry enough
objective, boundary, context, access, acceptance, and Evidence responsibility
for an Executor to complete a meaningful production increment autonomously;
it should not regress into micro-task or line-by-line orchestration.

**Status:** future deepening beyond the current one-PWU-first MVP boundary.

### 5.3 Engineering Context Fabric (ECF)

**Purpose:** provide decision-scoped context discovery, assembly, freshness,
provenance, and governed delivery to planning and execution capabilities.

**Status:** full ECF is deferred; current Context Assembly Lite and integration
boundaries remain the available foundation. See
[ECF Integration](../context/ecf-integration.md).

### 5.4 Guardian Enhancement

**Purpose:** deepen independent Engineering Assurance through stronger Evidence,
Finding, coverage, quality, and trust gates while avoiding step-by-step
micromanagement of the Executor.

**Status:** future enhancement beyond current Verification. See
[Guardian Integration](../assurance/guardian-integration.md).

### 5.5 Design Schema Library

**Purpose:** turn proven design methodologies, stage structures, dependencies,
questions, and completion expectations into reusable governed assets.

**Status:** future methodology assetization. The current seed schemas are an
implementation foundation, not yet an enterprise methodology library. See
[Guided Design Core](../architecture/guided-design-core.md).

### 5.6 Work Assets and Repository Reality

**Purpose:** associate repositories, documents, issue/planning systems, design
artifacts, Runtime environments, and other external systems with Work as
attributable inputs or execution surfaces; extract source Reality without
turning attachment into Work Truth or introducing a Project lifecycle.

**Status:** future bounded Work Asset / Asset Intake and Repository Reality
capability. Existing Engineering Resource and repository binding is only the
narrow foundation. See the
[Work-centric Production Model](../architecture/work-centric-production-model.md).

### 5.7 Responsibility-aware Reality Projection

**Purpose:** project one authoritative production Reality according to
execution, lead, product/engineering-management, and program/organizational
responsibility, using progressively more aggregated, exception-oriented, and
decision-oriented views rather than more raw data.

**Status:** future extension of the current Control Room perspectives. It does
not authorize user-role persistence, team management, permissions, or an
organization hierarchy.

### 5.8 Minimum-sufficient Capability and Access Provisioning

**Purpose:** derive the Assets and temporary/scoped capabilities needed by an
admitted Work/PWU, provision least-privilege action access, and withdraw it when
no longer required. This is distinct from ECF's least-context responsibility.

**Status:** future architecture and implementation work; no IAM/RBAC
replacement or capability marketplace is authorized. Sections 5.2–5.8 are
governed together by the
[Work-centric Production and Responsibility Principles](../architecture/work-centric-production-and-responsibility-principles.md).

### 5.9 External Engineering Intelligence

**Status:** **RECORDED / DEFERRED — valuable future product capability, not current implementation priority**.

**Purpose:** a future Human-visible capability allowing users to research
mature external engineering solutions, understand their mechanisms, compare
alternatives, evaluate local applicability and risks, and govern adaptation
into the user's system. Human-triggered research is the primary product form;
future Watt-suggested research remains within explicit governance.

**Placement:** after the current major development priorities and existing
future backlog entries. Priorities 1–4 remain unchanged; this is not a new
Priority 5, current MVP scope, or implementation authorization.

External sources remain evidence and design inputs, not Truth. Work, WIC,
Guided Design, Plan Steering, PWU/Executor, SPG, ECF, Guardian, and Human
Authority retain their existing ownership. Future ECF, Executor/PWU, Guardian,
and product/architecture reviews should revisit the
[External Engineering Intelligence Direction](../architecture/external-engineering-intelligence-direction.md),
including its User Story, expected research synthesis, adaptation provenance,
invariants, and explicit non-goals. Internal Reference Engineering is a related
use case, not a substitute for this user-facing product capability.

## 6. Roadmap Maintenance Rules

Update this document when:

- a major capability completes or changes status;
- program priority order changes;
- a new major product requirement is admitted;
- an architecture direction materially changes;
- Human Acceptance reveals a finding important enough to influence product
  direction or sequencing.

Do not update this document for ordinary bug fixes, local implementation
details, routine test changes, or transient execution incidents. Those belong
in the relevant contract, evidence, finding, or engineering history document.

Each update must:

1. distinguish current implemented Reality from future direction;
2. preserve historical failures and prior checkpoints rather than rewriting
   them;
3. link to the authoritative detailed document instead of duplicating it;
4. keep Human Authority, architecture boundaries, and explicit deferrals
   visible;
5. avoid presenting a roadmap item as implementation authorization.

## Human collaboration pipeline review — 2026-09-09

The [architecture review and measured optimization](../evidence/human-collaboration-pipeline-optimization.md)
completed within the Human collaboration envelope. Native pre-Work conversations
with matching models and reasoning settings now share one strict Provider Turn;
WIC interpretation, Guided Design structure, Conversation expression and Human
Authority ownership remain distinct. Active Work and explicitly replaced or
separately configured providers retain staged processing.

Five real cases reduced median first-text delivery from 58.45 s to 20.63 s.
Median full completion changed from 63.55 s to 59.12 s, with two slower cases.
The intermediate low-effort two-stage trial did not reliably improve latency
and was not adopted as default. Context correction/reuse and dialogue continuity
were repaired. The final language still needs Human acceptance: it remains
formal and sometimes repeats or bundles clarification questions.

Validation: 94 related contract tests, 39 isolated PostgreSQL integration tests,
25 JavaScript tests and the five-case real coalesced proof passed. No deployed
Runtime or Trusted Baseline changed. Watt Product MVP is not thereby closed.


## Human collaboration v3.1 — product intelligence and latency refinement

The [v3.1 report](../evidence/human-collaboration-pipeline-v31.md) records a bounded
quality/performance refinement of the existing single-call pre-Work pipeline.
It adds useful provisional recommendations, plain direct answers, one independent
clarification, validated reuse of unchanged meanings/frames, and explicit
semantic-validation/assessment-commit/final-persistence observations. Full current
facts and source records remain; no new intelligence owner or production lifecycle
was introduced. The first measured trial is retained despite its latency regression.
Final same-model Chinese samples improve median first text **23.84 → 18.80 s**
and completion **63.57 → 52.89 s**, but A/C regressions increase mean first text
**23.48 → 26.28 s** and leave mean completion effectively unchanged
(**58.38 → 58.85 s**). Consistent latency improvement is not proven. Quality,
source/authority fidelity and complete final-source validation are documented;
Human product acceptance remains pending. Final contracts: 128 passed; related
PostgreSQL integration: 41 passed (6 phase tests rerun on final source); JS: 25
passed. All 15 real turns across three conditions preserved one call per message
and created zero Work/Runtime rows.

Human product acceptance and consistently mature-assistant response speed remain
open. This record adds current evidence without rewriting historical shortcomings.
