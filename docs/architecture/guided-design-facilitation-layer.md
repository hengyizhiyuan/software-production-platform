# Guided Design Facilitation Layer

Status: **IMPLEMENTED / DETERMINISTIC VALIDATION PASS / REAL PROVIDER PROOF PASS**

Closure: **PENDING ARCHITECTURE LEAD REALITY REVIEW.**

Human–Watt experience calibration v2: **IMPLEMENTED / FOCUSED VALIDATION PASS /
REAL PROVIDER V2 PROOF PASS / HUMAN PRODUCT ACCEPTANCE PENDING.**

## Purpose

Guided Design Facilitation makes the existing Guided Design structure active
and Human-legible. It does not replace Design Reality or Plan Steering. It
projects the current stage, identifies completed and unresolved areas, exposes
dependencies and blockers, explains the next valuable focus, and chooses an
appropriate collaboration strategy.

The goal is a design-leading experience rather than a passive questionnaire.

## Facilitation responsibilities

For the selected design schema and current governed basis, Watt derives:

- current design stage;
- completed and unresolved design areas;
- unresolved dependency blockers;
- current focus and why it is next;
- one facilitation strategy and Human-facing guidance;
- progress count and narrative;
- readiness and unresolved critical conditions.

The bounded strategy set is:

| Strategy | Intended use |
| --- | --- |
| `CLARIFY` | Resolve ambiguity that blocks the current design issue. |
| `SUMMARIZE` | Consolidate enough accepted material before progression. |
| `PRESENT_ALTERNATIVES` | Expose materially distinct viable directions. |
| `EXPLAIN_TRADE_OFFS` | Make constraints, risks, and consequences reviewable. |
| `PROPOSE_NEXT_STEP` | Recommend the next bounded design move. |
| `REQUEST_HUMAN_DECISION` | Stop where product/architecture Authority is required. |

Question asking is one strategy, not the default behavior. The current issue,
dependencies, readiness, required output, and Human-Authority relevance govern
the selection.

At the pre-Work conversation boundary, facilitation now receives the matched
schema's ordered stages together with exact persisted Interaction Reality.
Human-facing behavior must explain the route, locate the current discussion,
reuse known information, recommend the next high-value design move, and surface
only the most material unresolved question. Proactive guidance remains
advisory: it can frame choices and explain trade-offs, but it cannot admit
Design Reality, create Work, or transfer Authority.

## Seed Design Schema Registry

The registry is provider-neutral, versioned, configurable in application code,
and extensible through stable schema identity/version contracts. Version `0.1`
contains three seed methodology assets:

### General Product/System Design v0.1

For new products, platforms, and internal systems. It covers motive, users and
problem; outcomes and journeys; boundary and non-goals; capability/lifecycle;
responsibility, information, and interaction; architecture, risks, and
assumptions; and verification/staged production readiness.

### Technical System Design v0.1

For infrastructure and architecture-oriented systems. Its stages cover
requirements, constraints, scale/performance, data model, architecture options,
failure modes, verification strategy, and implementation readiness.

### Existing Product Evolution v0.1

For explicit evolution of an existing product/system. Its stages cover current
Reality, user feedback, problem prioritization, solution options, impact
assessment, validation, and evolution plan.

These schemas are initial methodology assets, not a final library. This slice
does not add schema persistence administration, editing UI, marketplace, user
workflow editor, or BPM engine.

## Schema matching

Matching is deterministic and explainable. Explicit existing-product Reality
takes precedence, technical/infrastructure intent selects the technical schema,
and a new product/system Motive selects the general schema. The selected schema
identity, version, and rationale are persisted on the Interaction and later
Guided Design process.

For the mandatory scenario:

> 我想做一个运营管理平台。

Watt selects **General Product/System Design v0.1**, explains that the input is
a new software product/system design problem, establishes the opening stage and
focus, explains why that focus precedes downstream capability design, and
presents active guidance rather than merely returning a list of questions.
The persisted conversation response includes the selected methodology, its
ordered stage path, the opening stage, the current focus, and why that focus
precedes downstream design commitments.

## Ownership and progression

```text
WIC
    owns Human interaction and advisory interpretation

Guided Design
    owns schema, issue structure, facilitation projection, and readiness

Plan Steering
    owns WHAT NEXT and the current admitted Step

Human Governor
    owns material direction, trade-offs, scope, risk, and acceptance

SPG / Executor
    own governed production / HOW only after production admission
```

Schema matching and facilitation never create Work or production Authority.
When a governed Work exists, the matched schema seeds the existing Guided
Design process and Plan Steering uses the same ordered issue identities. Design
results continue to require existing semantic-result admission before they can
change Design Reality.

## Persistence and restart

The selected schema and rationale, agenda revisions, current focus, completed
and unresolved issues, dependencies, admitted decisions/results, and
progression rationale are persisted or deterministically reconstructed from
governed Reality. A restart or provider replacement does not reset the design
process and does not require hidden model memory.

## Limitations

The registry is code-configured, matching uses bounded deterministic intent
signals, and facilitation strategies are explainable heuristics over current
governed state. There is no learned schema routing, dynamic schema authoring,
distributed collaboration queue, or claim of enterprise-complete design
methodology.

## References

- [Human–Watt Collaboration Layer](human-watt-collaboration-layer.md)
- [Guided Design Core](guided-design-core.md)
- [Reality-driven Plan Steering Principles](reality-driven-plan-steering-principles.md)
- [Focused Validation](../evidence/human-watt-collaboration-layer-focused-validation.md)
