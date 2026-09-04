# Motive / Work / Plan Concept Calibration

## Status and Scope

**Architecture Decision: CLOSED / PASS**

This record calibrates product language and conceptual boundaries. It does not
rename current domain types, database tables, identifiers, API routes, Runtime
bindings, tests, or UI implementation. It adds no Project Governor, Initiative,
mandatory parent object, schema, API, or production capability.

## Motive: Product-facing Concept

**Motive** is the thing the user genuinely wants to make happen.

A Motive begins with the user's expression and is progressively refined into a
governable production or development intent. It may concern:

- creating a new software system;
- evolving an existing system;
- implementing a feature;
- producing architecture or documentation;
- investigating or analyzing data;
- resolving an engineering problem.

Motive is not restricted to code production, and it does not imply that the
initial expression is already executable or authoritative.

## Motive / Work Mapping

```text
Motive = product-facing concept and language
Work   = current internal governed representation
```

The existing implementation continues to use `Work`, including domain types,
database tables, `work_id`, API routes, Runtime bindings, and tests. No
repository-wide Work-to-Motive rename is authorized.

The mapping describes the current product/implementation boundary. It does not
assert that Motive and Work must remain permanently identical implementation
concepts.

## Work Scale

A governed Work is not inherently an atomic coding task. It may be narrow and
short-lived or broad and long-lived. Its trusted outcome may include code,
documentation, architecture, tests, evidence, analysis, Runtime/product state,
or multiple related trusted artifacts.

**Production Work Unit (PWU), not Work, is the bounded production-unit
concept.**

The current MVP one-PWU-first policy constrains executable production, not the
meaning or lifetime of Work. If a broad Work cannot yet be executed truthfully
within one PWU, the current Runtime may require refinement, Human-managed
sequencing, or deferral of independently governed steps. It must not redefine
the Work itself as inherently atomic.

## Plan Role

Plan is not only a short execution checklist. Conceptually, it can guide a
long-lived Work across changing Reality:

```text
Motive / Work
    ↓
Plan
    ↓
Current Reality
    ↓
determine the next appropriate step
    ↓
refinement / design / Human decision / governed production as needed
    ↓
New Reality
    ↓
Plan reassessment / evolution
    ↓
repeat until the Work outcome is achieved
```

The Plan maintains direction while allowing the path to evolve from evidence.
Dynamic adjustment remains governed, attributable, and explainable.

MVP-PLAN-1B is a narrow implementation subset: it creates one durable,
provider-neutral single-PWU Production Plan Proposal for the currently admitted
production step. Its ordered steps are not the complete long-lived Plan
Steering capability described here. PLAN-1B remains CLOSED / PASS and is not
reopened by this calibration.

## SPG Boundary

The broader Plan primarily answers:

> Given the Work objective and current Reality, what should happen next?

SPG is the governed software-production capability used when a Plan step
requires trusted engineering production. It primarily answers:

> How is an admitted production step executed, observed, verified, and
> committed truthfully?

SPG retains its existing Production Planner, Runtime, Executor, Verification,
and Commit responsibilities for an admitted production step. It does not become
the owner of every discovery, value judgment, product decision, or Human
decision in a long-lived Plan. Conversely, the broader Plan does not bypass
SPG production authority, evidence, or trust gates.

## Goal and Project Boundary

Goal remains an optional weak aggregation in the current product model. It is
not made mandatory above Motive or Work.

Project may describe an existing or new software system in the user's domain
world. It is not promoted to a new first-class production object, aggregate
root, or mandatory parent above Work. No Project or Initiative domain entity is
introduced.

## Remaining Core Capability: Reality-driven Plan Steering

**Status: NOT YET IMPLEMENTED — MATERIAL CORE PRODUCT CAPABILITY**

Reality-driven Plan Steering means AI continuously guides a long-lived Work by:

- evaluating the Work objective and current Reality;
- recommending or choosing the next Plan step within governance boundaries;
- requesting Human decisions when required;
- revising the Plan as new Reality appears;
- preserving the Motive, authority boundaries, evidence, and outcome direction.

This is not Phase-2 hardening. It is a remaining core product capability.
Advanced autonomous replanning, multi-PWU orchestration, optimization,
supersession automation, and unattended continuous production may remain
separately deferred; their deferral does not classify the core steering gap as
optional hardening.

Its higher-order product thesis and normative continuity, reconstructability,
equivalence, provenance, and anti-drift requirements are recorded in
[Reality-driven Plan Steering — Foundational Principles](reality-driven-plan-steering-principles.md).
Its bounded admitted MVP behavior is recorded in the
[Reality-driven Plan Steering MVP Behavioral Contract](reality-driven-plan-steering-mvp-contract.md).
Implementation remains not yet started.

A distinct future alignment capability is recorded in
[Interpretation Externalization and Multimodal Alignment](interpretation-externalization-and-multimodal-alignment.md).
It may help a Human calibrate the system's reconstructed Motive before costly
production, but it is not a mandatory Work gate, current MVP scope, or
implementation authorization.

No implementation contract, data model, API, orchestration change, or Feature
ID is created by this documentation decision.
