# External Design Intake Capability Direction

Status: **FUTURE HIGH PRIORITY CAPABILITY**

Implementation: **NOT STARTED**

Document role: **ARCHITECTURE DIRECTION MEMO**

This document records the intended purpose, responsibility boundaries, and
future architectural relationships of External Design Intake. It does not
authorize implementation, introduce a new Truth source, or change the current
Guided Design lifecycle.

## 1. Capability Purpose

External Design Intake allows a Human to bring existing design assets into
Watt as attributable inputs to a governed design process.

Representative assets include:

- product requirement documents (PRDs);
- product and business documents;
- prototypes and interaction descriptions;
- design files and exported design representations;
- architecture documents;
- API specifications.

The goal is to transform existing design assets into **governed design inputs**.
The capability must preserve the difference between what an external artifact
says, what an AI interprets from it, and what the Human ultimately admits as
Design Reality.

In the Work-centric production model, this capability is **Work Asset Intake**,
not Project import. Before Work admission, an external artifact remains
Interaction provenance or candidate input. Once a Work exists, an admitted
relationship makes it a Work Asset:

```text
External Design Artifact
    -> attributable candidate input
    -> Work admission / asset relationship admission
    -> Work Asset used by Guided Design
```

## 2. Core Principle

External Design Intake is not:

- generic file upload;
- document summarization;
- direct code generation.

Its intended flow is:

```text
External Design Artifact
    -> Artifact Interpretation
    -> Design Candidate Reality
    -> Guided Design
    -> Governed Design Reality
    -> Production Readiness
```

An uploaded or connected artifact is not automatically a design decision. An AI
interpretation is not automatically accepted Design Reality. Production
Readiness may be evaluated only after relevant interpretations, questions,
conflicts, and Human decisions have passed through the governed Guided Design
process.

## 3. Relationship With Guided Design

External Design Intake is an **input adapter for Guided Design**. It does not
create a second design system, parallel design lifecycle, or independent design
authority.

```text
External Artifact
    -> Guided Design Process
    -> Design Reality
```

[Guided Design Core](guided-design-core.md) remains responsible for the design
agenda, stage, focus, progress, readiness, and reconstructable Design Reality.
[Guided Design Facilitation](guided-design-facilitation-layer.md) remains
responsible for helping the Human understand and advance that process.

External Design Intake supplies attributable candidate material to those
capabilities. It does not decide which interpretation is correct, silently
resolve material ambiguity, or admit the result on behalf of the Human.

## 4. Provenance Model

The future provenance chain must preserve three distinct layers:

```text
Original Artifact
    -> AI Interpretation Candidate
    -> Governed Design Result
```

### Original Artifact

The original external item and its available identity, source, version,
location, and observation time should remain attributable. The artifact is an
evidence or input source, not an authoritative Watt Truth source.

### AI Interpretation Candidate

Extracted meaning is a candidate interpretation. It should remain traceable to
the relevant original material and expose uncertainty, assumptions, omissions,
and possible conflicts. It must not overwrite or masquerade as the source.

### Governed Design Result

Only the outcome admitted through Guided Design and the applicable Human
Authority boundary becomes governed Design Reality. The admitted result may
accept, refine, reject, or qualify the interpretation candidate.

This separation enables Watt to answer:

- which external artifact contributed this information;
- what the AI inferred rather than directly observed;
- what the Human reviewed or decided;
- which governed design result is currently authoritative.

## 5. Future Capability Scope

The following areas describe possible future scope. They are not current
implementation commitments.

### 5.1 Artifact Intake

Initial format directions may include:

- Markdown;
- PDF;
- DOCX;
- images;
- design exports.

Later connector directions may include:

- Figma;
- Axure;
- Jira;
- Confluence.

Format or connector support must preserve source identity and provenance. A
connector must not acquire design authority merely because it can retrieve an
artifact.

### 5.2 Artifact Interpretation

Interpretation may extract candidate information such as:

- intent;
- users and beneficiaries;
- scenarios and journeys;
- capabilities;
- constraints;
- assumptions.

Extraction results should identify their source basis and distinguish explicit
content from AI inference. Missing or ambiguous information should remain
visible rather than being silently completed.

### 5.3 Design Coverage Analysis

Watt may compare interpreted material with the applicable Design Schema to
identify:

- covered design areas;
- missing areas;
- unresolved questions;
- unsupported assumptions;
- areas requiring Human judgment.

Coverage is a navigation and facilitation aid. It is not automatic design
approval and must not turn schema completion into a substitute for product
quality.

### 5.4 Conflict Detection

Different external artifacts may disagree without containing textual
conflicts. For example:

```text
PRD:
    supports feature A

Prototype:
    does not contain feature A

API specification:
    does not support feature A
```

The system should surface the conflict, its source artifacts, and its likely
design impact for Human review. It must not silently choose a winner or rewrite
the governed design direction. Material conflict resolution remains a Human or
otherwise explicitly authorized design decision.

## 6. Explicit Non-goals

External Design Intake does not include or authorize:

- automatic code generation from design files;
- a Figma clone or general-purpose design editor;
- automatic approval of design correctness;
- replacement of Human judgment or Authority;
- full Engineering Context Fabric (ECF);
- Production Passport implementation.

It also does not introduce a new Work, Guided Design, Plan, production, or
evidence Truth owner.

## 7. Relationship With Future Architecture

External Design Intake benefits from several existing and future capabilities:

- **Guided Design Facilitation** helps the Human understand coverage,
  ambiguity, conflict, and the next valuable design focus;
- **Design Schema** provides the structured design areas against which
  interpreted material can be organized and assessed;
- future **ECF** may provide source discovery, freshness, provenance, and
  decision-scoped context assembly;
- future **Production Execution Package** may record which governed design
  inputs and results formed the context basis of a production event.

See [ECF Integration](../context/ecf-integration.md) and
[Production Execution Package Direction](production-execution-package-direction.md).

External Design Intake should not be implemented before Guided Design behavior
is stable enough to receive, question, reconcile, and govern the resulting
candidate material. Adding more input before the facilitation and Authority
boundaries are reliable would increase ambiguity rather than create trustworthy
Design Reality.

## 8. Formal UX/UI reference-asset dogfood requirement

Formal UX/UI Phase 1 established a concrete future dogfood set for this
capability. Six exact Human-approved Workspace visual references remain in the
[Workspace Skin asset manifest](../assets/ui-skins/README.md). Industrial Cyan
is the only current manually reconstructed production skin. The other five are
preserved as `FUTURE_EXTERNAL_ASSET_DOGFOOD` rather than manually approximated
or exposed as unfinished product options.

The future capability should be able to consume sources such as Figma,
structured UI assets, external design packages, design systems, design tokens,
or component libraries through a governed loop:

```text
External Design Source
    → Design Reality / Versioned Baseline
    → Structured Design Context
    → Watt Production
    → Browser Render
    → Visual Comparison
    → Iterative Correction
    → Human Acceptance
```

This is a high-value product and internal dogfood requirement, not current
implementation authorization. The preserved references are evidence inputs;
they do not become executable Truth or bypass Human acceptance.

## 9. Current Status

```text
External Design Intake Capability

Status:
    FUTURE HIGH PRIORITY CAPABILITY

Implementation:
    NOT STARTED
```

Current authorized action is documentation only. A future implementation
requires a separate bounded architecture contract, explicit source and
provenance semantics, Human Authority rules, acceptance scenarios, and
implementation authorization.
