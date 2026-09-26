# Guardian Integration

## Formal Positioning

**Guardian — Engineering Assurance System**

Guardian is platform-native, but platform-independent.

## Boundary

The platform is responsible for Orchestration. Guardian is responsible for Assurance.

Assurance validates observed results, Evidence, contract satisfaction,
important boundary violations, and quality Findings. It does not micromanage
each Executor move or replace the Executor's autonomy inside an admitted
production envelope. See the
[Work-centric Production and Responsibility Principles](../architecture/work-centric-production-and-responsibility-principles.md).

Model-mediated assurance judgments, where present, are candidates subject to
Guardian's own evidence and exact-subject validation. Watt's governed
Self-Refine semantics may support a bounded re-evaluation after contradiction;
they do not turn a wrong-revision PASS into truth, lower Guardian's evidence
bar, or transfer Assurance ownership to the Executor. Current exact-revision
Verification remains a deterministic rejection boundary; no new Guardian
reasoning runtime is claimed by this calibration.

Guardian is:

- Not an AI Code Reviewer
- Not an ordinary CI Gate
- Not an Agent inside a Consumer Application

## External Product and Work Relationship

For Work that produces or evolves an external product such as 易决, the current
direct integration is a **Reference / Transitional Integration**. The
long-term direction is **Platform-mediated Integration**. Guardian qualifies
Evidence for the governed Work/PWU; it does not own a Project lifecycle, Work,
Plan, or attached Assets.

This document does not design Guardian Core.
