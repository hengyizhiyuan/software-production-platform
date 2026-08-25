# System Overview

The platform is not a single Agent. Its core abstraction is the relationship among Role, Responsibility, Authority, Context, Artifact, and Gate.

```text
Human Governance
        |
        v
AI Design / Planning
        |
        v
Executor
        |
        v
Verification
        |
        v
Assurance
```

The platform target is a **Governed AI Engineering Loop** in which human governance, AI design and planning, execution, verification, and assurance are connected through explicit responsibilities and evidence.


## Long-term Role Relationship

The long-term system keeps three responsibilities distinct:

```text
ECF Engineering Context ──┬──→ Production Planner
                          └──→ Guardian
Human Governance ─────────────→ Production Planner

Production Planner ──→ Executor ──→ Guardian
        │                 │              │
        └── Plan Event ───┴─ Execution ──┴─ Assurance Evidence
                              ↓
                      SPG Production State
```

Production Planner is responsible for production direction and coherence, Executor for production execution, Guardian for independent Assurance, ECF for canonical engineering context and factual projections, and SPG for Production State. ECF is not a downstream stage after Guardian, and Guardian does not own Production State.

This relationship is an architectural direction. It does not define new MVP implementations or internal designs for Guardian or ECF.

## Production Intelligence Architecture

The system organizes capabilities under Human Governance and the Production Planner Role:

```text
Human Governor
        ↓
Production Planner Role
        ↓
Capability Contract Layer
  Decision Intelligence Capability
    (replaceable providers; YiJue integration is Future)
  Production Execution (Executor)
  Assurance Intelligence (Guardian — Future)
  Context Intelligence (ECF)
```

The Production Planner coordinates capability execution; it does not own every domain intelligence capability.

SPG depends on the Decision Intelligence Interface and Decision Artifact Contract, not on YiJue or another concrete provider. A lightweight provider may bootstrap production-loop validation before a mature provider is integrated.
