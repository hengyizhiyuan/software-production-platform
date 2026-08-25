# Program-level Architecture Decisions

This document records program-level architecture decisions and strategic boundaries. It is a living decision record; future directions described here are not current implementation capabilities.


## Decision Intelligence Terminology and Product Boundary

The Decision Intelligence domain is layered as follows:

```text
Decision Intelligence Domain
        ↓
Decision Intelligence Capability
        ↓
Decision Intelligence Provider
        ↓
Provider Implementation
```

YiJue is a Consumer Product / Application and one possible Decision Intelligence Capability Provider. It is not the Decision Intelligence Platform Capability, Enterprise Decision Infrastructure, or a Software Production Platform component.

YiJue owns its Consumer Product Experience, Decision Room Experience, Consumer Runtime, product-specific Policy, product-specific Business Logic, and User Interaction Model.

The Decision Intelligence Capability is the reusable abstraction that transforms incomplete intent and complex context into structured, explainable, and accountable Decision Artifacts. A provider may be implemented by a lightweight LLM-based adapter, YiJue Decision Engine, Enterprise Decision Engine, or Third-party Decision Provider.

Decision Artifact semantics belong to the Decision Intelligence Domain. YiJue produces Decision Artifact instances as one product implementation; it does not own the domain model for all consumers.

## Software Production Governor (SPG) Positioning

**SPG is not an AI brain.**

SPG is the **Software Production Governor**: an intelligence orchestration and software production governance layer.

In Chinese:

> 软件生产治理层，通过组织智能能力、编排生产流程、维护生产状态和驱动持续迭代，实现 AI 原生软件生产。

SPG is responsible for:

- Production Intent Interpretation
- Production Planning
- Workflow Orchestration
- Production State Management
- Execution Coordination
- Production Control Loop
- Production Pattern Evolution — Future Capability

SPG is not responsible for:

- General-purpose Decision Intelligence
- Enterprise-level judgment capability
- Business value judgment

## SPG Lite Domain and Contract Boundary Decision

The accepted minimum SPG domain-object and capability-contract model is consolidated in [SPG Lite Domain Model and Contract Boundary Baseline](spg-lite-domain-contract-baseline.md).

The decision fixes the following boundaries:

- SPG owns Production Plan, Production Work Unit, and production coordination.
- Producing capabilities own generated Work Product Artifacts; SPG maintains lineage and lifecycle relationships.
- Verification does not equal Acceptance, and generated output does not automatically become trusted production truth.
- Guardian retains Assurance Evidence authority; ECF retains Context Projection authority.
- Human authority decisions and governance exceptions produce Human Decision Records.
- Capabilities communicate through owned contracts rather than implementation dependencies.

This is a domain and contract consolidation. It does not add a module, schema, endpoint, provider integration, or MVP implementation commitment.

## Decision Intelligence Capability Ownership

Decision Intelligence Capability and its reusable Decision Engine implementations are company-level strategic intelligence assets. YiJue is a Consumer Product / Application that may provide or consume this capability.

The long-term direction is to evolve the reusable Decision Intelligence Capability into a Decision Intelligence Core / Platform Capability, independently of any one Consumer Product.

The ownership principle is:

> Systems that require general-purpose decision capability should preferentially reuse a unified Decision Intelligence capability rather than build independent Decision Engines repeatedly.

This applies to SPG, enterprise management systems, operations systems, and other AI applications. This is a strategic direction, not a statement that such reuse is currently implemented.

## Intelligence Capability Ownership Principle

An AI-native organization should not repeatedly build the same general-purpose intelligence capability across products or modules.

Each core intelligence capability should have clear strategic ownership and be reusable by other systems through a defined Contract.

| Capability | Owner |
|---|---|
| Decision Intelligence | Decision Intelligence Domain / Capability Owner |
| Production Intelligence | SPG |
| Assurance Intelligence | Guardian |
| Context Intelligence | ECF |

The table records intended capability ownership. It does not transfer ownership of the internal implementation of any external system.

## SPG and Decision Intelligence / YiJue Relationship

The long-term relationship is neither “SPG contains YiJue Decision Engine” nor “SPG builds another Decision Engine.”

```text
Human Intent
      ↓
Decision Intelligence Capability
      ↓
Decision Artifact
      ↓
SPG — Production Governance
      ↓
Software Production
      ↓
Guardian — Assurance
```

Decision Intelligence Capability answers:

> What should we do and why?

SPG answers:

> How do we build it reliably?

YiJue is an important productized provider of the first capability; it is not the capability boundary itself. This is an Architecture Direction. No YiJue integration is implemented by this decision record.

## Intelligence Provider Model

SPG must not be bound to one Decision Provider. The Decision Intelligence Contract may be fulfilled by the following provider forms:

```text
SPG
  ↓
Decision Intelligence Contract
  ├── Lightweight LLM-based Provider
  ├── YiJue Decision Engine
  ├── Enterprise Private Decision Engine
  ├── Third-party Decision Provider
  └── Customer Internal Intelligence
```

The provider model preserves room for enterprise data sovereignty, private deployment, customer-built intelligence capabilities, and ecosystem openness.

No concrete API, adapter, deployment mechanism, or provider implementation is defined here.

## Decision Intelligence Contract First

The Software Production Platform does not wait for a complete Decision Intelligence Product before validating its production loop. Its dependency is the Decision Intelligence Interface and Decision Artifact Contract, not YiJue or any other provider implementation.

The bootstrapping sequence is:

```text
Decision Intelligence Contract
        ↓
Lightweight Decision Intelligence Provider
        ↓
SPG Production Loop Validation
        ↓
Replace / Upgrade Provider
        ↓
YiJue Decision Engine Integration
```

This sequence is an architecture evolution strategy, not a commitment that every provider or integration is currently implemented.

### Decision Intelligence Interface Boundary

At the architecture level, the interface accepts:

- Human Intent
- Background
- Constraints
- Expected Outcome

It returns a **Decision Artifact Candidate** conforming to the Decision Artifact Contract. SPG consumes the artifact contract and must not depend on provider-specific prompts, models, internal reasoning structures, or product APIs. A candidate remains subject to applicable human authority and governance before it becomes an approved production baseline.

The contract defines responsibility and interaction semantics. It does not define a concrete API, transport, schema version, deployment topology, or YiJue adapter.

### Lightweight Provider Boundary

An early provider may use an LLM, Governed Prompt, and Limited Context Assembly to supply the minimum Decision Intelligence needed to exercise the contract. Its purpose is to:

- Bootstrap the SPG production loop
- Validate the production workflow
- Validate the Decision Artifact Contract
- Reveal real capability gaps through production evidence

It is not a substitute for YiJue, a second Decision Engine product, a complete Decision Room, or a multi-role decision system. Its existence must not transfer Decision Intelligence ownership to SPG.

### Production-loop Validation

Decision Intelligence Capability is validated through the real production loop rather than theoretical completeness:

```text
Human Intent
        ↓
Decision Intelligence Provider
        ↓
Decision Artifact Candidate
        ↓
SPG Production Planner
        ↓
Production Work Unit
        ↓
Execution
        ↓
Work Product Artifact
        ↓
Verification
        ↓
Production State
```

Validation should examine Intent interpretation quality, task decomposition quality, Context sufficiency, Decision Artifact usability, and downstream production efficiency.

### Provider Evolution

```text
Provider v0 — Lightweight Decision Adapter
        ↓
Provider v1 — YiJue Decision Engine
        ↓
Provider vN — Multiple Enterprise Decision Providers
```

SPG remains stable at the capability-contract boundary while providers evolve. YiJue remains a Consumer Product and an important productized implementation of Decision Intelligence Capability. It is the intended first reference provider for mature integration, but it is not a hard dependency of SPG; this positioning does not create a current integration commitment.

## Capability Contract Before Capability Implementation

Capability boundaries and interaction contracts must be defined before a concrete implementation is selected or made mandatory. Implementations may then be bootstrapped, replaced, or upgraded without transferring capability ownership or destabilizing consumers.

This principle is consistent with:

- Guardian and Coding Executor separation
- ECF and concrete data-source separation
- Capability and Provider separation
- Role and Agent Runtime separation

## Future Intelligence Fabric

A long-term direction is an **AI Native Organization Intelligence Stack**, rather than multiple isolated AI modules:

```text
AI Native Organization Intelligence Stack

Decision Intelligence Capability
        ↓
Provider implementations, including YiJue Product

Production Intelligence
        ↓
SPG

Assurance Intelligence
        ↓
Guardian

Context Intelligence
        ↓
ECF
```

The capabilities may cooperate through Contracts while preserving ownership, Source of Truth, authority, and lifecycle boundaries.

This is a Future Architecture Direction and is Not Implemented.

## Architecture Rationale

If SPG owned its own Decision Engine, the program could create:

- Confused strategic asset boundaries
- Enterprise data security concerns
- Repeated capability construction
- Reduced ecosystem extensibility

Capability separation provides:

- Enterprise openness
- Private deployment support
- Long-term commercial expansion potential
- Strategic accumulation of core intelligence assets

## Scope and Validation Boundary

This decision record:

- Does not modify YiJue MVP
- Does not modify SPG MVP
- Does not add an implementation commitment
- Does not define a concrete API or adapter
- Does not make future architecture a current capability

All concrete provider integrations, including YiJue integration, unified Decision Intelligence reuse, and Intelligence Fabric composition remain Future Architecture Directions / Not Implemented. A lightweight bootstrap provider remains an allowed validation option rather than a committed MVP deliverable.
