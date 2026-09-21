# WIC Software Domain Grounding

Date: 2026-09-21

Status: **ARCHITECTURE BASELINE / FOUNDATION IMPLEMENTED**. The minimum
Engineering Pattern representation and structured activation/consumption seam
are Repository Reality. Persistence, management tooling, Pattern evolution, and
organizational catalog governance remain future work.

## Purpose

Software Domain Grounding provides reusable engineering cognitive structures
that help Watt recognize relevant software-engineering considerations,
patterns, trade-offs, failure modes, and decision dimensions.

It improves the quality and consistency of what Watt notices when interpreting,
exploring, reviewing, or deciding. It is not:

- a traditional knowledge base;
- a document-retrieval system;
- a simple retrieval-augmented generation layer;
- a rule engine; or
- a replacement for Human judgment.

Domain Grounding is positioned after the implemented
[WIC Response Contract](wic-response-contract.md) and alongside the bounded
Software Production SOP foundation. Response Contract governs what kind of collaboration
the current turn requires. Domain Grounding may supply relevant engineering
frames. A future SOP may govern production sufficiency and progression. None of
these layers owns Engineering Semantic Truth or Steering.

## Engineering Pattern

An **Engineering Pattern** is:

> A reusable engineering cognitive framework organized around a software
> engineering decision space.

A Pattern is not a document, fixed workflow, implementation recipe, or
mandatory rule. It does not tell Watt to reproduce one solution. Instead, it
helps Watt direct attention toward material considerations and reason within a
recognizable decision space.

A Pattern may provide:

- attention guidance: what an engineer should notice;
- decision dimensions: which distinctions materially affect the outcome;
- possible options: credible directions worth considering;
- trade-off awareness: what improves or degrades under each direction; and
- failure awareness: recurring ways the decision can go wrong.

Pattern use should remain proportional to the current Response Contract and
Context Budget. Activating a relevant Pattern is not a requirement to expose
all of its content to the Human.

## Conceptual knowledge layers

The current architecture direction distinguishes four related layers. These are
conceptual responsibilities, not a required storage hierarchy.

### 1. Concept Knowledge

Answers: **What is this?**

Examples include OAuth, JWT, PostgreSQL, and Kubernetes. Concept Knowledge
supports accurate terminology and mechanism understanding, but does not by
itself frame an engineering decision.

### 2. Engineering Pattern

Answers: **What should an engineer consider?**

For example, an Authentication Capability Design Pattern could surface identity
boundaries, account recovery, session lifetime, abuse resistance, integration
cost, and user experience without prescribing one authentication stack.

### 3. Decision Framework

Answers: **How should alternatives be evaluated?**

A Decision Framework makes evaluation dimensions and material trade-offs
explicit for the current goals and constraints. It supports judgment; it does
not own the final decision or its authority.

### 4. Failure Memory

Answers: **What has repeatedly gone wrong before?**

Failure Memory preserves attributable lessons, failed assumptions, and
conditions under which a prior approach was unsafe or ineffective. It informs
attention and challenge without turning one historical failure into a universal
prohibition.

## Candidate Pattern structure

The candidate core structure is:

- **Identity** — the decision space the Pattern addresses;
- **Activation** — evidence or conditions indicating possible relevance;
- **Mental Model** — the useful conceptual frame;
- **Dimensions** — material aspects to inspect or compare;
- **Options** — credible alternative directions;
- **Trade-offs** — consequences and tensions among options; and
- **Evidence** — attributable support and applicability conditions.

Possible future metadata includes:

- Failure Modes;
- Relations to other Patterns;
- Confidence;
- Evolution history; and
- Organization variants.

This is an architectural direction, not a frozen implementation schema. It does
not select a database model, serialization format, graph representation,
retrieval strategy, provider interface, or authoring workflow.

## Authority boundary

Patterns provide engineering awareness, candidate considerations, and decision
support. They do not:

- override explicit Human intent;
- override current [Engineering Semantic Truth](engineering-semantic-truth.md);
- silently change Work Reality;
- directly authorize execution;
- select the formal next Work step; or
- become Production Policy.

The governing principle is:

> Pattern constrains reasoning space, not Human expression space.

Human expression remains free-form. When a Pattern conflicts with higher
authority, it may surface a risk or question, but it cannot replace that
authority. Pattern-derived suggestions retain their source and epistemic status;
they do not become project facts merely because a Pattern supplied them.

## Relationship to adjacent capabilities

| Capability | Responsibility | Domain Grounding boundary |
|---|---|---|
| Engineering Semantic Truth | Durable governed meaning for the current Work | Patterns consume current truth and cannot rewrite it |
| Response Contract | Turn-scoped collaboration and answer shape | Determines how much Pattern contribution is useful now |
| Context Orchestrator | Selects and budgets relevant current context | May select Pattern material without making it truth |
| Decision Intelligence | Makes or supports bounded judgments under authority | May use Pattern dimensions and attributable evidence |
| Software Production SOP | Future sufficiency and progression policy | May reference Patterns but remains a separate future layer |
| Steering | Formal `WHAT NEXT` for the Work | Cannot be bypassed by Pattern activation |
| ECF | Context Reality, projection, freshness, and provenance | Remains separate from the general Pattern domain |

## Current capability, direction, and future work

Current capability:

- immutable Pattern identity, activation metadata, dimensions, options,
  trade-offs, evidence direction, and provenance;
- structured activation by Engineering Activity and governed semantic shape;
- Context Orchestrator consumption under a bounded budget; and
- Response Contract v2 and Engineering Semantic Truth inputs whose authority
  boundaries remain preserved.

Architecture direction captured here:

- Engineering Pattern semantics;
- conceptual knowledge layers;
- candidate Pattern structure; and
- authority and integration boundaries.

Future exploration:

- representation, activation, retrieval, authoring, governance, evaluation,
  organizational variation, and evolution mechanisms.

## Explicit non-goals

```text
NOT_IMPLEMENTED:
- Pattern Studio
- Pattern management UI
- Pattern Evolution engine
- Benchmark / WIC Evaluation Corpus
- Automated knowledge mining
- Full Software Production SOP
```

The foundation adds no persistence schema, API, Provider-specific behavior,
Pattern management product, benchmark infrastructure, or production authority.
