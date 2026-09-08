# Engineering Context Fabric Integration

This document does not design ECF internally. It records only the platform's need for Context capability.

In the future, Engineering Context Fabric may provide:

- Canonical Context
- Projection
- Provenance
- Synchronization

The platform consumes Context capability from ECF.

Under the [Work-centric Production Model](../architecture/work-centric-production-model.md),
ECF assembles context from attributable Work Assets. It does not create a
Project container or turn an Asset into Work Truth:

```text
Work + admitted Asset relationships
    -> ECF discovery / freshness / provenance / projection
    -> decision-scoped Engineering Context
```

## Governed Execution Context Boundary

The [SPG Lite Runtime Implementation Contract](../architecture/spg-lite-runtime-implementation-contract.md) confirms Context Assembly Lite while full ECF remains deferred.

Context Packages may rely on admitted, versioned, traceable Engineering
Artifacts, Work Asset references, Contracts, facts, constraints, and Baseline
references as execution Authority. Raw conversation may be preserved as
provenance, audit evidence, or interaction history, but it must not be inserted
as task Authority or become a direct execution dependency.

Every Execution Attempt must remain traceable to the exact governed Context Package used.
