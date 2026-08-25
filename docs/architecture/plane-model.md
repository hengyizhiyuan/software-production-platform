# Plane Model

The program-level system baseline consists of five capability planes. The earlier three-plane technical view—Production / Control, Assurance, and Context—remains a subset of this system model rather than the complete overall architecture.

```text
AI-Native Software Production System
├── Human Governance Plane
├── Decision Intelligence Plane
├── Production / Control Plane
├── Assurance Plane
└── Context Plane
```

## Human Governance Plane

Responsible for Intent, authority, value judgment, risk acceptance, and final accountability.

## Decision Intelligence Plane

Responsible for Intent understanding, decision reasoning, and Decision Artifact formation through a provider-independent Decision Intelligence Contract.

## Production / Control Plane

Responsible for:

- Workflow
- Task
- Executor orchestration
- Verification flow
- Delivery lifecycle

## Assurance Plane

Provided by Guardian, the Independent Engineering Assurance Subsystem.

## Context Plane

Provided by Engineering Context Fabric, responsible for Context Authority, Context Projection, and Context Lineage across all planes.

Execution participates through capability contracts within the Production / Control flow. Production Artifact is the domain category; the Execution System or producing Capability Provider owns concrete Work Product Artifacts. SPG owns Production Work Unit governance and coordination rather than executor internals or generated artifact content.

This model records responsibility and dependency boundaries. It does not require each plane to be a separate runtime, service, repository, or MVP implementation.
