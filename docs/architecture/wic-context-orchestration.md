# WIC Context Orchestration

Date: 2026-09-21

Status: **ARCHITECTURE BASELINE / FOUNDATION IMPLEMENTED**. This document
defines the WIC context-selection boundary now used by governed response and
Task Contract assembly. It does not redesign ECF or add a retrieval index,
separate persistence layer, or production workflow.

## Definition

A **Context Orchestrator** is:

> A cognitive context selection layer responsible for selecting,
> prioritizing, trimming, and assembling the information required for the
> current Human interaction and engineering task.

Its job is not to maximize supplied context. Its job is to assemble the minimum
sufficient, authoritative, and relevant context for the current cognitive and
engineering obligation.

## ECF boundary

The distinction is:

```text
ECF
    -> What exists?

Context Orchestrator
    -> What is needed now?
```

ECF retains Context Reality, source provenance, freshness, synchronization, and
authoritative Context Projection semantics as described by
[ECF Integration](../context/ecf-integration.md). The Context Orchestrator may
consume an ECF projection alongside other governed sources, but it does not
become ECF or redefine what exists.

This WIC-level selection responsibility also does not transfer ECF's existing
least-context responsibility. ECF may minimize an ECF-owned projection for a
consumer; the Context Orchestrator composes the current interaction/task context
across multiple capability-owned sources. The two boundaries can cooperate
without merging ownership.

## Candidate context sources

Depending on the current obligation, context may be selected from:

- **Response Contract** — interaction mode, obligation, reasoning sequence,
  information budget, and question budget;
- **System Capability Reality** — repository-versioned Watt identity, currently
  implemented production capabilities, evidence requirements, and authority
  boundaries;
- **Engineering Semantic Truth** — current facts, authority, epistemic state,
  provenance, and supersession;
- **ECF Reality** — governed context projections, source lineage, and freshness;
- **Repository Reality** — exact source, configuration, dependency, and history
  observations;
- **Runtime Reality** — execution, queue, deployment, health, and observed
  behavior;
- **Decision Memory** — prior decisions, rationale, authority, status, and
  evidence references;
- **Domain Grounding** — relevant Engineering Patterns, decision dimensions,
  trade-offs, and failure awareness;
- **Software Production SOP** — future progression and sufficiency policy; and
- **Guardian Evidence** — assurance findings, verification evidence, and gates.

Listing a source does not grant WIC ownership of it. Every selected item retains
its authority, provenance, freshness, and lifecycle semantics.

### System Capability Reality boundary

System Capability Reality is the governed source for questions such as “你是谁”
or “你能做什么”. It describes Watt as an AI-native software production system
that can understand intent and constraints, reason about repositories and
architecture, produce or modify software artifacts, execute within bounded
authority, verify results, and preserve Work, decision, and evidence lineage.

It is neither marketing copy nor a model personality prompt. Its claims remain
versioned and attributable to repository capability, and its projection must
carry the relevant limits: it cannot claim deployment, messaging, external
side effects, or other execution without an available integration, sufficient
authority, and evidence. Selecting this source does not admit Work or promote a
capability description into Product Truth.

Response Contract may also require this source when its Capability Alignment
Context classifies the turn as production advisory or production. Knowledge
Mode does not use a merely technical topic as a reason to promote Watt. The
selection supplies an accurate boundary to the Realizer; it does not grant
Work, Steering, or Executor authority.

## Priority and conflict handling

The current context-priority principle is:

```text
Human Explicit Truth
        ↓
Current Engineering Reality
        ↓
Historical Decisions
        ↓
Domain Patterns
        ↓
General Knowledge
```

Higher-level Reality cannot be silently overridden by lower-level suggestions.
For example:

- a Pattern cannot replace an explicit Human correction;
- a historical decision cannot override newer Repository or Runtime Reality;
- general model knowledge cannot contradict the current governed Work; and
- a Response Contract cannot promote selected context into Product Truth.

Priority does not mean lower layers are ignored. They may identify a conflict,
surface a risk, or support a recommendation, but their contribution must remain
clearly attributable and subordinate to current authority.

## Context Budget

More context does not necessarily produce better reasoning. Unbounded context
can hide decisive evidence, reintroduce superseded facts, increase latency, and
encourage irrelevant explanation.

Context assembly should optimize:

- **relevance** — material to the current obligation;
- **sufficiency** — enough to reason and act safely within current authority;
- **latency** — no unnecessary retrieval or projection work; and
- **cognitive clarity** — decisive facts and conflicts remain visible.

Avoid context dumping. The selected context should be explainable in terms of
the current Response Contract, Work step, decision question, or verification
need. Omitted context remains available at its owning source; omission does not
delete or supersede it.

## Selection responsibilities

The future Context Orchestrator may be responsible for:

- identifying the active interaction or engineering obligation;
- locating candidate sources without bypassing their access boundaries;
- ranking current, authoritative, and relevant material;
- excluding stale, superseded, duplicate, or immaterial material;
- preserving source identity and epistemic status;
- fitting the result to a bounded Context Budget; and
- exposing material gaps or conflicts instead of fabricating continuity.

It must not:

- reinterpret settled Engineering Semantic Truth;
- mutate source systems through context assembly;
- convert conversation history into execution authority;
- grant Human or system authority;
- choose the formal Steering transition; or
- turn Domain Patterns into project facts or Production Policy.

## Relationship to Response Contract

Response Contract answers what kind of Human collaboration the current turn
requires. Context Orchestration answers which governed information is needed to
satisfy that obligation. For example, STATUS should prioritize current Work and
Runtime Reality, while DESIGN_EXPLORE may admit relevant Domain Patterns and
decision dimensions within a larger information budget.

The relationship is directional but not authoritative:

```text
Response obligation
    -> context selection and budget
    -> governed realization or engineering consumer
```

The selected package does not become truth merely because it was assembled.

## Current capability, direction, and future work

Current capability:

- bounded native context assembly and existing ECF integration seams;
- repository-versioned System Capability Reality for identity and capability
  questions;
- Response Contract v2 budgets and Engineering Semantic Truth projections;
- cross-source candidate selection with explicit priority and source authority;
- structured Pattern and SOP contribution without truth promotion; and
- bounded cognitive context packages consumed by governed response and Task
  Contract assembly.

Architecture direction captured here:

- cross-source selection responsibility;
- ECF separation;
- priority and conflict rules; and
- minimum-sufficient Context Budget.

Future exploration:

- concrete ports, selection algorithms, freshness protocols, observability,
  compaction, caching, and evaluation.

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

The implemented foundation creates no separate Context Orchestrator service,
schema, retrieval index, RAG pipeline, or ECF implementation. General retrieval,
freshness, caching, compaction, and evaluation remain future work.
