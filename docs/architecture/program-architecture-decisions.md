# Program-level Architecture Decisions

This document records program-level architecture decisions and strategic boundaries. It is a living decision record; future directions described here are not current implementation capabilities.


## Decision Intelligence Terminology and Product Boundary

The Decision Intelligence domain is layered as follows:

```text
Decision Intelligence Domain
├── Decision Intelligence Capability
├── Decision Engine
└── Product / Provider Implementations
        └── YiJue Product
```

YiJue is a Consumer Product / Application and one possible Decision Intelligence Capability Provider. It is not the Decision Intelligence Platform Capability, Enterprise Decision Infrastructure, or a Software Production Platform component.

YiJue owns its Consumer Product Experience, Decision Room Experience, Consumer Runtime, product-specific Policy, product-specific Business Logic, and User Interaction Model.

The Decision Intelligence Capability is the reusable abstraction that transforms incomplete intent and complex context into structured, explainable, and accountable Decision Artifacts. It may be implemented by a YiJue Decision Engine, Enterprise Decision Engine, or Third-party Decision Provider.

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

## SPG and YiJue Relationship

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

YiJue answers:

> What should we do and why?

SPG answers:

> How do we build it reliably?

This is an Architecture Direction. No YiJue integration is implemented by this decision record.

## Intelligence Provider Model

SPG should not be bound to one Decision Provider. A future capability contract may allow the following provider forms:

```text
SPG
  ↓
Intelligence Capability Contract
  ├── YiJue Decision Engine
  ├── Enterprise Private Decision Engine
  ├── Third-party Decision Provider
  └── Customer Internal Intelligence
```

The provider model preserves room for enterprise data sovereignty, private deployment, customer-built intelligence capabilities, and ecosystem openness.

No concrete API, adapter, deployment mechanism, or provider implementation is defined here.

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

All provider integration, unified Decision Intelligence reuse, and Intelligence Fabric composition remain Future Architecture Directions / Not Implemented.



