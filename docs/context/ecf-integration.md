# Engineering Context Fabric Integration

This document does not design ECF internally. It records only the platform's need for Context capability.

In the future, Engineering Context Fabric may provide:

- Canonical Context
- Projection
- Provenance
- Synchronization

The platform consumes Context capability from ECF.



## Governed Execution Context Boundary

The [SPG Lite Runtime Implementation Contract](../architecture/spg-lite-runtime-implementation-contract.md) confirms Context Assembly Lite while full ECF remains deferred.

Context Packages may rely on admitted, versioned, traceable Engineering Artifacts, Contracts, facts, constraints, and Baseline references as execution Authority. Raw conversation may be preserved as provenance, audit evidence, or interaction history, but it must not be inserted as task Authority or become a direct execution dependency.

Every Execution Attempt must remain traceable to the exact governed Context Package used.
