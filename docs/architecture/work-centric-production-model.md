# Watt Work-centric Production Model

Status: **ARCHITECTURE PRINCIPLE / ALIGNED**

Implementation impact: **DOCUMENTATION ONLY — NO NEW ENTITY, SCHEMA, API, OR
RUNTIME BEHAVIOR**

## 1. Purpose

Watt organizes AI-native software production around **Work**. It does not use
Project as a first-class production entity or introduce a parallel Project
lifecycle above Work.

The governing shape is:

```text
Work
├── Intent
├── Design Reality
├── Assets
│   ├── Repository Asset
│   ├── Document Asset
│   ├── Design Artifact Asset
│   ├── External System Asset
│   └── Runtime Asset
├── Work Reality
├── Steering Plan
├── PWU
├── Execution History
└── Evidence
```

This is a conceptual responsibility model. It does not prescribe a new
database aggregate or claim that every branch is already implemented as one
physical object.

## 2. Work Is the Primary Production Entity

A Human begins with a Motive, goal, request, problem, or desired change. WIC
interprets and refines that expression. Only governed admission creates or
revises Work.

```text
Human Motive / Goal
    -> Interaction and interpretation
    -> governable intent
    -> Human Work admission
    -> Work
```

Work is the durable governed representation around which Watt relates:

- admitted intent, desired outcome, constraints, and scope;
- Design Reality and accepted decisions;
- Steering Plan and current direction;
- bounded Production Work Units;
- execution and Runtime lineage;
- Verification, acceptance, and other Evidence;
- the resources required to understand or produce the outcome.

Work may be narrow or broad and short-lived or long-lived. PWU, not Work, is
the bounded execution unit.

Goal remains an optional weak aggregation. It is not a mandatory parent and
does not create a Project lifecycle.

## 3. Work Asset

A **Work Asset** is the governed association between a Work and an internal or
external resource relevant to understanding, designing, producing, operating,
or verifying that Work.

Representative assets include:

- a Git repository or exact repository baseline;
- a PRD, architecture document, specification, or other document;
- a Figma file, prototype, image, or exported design artifact;
- a Jira board, issue system, service catalog, or other external system;
- a Runtime environment or attributable Runtime state.

The association should eventually be able to preserve identity, source,
version or observed revision, provenance, intended role, scope, and freshness
where those facts matter. This document does not define the final Work Asset
schema.

### Association, not external ownership

`Assets belong to Work` means that Watt governs the asset's relevance and
binding in the context of that Work. It does not mean Watt owns the external
repository, document system, design tool, or Runtime.

The same external resource may be relevant to more than one Work. Each Work
must preserve its own admitted relationship and exact applicable Reality rather
than relying on an ambiguous global Project container.

### Asset is not Truth

An asset does not become governed Work Reality merely because it is attached:

```text
Asset
    -> attributable observation / extraction
    -> candidate meaning or context
    -> impact and authority evaluation
    -> admitted Work Reality where applicable
```

Source-domain facts remain owned by their source. A document can contain a
claim; a repository can expose exact code Reality; a Runtime can expose
operational Reality. Watt must distinguish those observations from AI
interpretation and from the governed conclusions admitted into Work Reality.

Before Work admission, external material may exist as Interaction provenance
or a candidate input. It becomes a Work Asset relationship only when a Work
exists and the relationship is admitted. This preserves
`FIRST UTTERANCE != WORK CREATION`.

## 4. Repository Relationship

A repository is a **Repository Asset**, not a Project, not the Work itself, and
not the owner of Work Truth.

```text
Repository Asset
    -> exact Repository Reality extraction
    -> attributable context / candidate impact
    -> governed Work Reality
```

Repository revisions, trees, status, observations, integration effects, and
Trusted Baselines retain their existing source and Runtime semantics. Work
Reality references the relevant exact facts; it does not flatten or duplicate
the repository as a second truth store.

An Executor operates only against the exact Repository Asset baseline and
scope admitted for a PWU. Repository access does not grant authority to change
Work intent, attach unrelated assets, or create a Project lifecycle.

## 5. Product Language

Watt product and architecture language should prefer:

| Avoid as a Watt production operation | Use |
| --- | --- |
| New Project | New Work |
| Import Project | Work Asset Intake |
| Project Lifecycle | Work lifecycle and governed Work Reality revisions |
| Project repository | Repository Asset attached to Work |
| Project plan | Steering Plan for Work |
| Project execution | Governed PWU execution for Work |

`Project` may still appear:

- in historical evidence or task names;
- when describing traditional project management as a contrast;
- as a Human/domain-world description of an external software system;
- when naming an external product or organizational engagement.

Those uses do not create a Watt Project entity, aggregate root, authority
boundary, or lifecycle.

## 6. Capability Boundaries

| Capability | Work-centric responsibility |
| --- | --- |
| WIC | Interprets Human input, preserves provenance, assesses impact, and coordinates Human-governed Work admission or revision. |
| Work / Work Reality | Owns the admitted Motive representation, outcome, constraints, scope, and evolving governed production intent. |
| Guided Design | Uses attributable asset inputs to facilitate and admit Design Reality without owning Work or asset-source truth. |
| Plan Steering | Determines WHAT NEXT from Work Reality and relevant asset-derived facts; it does not own or mutate the assets. |
| PWU | Bounds one admitted production step, including exact asset baseline, scope, contract, and evidence obligations. |
| SPG | Governs execution, observation, Verification, integration, and truthful production-state transition for an admitted PWU. |
| Executor | Determines HOW within the envelope; asset access is capability, not Work or production Authority. |
| Guardian / Verification | Qualifies evidence and trust obligations; it does not own Work, Plan, or source assets. |
| ECF | Discovers, projects, assembles, checks freshness, and preserves provenance for context drawn from Work Assets. |

No capability in this table introduces a parallel Project lifecycle.

## 7. Current Implementation Reality

The current implementation is compatible with this principle:

- `WorkRecord` is the governed production representation and has no
  `project_id`;
- Goal is optional;
- `EngineeringScope` is keyed by `work_id`;
- `ResourceBinding` connects an admitted Engineering Scope to an Engineering
  Resource;
- the current `EngineeringResourceKind` supports `REPOSITORY`;
- `WorkRuntimeBinding` joins Work Reality, Engineering Scope/Resource,
  Steering, Plan, PWU, Run, and Governance records;
- no Project domain record, Project table, or Project lifecycle exists.

Current Engineering Resource and repository bindings are a narrow implemented
foundation, not a complete generic Work Asset capability. Documents, design
artifacts, external systems, and Runtime Assets do not yet share one generalized
Work Asset contract.

## 8. Future Changes Requiring Separate Admission

Possible future work includes:

- a provider-neutral Work Asset identity and binding contract;
- multiple assets per Work with explicit semantic roles;
- version, freshness, provenance, and access-policy semantics;
- Work Asset Intake for documents, design tools, issue systems, and Runtime
  sources;
- ECF-backed context projection over admitted Work Assets;
- Human-facing asset relationship and impact views.

These are future design questions, not implementation authorized by this
alignment. No schema, migration, API, UI, connector, lifecycle, or Runtime
change is introduced here.

## 9. Invariant

> Work is Watt's primary production entity. Assets provide attributable inputs
> and execution surfaces for Work; they do not become Work, Project, or Truth
> owners.

## References

- [Work-centric Production and Responsibility Principles](work-centric-production-and-responsibility-principles.md)
- [Watt Product North Star](watt-product-north-star.md)
- [Motive / Work / Plan Concept Calibration](motive-work-plan-concept-calibration.md)
- [Work Interaction & Closed-loop Refinement](work-interaction-closed-loop-refinement.md)
- [Reality-driven Plan Steering Principles](reality-driven-plan-steering-principles.md)
- [External Design Intake Capability Direction](external-design-intake-capability-direction.md)
- [ECF Integration](../context/ecf-integration.md)
- [Guardian Integration](../assurance/guardian-integration.md)
