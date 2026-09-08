# Design Intelligence Capability Evolution

## Architecture Insight

The MVP uses Single Intelligence Mode:

```text
Human Goal
    ↓
Production Planner
    ↓
Design / Planning / Task Decomposition
    ↓
Execution Loop
```

This is a validation mode for the AI-native software production loop.

Long term, Production Planner should be understood as a **Production Planning Capability**, not as a fixed super AI Architect Agent.

## Stable Role, Evolving Intelligence

A Role can have different implementations while its Role Contract remains stable:

```text
Role: Production Planning

MVP:      Single AI Model
Future:   Multi-role Decision System
Advanced: Human + AI Decision Council
```

The platform preserves the capability boundary while allowing the intelligence implementation to evolve.

## Decision Intelligence Integration

YiJue, as a Consumer Product / Application, may provide a future Decision Intelligence Provider implementation invoked by Production Planner through a capability contract.

It does not replace Production Planner or implement Production Planning Capability. The relationship is:

```text
Production Planning Capability
        └── Production Planner
                └── may invoke Decision Intelligence Capability (Future)
                        └── Provider implementations, including YiJue Product
```

## Decision Intelligence Interface

The platform defines a provider-independent Decision Intelligence Interface as an architecture contract. A concrete API and provider integration remain future implementation choices.

Contract input:

- Human Intent
- Background
- Constraints
- Expected Outcome

Contract output:

- Decision Artifact Candidate

SPG consumes the Decision Artifact Contract rather than a provider-specific response format. The contract does not require the MVP to implement an API or integrate YiJue.

## Complementary System Relationship

YiJue and the Software Production Platform are complementary systems:

```text
YiJue
How to think better
        ↓
Software Production Platform
How to build better
        ↓
Guardian
How to trust better
```

The broader relationship is:

```text
Decision Intelligence → Intent Formation → Production Planning
    → Execution → Verification → Assurance → Continuous Evolution
```

## Scope Boundary

This document records a current architecture contract plus a Long-term Architecture Vision and Future Evolution Direction. The contract does not make its provider implementations an MVP Requirement or Current Implementation Scope.

The MVP remains focused on:

```text
Human Goal → Production Planner → Task Planning → Executor
    → Verification → Iteration
```


## Capability Separation

Decision Intelligence answers:

> What should we do?

Software Production Platform answers:

> How do we produce it?

Guardian answers:

> How do we trust it?

The platform does not directly embed or own Decision Intelligence. It uses a Capability Contract Layer through which Production Planner may coordinate a replaceable provider.

## Boundary Rules

Production Planner is responsible for Work Intelligence, Production Intelligence, Iteration Management, and bounded PWU coordination.

It does not own enterprise strategic decisions, product direction selection, major value judgments, or Decision Intelligence Capability.

## MVP and Future Boundary

The MVP may use a Minimal Decision Capability Provider as a lightweight, replaceable boundary for validating workflow needs. Such a provider may use an LLM, Governed Prompt, and Limited Context Assembly. Its purpose is to bootstrap the SPG loop, validate the Decision Artifact Contract, and expose real capability gaps; it does not replicate or replace YiJue, build a Decision Room, define a complete Decision Schema, build a multi-role decision system, or implement a YiJue adapter.

YiJue integration is a Future Capability and Architecture Direction only.


