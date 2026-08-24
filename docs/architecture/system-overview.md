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
Executor
   | responsible for production speed
   ↓
Design Lead AI
   | responsible for evolution direction and design consistency
   ↓
Guardian
   | responsible for trusted boundaries and Assurance
   ↓
ECF
   | provides Context, Source of Truth, and Engineering State
```

This relationship is an architectural direction. It does not define new MVP implementations or internal designs for Guardian or ECF.
