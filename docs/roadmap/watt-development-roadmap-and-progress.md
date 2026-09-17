# Watt Development Roadmap and Progress Reality

Status: **PROGRAM-LEVEL NAVIGATION / CURRENT REALITY**

Last updated: **2026-09-13**

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

### Watt-native Executor Runtime technical closure

**2026-09-13 — IMPLEMENTATION COMPLETE / TECHNICALLY QUALIFIED / CONTINUITY
QUALIFIED / TECHNICAL PHASE CLOSED.** Q01–Q50 technical requirements are
closed, and Continuity Benchmark v8 passed all 18 A/B pairs and 36 real
executions, including compatible DeepSeek model replacement. Human Product
Acceptance is `DEFERRED_BY_HUMAN_GOVERNANCE` until the later system-wide Human
Journey and UX/UI reconstruction phase; no acceptance is inferred. See the
[final technical closure](../evidence/watt-native-executor-technical-closure.md).

The recommended next program step is **WIC Intelligence Architecture vNext
reconstruction**. Before materially replacing current WIC behavior, preserve a
bounded `OPEN_WIC_BASELINE`; then reconstruct, evaluate through bounded replay
and dogfood, and activate only after evidence supports it. Implementation
requires its own admitted mission.

### New mission: Work-to-Delivery with multiple repositories

**2026-09-10 — Software Artifact Delivery — implemented, automated validation passed, runtime ready.** Adds first-class software delivery, exact source/commit/test evidence, reproducible source packages and an isolated local static-Web runtime adapter. See the [software delivery report](../validation/software-artifact-delivery-slice.md); Human product acceptance remains pending.

**2026-09-10 — Work-to-Delivery first slice: IMPLEMENTED / AUTOMATED VALIDATION PASS / RUNTIME READY / HUMAN PRODUCT ACCEPTANCE PENDING.** Human confirmed multiple repositories in one runtime and clarified that implementation should continue. The [as-built design](../architecture/work-to-delivery-multi-repository-spg-proposal.md) covers repository-scoped baseline/recovery, Work before asset binding, Document Package delivery and explicit Human acceptance. See the [implementation and acceptance report](../validation/work-to-delivery-first-slice.md) for actual evidence and runtime access. Existing closed foundations retain their original scope.

### WIC interaction-intelligence phase closure

**2026-09-17 — CLOSED / PASS WITH PRESERVED HUMAN FINDINGS.** Human Retest
confirmed materially better focus and perceived response speed and judged this
phase useful enough to stop further conversational-intelligence optimization.
One observed syntax-invalid coalesced Provider response is repaired through a
bounded pre-admission attempt. Professional guidance confidence, proactive AI
voice, rich response forms, product-level perceived latency, and TNGA naming
cleanup remain explicit future findings. See the
[closure evidence](../evidence/wic-interaction-intelligence-phase-closure.md).

The next major first-release sequence is **Formal UX/UI implementation**, then
real production/Reality integration and Human Journey dogfood/Acceptance. Each
requires separate authorization; this roadmap update starts none of them.

### Historical collaboration checkpoint


```text
Checkpoint Phase:
    Human–Watt Collaboration Layer Validation

Status:
    IMPLEMENTED
    REAL PROVIDER PROOF PASS
    HUMAN PRODUCT ACCEPTANCE WAS IN PROGRESS
```

This earlier implementation checkpoint proved the product and engineering path
through a real Provider. It is preserved as historical context; the later Human
Retest and current phase result are recorded in the closure section above.

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
| Conversation Intelligence | Current phase CLOSED / PASS WITH PRESERVED HUMAN FINDINGS; WIC/domain semantics, bounded context, governed realization, DeepSeek transport, reusable probe, and Human Retest evidence are preserved without claiming final experience perfection. |
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

### Priority 1 — WIC Intelligence Architecture vNext Reconstruction

**Current Reality: CLOSED / PASS WITH PRESERVED HUMAN FINDINGS.** The external
study, architecture synthesis, bounded `OPEN_WIC_BASELINE`, reconstruction,
controlled activation, automated probe, and Human Retest are complete for this
phase. See the
[WIC Intelligence Architecture Closure](../architecture/watt-wic-intelligence-architecture-closure.md)
and [phase closure evidence](../evidence/wic-interaction-intelligence-phase-closure.md).
No further WIC interaction-quality optimization is active in this phase.

### Priority 2 — External Design Intake Capability

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

### Priority 3 — Human–Watt Collaboration Experience Improvement

Current Reality: the current interaction-intelligence phase is **CLOSED / PASS
WITH PRESERVED HUMAN FINDINGS** after Human Retest and full regression. The
items below are deferred inputs to Formal UX/UI and Conversation Rendering, not
an active additional WIC optimization round.

Focus:

- stronger Design Facilitation behavior;
- clearer conversational experience;
- genuinely incremental streaming where justified;
- proactive guidance that remains inside governed boundaries;
- preservation of Human Authority and reconstructable Interaction Reality.

### Priority 4 — UX/UI Reconstruction

**Next major phase after WIC closure; separate authorization required.** Goal:
transform the current interface into a Human-facing AI collaboration
workspace, not merely restyle the existing screens.

Focus:

- conversation as an understandable collaboration surface;
- visible design path and progress;
- clear current focus and next meaningful decision;
- accessible governed Reality, Attention, and trust basis;
- progressive disclosure rather than dashboard overload.

This priority does not itself authorize a Workspace entity, a new state store,
or duplicated product truth.

### Priority 5 — TNGA to Watt Full Text Migration

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

**Status:** the initial Watt-native continuity, recovery and multi-repository
deepening is technically qualified. Distributed execution, broader capacity
evolution and later integrations remain future work behind the closed native
contracts.

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
future backlog entries. Priorities 1–5 remain unchanged; this is not a new
current priority, MVP scope, or implementation authorization.

External sources remain evidence and design inputs, not Truth. Work, WIC,
Guided Design, Plan Steering, PWU/Executor, SPG, ECF, Guardian, and Human
Authority retain their existing ownership. Future ECF, Executor/PWU, Guardian,
and product/architecture reviews should revisit the
[External Engineering Intelligence Direction](../architecture/external-engineering-intelligence-direction.md),
including its User Story, expected research synthesis, adaptation provenance,
invariants, and explicit non-goals. Internal Reference Engineering is a related
use case, not a substitute for this user-facing product capability.

### 5.10 Autonomous Governed Deployment

**Purpose:** take a governed Delivery into a Human-authorized external runtime
through provider-neutral Deployment Contracts and Adapters, with autonomous
observation, diagnosis, bounded remediation, recovery, and verification.

**Status:** **Phase 2 product direction approved / detailed architecture not
frozen / implementation not authorized / no current-release dependency.** See
[Autonomous Governed Deployment - Phase 2 Product Direction](../product/watt-autonomous-governed-deployment-phase-2.md).
This direction does not reorder the current first-release roadmap or authorize
cloud access, credentials, adapters, runtime changes, or deployment work.
WeChat Mini Program is the first approved representative platform-managed
Deployment Target under this same Phase 2 direction. It confirms that the
Deployment Plane must be non-server-centric, treats platform review as an
external authority gate rather than failure, and preserves compound Mini
Program + backend deployment under one Motive-bound Work. Its Adapter,
credentials, platform connection, upload, review, and release implementation
remain deferred and do not change current priorities.

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
