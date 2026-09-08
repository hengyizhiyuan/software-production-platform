# Watt Development Roadmap and Progress Reality

Status: **PROGRAM-LEVEL NAVIGATION / CURRENT REALITY**

Last updated: **2026-09-08**

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
| Async Interaction Processing | Bounded asynchronous Turn processing and durable terminal outcome projection are implemented. |
| Conversation history | Human and Watt messages remain reconstructable without turning conversation into governed Work Truth. |
| Real Provider validation | The mandatory Chinese product-design scenario completed with `gpt-5.6-sol`; schema matching and Guided Design facilitation were reached with sanitized evidence. |

Detailed evidence is recorded in
[Human–Watt Collaboration Layer Focused Validation](../evidence/human-watt-collaboration-layer-focused-validation.md).

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

Current calibration status: **IMPLEMENTED / FOCUSED VALIDATION PASS / HUMAN
ACCEPTANCE PENDING**. The implementation now supplies the ordered Design Schema
to the Provider, requires path/stage/focus explanation and proactive bounded
guidance, reuses known Interaction Reality, and projects the full design route
in the persisted Watt response. This status does not yet claim that the Human
experience is accepted.

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

Current calibration status: **IMPLEMENTED / FOCUSED VALIDATION PASS / REAL
PROVIDER V2 PROOF PASS / HUMAN ACCEPTANCE PENDING**. The Codex adapter now
consumes real agent-message deltas and SSE exposes only incremental
Human-facing response content while the Turn is processing. The terminal
message remains the durable conversation record; process-local deltas are
bounded UX state.

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
without losing the encompassing Work direction.

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
