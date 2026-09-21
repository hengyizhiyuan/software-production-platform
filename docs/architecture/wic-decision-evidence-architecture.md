# WIC Decision and Evidence Architecture

Date: 2026-09-21

Status: **ARCHITECTURE BASELINE / FOUNDATION IMPLEMENTED**. This document
captures distinctions among reasoning summaries, decisions, and evidence. The
bounded immutable contracts and Task Contract lineage are Repository Reality;
they introduce no storage schema, lifecycle service, or new authority.

## Purpose

Reliable software-production intelligence needs to explain what was considered,
what was decided, who had authority, and which evidence supports the result.
Those concerns are related, but they are not interchangeable.

```text
Reasoning Trace
    -> useful summarized rationale and assumptions

Decision Trace
    -> the governed decision and its lifecycle

Evidence
    -> attributable observations or authority supporting evaluation
```

This separation prevents plausible reasoning prose from being mistaken for a
decision, and prevents a decision record from being mistaken for proof that its
outcome is correct.

## Reasoning Trace

Reasoning Trace captures useful reasoning summaries, assumptions, and rationale
needed for review, continuity, or later challenge.

It may retain:

- concise rationale summaries;
- material factors considered;
- explicit assumptions;
- uncertainty that affects the conclusion;
- alternatives considered at a useful level; and
- references to supporting or conflicting evidence.

It must not store or request raw private chain-of-thought. Internal token-level
deliberation, hidden model scratch work, and unrestricted transcripts are not
architectural evidence.

Reasoning Trace is also distinct from Response Contract
`reasoning_sequence`: the sequence governs the order of Human-facing cognition
for one turn, while a Reasoning Trace summarizes durable rationale when a
consumer legitimately needs it. Neither becomes Product Truth by itself.

## Decision Trace

A Decision Trace records the governed outcome of a material decision. Candidate
semantic content includes:

- the decision question;
- considered options;
- the selected decision;
- rationale;
- decision authority;
- evidence references; and
- lifecycle status.

For example, a Decision Trace could explain why a particular authentication
architecture was selected, which alternatives were considered, which Human or
system authority admitted the choice, which facts supported it, and whether the
decision is current, superseded, or pending review.

This is a conceptual record, not a frozen schema. Concrete identity, lifecycle,
granularity, ownership, storage, and reconciliation require a separately
authorized design.

Decision Trace does not replace:

- Engineering Semantic Truth for current governed meaning;
- Human Decision Records for explicit authority actions;
- Steering for the formal next Work step;
- Git for code history;
- Guardian for Assurance Evidence; or
- SPG for production-governance state.

## Evidence categories

Evidence remains attributable to its owning source and authority domain.

### Human Evidence

Examples:

- approval;
- correction; and
- acceptance.

Human Evidence records what the Human explicitly authorized, changed, or
accepted. It must retain identity, scope, and the subject to which it applies.

### Engineering Evidence

Examples:

- test results;
- Runtime observations; and
- Repository facts.

Engineering Evidence supports claims about actual implementation or behavior.
Generated explanation is not a substitute for an observed result.

### Assurance Evidence

Examples:

- Guardian verification;
- findings; and
- gates.

Guardian retains Assurance Evidence authority. A WIC summary may reference
Guardian evidence, but cannot manufacture a PASS, dismiss a finding, or bypass
an assurance gate.

## Evidence is not authority by itself

Evidence supports a conclusion; authority determines who may admit a decision
or transition. A passing test may support a delivery decision but cannot accept
delivery on behalf of the Human. A Human preference may be authoritative for a
product choice but does not prove Runtime behavior. A Pattern may suggest a
risk, but the suggestion is not current project evidence until grounded in
relevant Reality.

Preserving these distinctions supports later challenge and supersession without
rewriting history.

## Relationship with ECF

ECF may contain or project:

- Reality;
- Semantic Facts;
- Decision Memory; and
- Evidence references.

ECF remains responsible for context projection, provenance, and freshness; it
does not acquire decision or assurance authority merely by carrying references.
See [ECF Integration](../context/ecf-integration.md) and
[Program Architecture Decisions](program-architecture-decisions.md).

Domain Patterns remain separate from ECF-held project context and Decision
Memory. Project truth and general engineering experience must not contaminate
each other:

- project facts must not silently become universal Pattern guidance;
- Pattern guidance must not silently become current project truth; and
- historical applicability conditions must remain attributable.

The Context Orchestrator may assemble ECF Reality, Decision Memory, evidence
references, and relevant Domain Patterns for a current task, while preserving
these ownership and authority boundaries.

## Lifecycle and history

Decision and evidence history should be additive where practical. A later
correction or stronger observation may supersede an earlier conclusion without
mutating the original rationale or evidence in place. Current projections may
select the active decision, while historical traces remain available for audit,
learning, and conflict explanation.

This direction does not prescribe Event Sourcing, a graph database, a universal
Evidence ontology, or one shared lifecycle for all evidence categories.

## Current capability, direction, and future work

Current capability:

- Engineering Semantic Truth already preserves authority, provenance, and
  supersession for governed semantic facts;
- bounded Reasoning Summary and Decision Trace contracts preserve useful
  rationale, considered options, selected direction, authority, and status;
- Human, Engineering, and Assurance evidence references retain source, subject,
  basis, assertion, and authority domain inside the PWU Task Contract; and
- existing Human, Repository, Runtime, Verification, and Guardian boundaries
  remain authoritative in their own domains.

Architecture direction captured here:

- Reasoning Trace as summarized rationale rather than raw chain-of-thought;
- Decision Trace semantics;
- evidence categories and authority separation; and
- ECF and Domain Pattern separation.

Future exploration:

- concrete ownership, contracts, retention, reconciliation, lifecycle states,
  projections, and evaluation.

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

The foundation creates no database table, API, Decision Memory service,
evidence store, automated raw reasoning capture, or Guardian authority change.
