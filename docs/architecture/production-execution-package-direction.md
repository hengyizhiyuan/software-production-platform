# Watt Production Execution Package / Production Passport Direction

## 1. Status and authority

```text
Production Execution Package / Production Passport
    FUTURE HIGH PRIORITY CAPABILITY

Implementation
    NOT STARTED

Current Scope
    NOT MVP IMPLEMENTATION
```

This document records a future architecture direction only. It does not
authorize implementation of Production Execution Package Lite, Production
Passport, Watt Native Context Assembly, or ECF.

The direction follows the existing ownership boundaries in the
[SPG FVS-1 Implementation Contract](spg-fvs-1-implementation-contract.md) and
the Human-facing projection boundary established by the
[Control Room Slice 3 Contract](software-production-control-room-slice-3-implementation-contract.md).

## 2. Problem definition

AI-native software production requires a reconstructable production history.
A trusted result is not explained by an output artifact alone: its intent,
governed production state, plan, bounded production unit, admitted context,
execution, verification, and resulting Runtime Reality must remain
traceable as a coherent lineage.

Current challenges include:

- reproducing a governed production process across different models or
  providers;
- analyzing failures when the relevant context and production lineage are
  incomplete or scattered;
- accumulating reusable software-production knowledge from successful and
  unsuccessful production events.

## 3. Core concept

A Production Execution Package is a structured production record. Its future
purpose is to connect the governed facts required to reconstruct a production
event, including:

- Human Intent;
- Work Reality;
- Plan;
- Production Work Unit (PWU);
- Production Contract;
- Context Basis;
- Execution Envelope;
- Executor Attempt;
- Produced Artifact;
- Verification Evidence;
- Runtime Reality.

The package records references, relationships, and lineage among facts owned
by their existing authoritative capabilities. It does not become the
authoritative owner of those facts and does not rewrite their semantics.

A Production Execution Package is not:

- a prompt;
- a chat transcript;
- a replacement for Work;
- a replacement for PWU;
- a replacement for Materialized Execution Input (MEI).

MEI remains the exact provider-neutral execution input bound for an Attempt.
The Production Execution Package direction addresses the broader,
reconstructable lineage of the governed production event.

## 4. Strategic value

### A. Provider and model independence

A sufficiently complete production package should allow a different
compatible AI provider or model to understand the same governed production
basis and reproduce or analyze the production process without depending on
the original model session.

This is a direction for reproducibility and portability. It does not promise
identical model output or transfer production authority to a Provider.

### B. Failure analysis

A complete production lineage should support future AI-assisted analysis of:

- intent misunderstanding;
- missing or stale context;
- production-contract issues;
- execution deviation;
- verification gaps;
- Runtime issues.

Such analysis must remain evidence-based. The package connects the relevant
facts; it does not manufacture missing evidence or replace Human,
Verification, or Runtime authority.

### C. Engineering data asset

Over time, governed production history may form an engineering data asset
containing:

- successful production patterns;
- failure patterns;
- verification patterns;
- architecture patterns;
- production-economics data.

This is a future strategic value direction, not a current analytics,
benchmarking, or optimization capability.

## 5. Relationship with existing Watt architecture

Production Execution Package does not replace:

- Work, which represents the current governed Work Reality;
- PWU, which remains the bounded production unit;
- MEI, which remains the exact materialized input for an Executor Attempt;
- Completion Contract, which defines the admitted completion obligations;
- Verification, which remains the authority for verification results and
  evidence.

It records and connects production facts across their existing lineage.
WIC, Plan Steering, SPG, Executor, Verification, repository integration, and
Runtime retain their current responsibilities and sources of truth.

The Control Room may later project a package or passport for Human
understanding, but it remains a projection layer and does not own the
underlying production history.

## 6. Relationship with future ECF

Future ECF provides governed context capabilities such as:

- Context discovery;
- Context assembly;
- Context freshness;
- Context provenance.

Production Execution Package records the context basis used by a production
event together with its execution and outcome lineage.

```text
Future ECF
    Context capability provider
        |
        v
Production Execution Package
    reconstructable production history
```

The relationship does not make the package an ECF replacement. ECF retains
authority over Context Projection semantics, while the package records the
exact context relationship relevant to the production event.

## 7. Planned evolution

```text
Control Room
    |
    v
Production Execution Package Lite
    |
    v
Watt Native Context Assembly
    |
    v
Real Dogfood
    |
    v
Full Production Passport
```

Every stage in this sequence is future work requiring separate architecture,
scope, implementation authority, and evidence. The sequence is directional;
it is not a current implementation commitment.

## 8. Explicit non-goals

This record does not introduce or authorize:

- a database model or migration;
- an API;
- Runtime behavior;
- Production Execution Package Lite implementation;
- Production Passport implementation;
- Watt Native Context Assembly implementation;
- ECF implementation;
- a new source of truth or lifecycle owner.
