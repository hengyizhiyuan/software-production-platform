# Watt Decision and Evidence Architecture

Date: 2026-09-21

Status: **ARCHITECTURE BASELINE / FOUNDATION IMPLEMENTED**. This document
defines Watt-wide responsibility and lineage boundaries. It does not create a
Decision Store, Evidence Store, schema, service, or automated reasoning capture.

## Purpose

Watt must preserve enough rationale, decision authority, and evidence lineage
to support continuity, challenge, verification, supersession, and audit. These
concerns must remain distinct:

```text
Reasoning Summary
    -> useful rationale

Decision Trace
    -> governed choice and authority

Evidence
    -> attributable support or contradiction
```

A fluent explanation is not a decision. A decision is not proof. Evidence does
not grant authority by itself.

## Reasoning Summary

A Reasoning Summary captures useful rationale at the level required for Human
review or engineering continuity. It may include:

- material factors considered;
- assumptions;
- uncertainty;
- relevant alternatives; and
- a concise explanation of the recommendation or conclusion.

Do not store raw chain-of-thought, hidden model scratch work, or unrestricted
token-level deliberation. Where durable rationale is justified, store a bounded
summary whose claims remain attributable to evidence and current Reality.

Reasoning Summary is distinct from Response Contract Reasoning Sequence. The
former summarizes material rationale; the latter controls the presentation
order for one Human-facing turn.

## Decision Trace

A Decision Trace records:

- the decision question;
- considered options;
- the selected decision;
- rationale;
- authority;
- evidence references; and
- lifecycle status.

A trace should make it possible to understand what was decided, why, by whom or
under which authority, on which evidence, and whether the decision remains
current. A later correction or stronger decision supersedes the old trace where
appropriate without rewriting historical evidence in place.

Decision Trace does not replace Engineering Semantic Truth, Human Decision
Records, Steering, Work Reality, Git history, SPG Production State, or Guardian
Assurance Evidence.

## Evidence

Evidence retains its source, subject, revision or time basis, scope, and
authority domain.

### Human Evidence

Examples:

- approval;
- correction; and
- acceptance.

Human Evidence establishes what the Human explicitly decided or accepted. It
does not by itself prove implementation behavior.

### Engineering Evidence

Examples:

- tests;
- Runtime observations; and
- Repository facts.

Engineering Evidence supports claims about what was implemented or observed.
Generated prose and intended behavior are not substitutes for observations.

### Assurance Evidence

Examples:

- Guardian verification;
- findings; and
- gates.

Guardian owns Assurance Evidence semantics. Other layers may reference the
evidence but cannot manufacture a PASS, dismiss a finding, or bypass a gate.

## Authority and evidence

Evidence supports evaluation; authority governs admission and progression.

- a passing test may support delivery but cannot accept it for the Human;
- a Human preference may govern a product choice but cannot prove Runtime
  correctness;
- a Pattern may surface a risk but is not project evidence until grounded in
  current Reality; and
- an AI recommendation may cite evidence but does not become Production
  Authority.

The core principle is:

> AI Intelligence != Production Authority.

## Cross-layer ownership

| Concern | Owner or authority | Boundary |
|---|---|---|
| Explicit Human decisions | Human Governance | Scope-specific authority, not Engineering proof |
| Engineering Semantic Truth | Semantic Truth capability | Current governed meaning and supersession |
| Work and Production Reality | Work/SPG domains | Current lifecycle facts |
| Decision support | Decision Intelligence | Recommendation and rationale, not automatic admission |
| Formal next Work action | Steering | Operates within admitted authority |
| Execution records | PWU/Executor | Execution lifecycle and produced artifacts |
| Repository history | Git / Repository Reality | Code and revision evidence |
| Assurance Evidence | Guardian | Assurance findings, confidence, and gates |
| Context projection | ECF | Projection, provenance, and freshness, not source ownership |

## ECF and Domain Pattern separation

ECF may project Reality, Semantic Facts, Decision Reality, and Evidence
references while preserving their source ownership. General Engineering
Patterns remain separate from project-specific context.

Project truth and general engineering experience must not contaminate each
other:

- project facts do not silently become universal Pattern guidance;
- Pattern guidance does not silently become current project truth; and
- a historical decision remains bounded by its original applicability and
  lifecycle status.

See [WIC Decision and Evidence Architecture](wic-decision-evidence-architecture.md)
for the WIC-specific context and
[WIC Software Domain Grounding](wic-software-domain-grounding.md) for the Pattern
boundary.

## Task and PWU lineage direction

Future Task Contracts and their PWUs should preserve:

- SOP lineage;
- Task Contract lineage;
- Decision lineage; and
- Evidence lineage.

Lineage links the exact governed basis used for execution and verification. It
does not imply that all referenced inputs remain current, nor does it promote a
Reasoning Summary or Pattern into authority.

## Lifecycle principles

- Preserve historical rationale and evidence rather than mutating it in place.
- Project the current decision separately from historical alternatives.
- Mark supersession explicitly where a newer authoritative decision conflicts.
- Treat stale, incomplete, or contradictory evidence as a visible condition.
- Keep Human Acceptance separate from Verification and Assurance.
- Avoid one universal lifecycle when evidence categories have different owners.

These principles do not require Event Sourcing, a graph database, or a universal
Evidence ontology.

## Current capability and future direction

Current Repository Reality already contains governed semantic facts,
provenance, supersession, Human decisions, production lineage, test/runtime
observations, and Guardian integration boundaries in their respective domains.

Immutable `ReasoningSummary`, `DecisionTrace`, and attributable Human,
Engineering, and Assurance `EvidenceReference` contracts now preserve bounded
lineage inside the PWU Task Contract. They intentionally do not store raw
chain-of-thought or create new authority. A general Decision/Evidence store,
retention policy, projections, and lifecycle services remain future work.

## Explicit non-goals

```text
NOT_IMPLEMENTED:
- Pattern Studio
- Pattern management UI
- Pattern Evolution engine
- WIC Evaluation Corpus
- Benchmark infrastructure
- Full Software Production SOP runtime
- Automated knowledge mining
- Decision Store or Evidence Store
```

The foundation projects existing authority and evidence lineage into the Task
Contract consumed by PWU execution and verification. It does not transfer
ownership among Guardian, ECF, Steering, PWU, or Executor.
