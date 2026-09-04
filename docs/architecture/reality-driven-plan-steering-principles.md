# Reality-driven Plan Steering — Foundational Principles

## Status and Authority

**Foundational Architecture / Product Principles: RECORDED / ADMITTED**

**Reality-driven Plan Steering: MATERIAL MVP CORE PRODUCT CAPABILITY — NOT YET IMPLEMENTED**

This record builds on the
[Motive / Work / Plan Concept Calibration](motive-work-plan-concept-calibration.md).
It defines product intent and normative architecture requirements. It does not
implement Plan Steering, prescribe a database schema, or change production
code, API, Runtime, Executor, migration, or authority behavior.

## Strategic Product Position

Reality-driven Plan Steering is not merely an AI task-list generator or a
convenience feature. It is intended to become one of Watt's primary product
differentiators.

Code generation, tool use, agent loops, test execution, review, CI integration,
and model/tool orchestration can be supplied by many evolving capabilities.
Watt's intended higher-order value is to:

```text
continuously preserve development direction;
reconstruct why the current Plan exists;
determine the next appropriate move from governed engineering Reality;
prevent long-running software production from drifting away from
the original Motive and admitted decisions.
```

This is a product thesis and differentiation strategy, not a claim of exclusive
market capability or leadership.

## Core Problem: Plan Continuity Must Not Depend on Conversation Continuity

Long-running AI-assisted development can drift across conversation/session
boundaries, context-window truncation, model/provider changes, host or execution
environment changes, contradictory conversation, forgotten reasoning, and
Executor-local optimization. A Plan derived from transient model memory rather
than governed facts cannot provide durable direction.

A user must not need to remain in one long AI conversation merely to preserve
the established development direction.

> Plan continuity must not depend on conversational continuity.

## Foundational Principle: Facts Constrain the Plan

> **Facts constrain the Plan.**

A Plan must be derived from governed Reality, including the applicable:

- Motive / Work objective and admitted Desired Outcome;
- approved decisions and explicit Human priorities;
- constraints and authority/risk boundaries;
- Current Trusted Baseline and relevant Runtime Reality;
- Engineering Resource Reality;
- completed Work and production results;
- open and closed Findings;
- Verification and Acceptance evidence;
- unresolved blockers and explicit deferred boundaries;
- currently available capabilities;
- prior admitted Plan revisions.

Conversation may contribute candidate information during Refinement, but raw
conversation history is not the authoritative basis of Plan continuity.

## Foundational Principle: Models Do Not Own the Plan

> **Models reason over the Plan. Models do not own the Plan.**

A model is a replaceable reasoning capability. The authoritative Plan must not
be hidden inside a model session, chain-of-thought, transient prompt context,
provider-specific memory, or one ChatGPT, Codex, Claude, or other conversation.

Changing model, provider, session, host, or execution environment must not by
itself redefine the accepted development direction. Internal chain-of-thought
is neither required nor treated as governed Plan provenance; the system relies
on explicit facts, rationale summaries, decisions, and evidence.

## Material Plan Equivalence

The architecture targets the following expectation:

```text
same governed facts
+ same Motive / Work objective
+ same constraints
+ same accepted decisions
≈ materially equivalent Plan
```

Material equivalence does not require deterministic model output, identical
wording, or identical micro-ordering. Models may legitimately differ in
explanation, local implementation preference, or ordering between equally valid
non-blocking steps.

Without changed governed Reality, they should not differ materially in major
phases, known blockers, hard dependencies, admitted scope, mandatory
constraints, major risk ordering, completion conditions, or already-deferred
boundaries. Material divergence without changed governed Reality must be
detectable and explainable.

## Foundational Principle: Plan Must Be Reconstructable

> **Plan must be reconstructable from governed Reality.**

A future Watt instance must be able to answer:

- What are we trying to achieve?
- Where are we now?
- Why is the current Plan shaped this way?
- Why is the current step next?
- Which facts caused a previous Plan revision?
- Which Human decisions constrain the Plan?
- Which Findings remain open?
- What must change before the Plan should materially change?

The original AI conversation must not be required. A rationale that can only be
expressed as "the previous model/session said so" is not acceptable.

## Plan Revision Provenance

A Plan Revision should be semantically traceable to facts equivalent to:

```yaml
Plan Revision N:
  derived_from:
    - Motive / Work version
    - previous Plan Revision
    - Trusted Baseline / relevant Reality snapshot
    - approved Decisions
    - open / closed Findings
    - Constraints
    - Verification / Acceptance evidence
    - Human priority changes
  material_change: what changed in the Plan
  reason: which governed Reality change justified the revision
  supersedes: previous Plan Revision
```

This is a semantic traceability requirement, not a final persistence schema.

## Reality-driven Evolution

Plan is a living governed structure, not a frozen upfront roadmap:

```text
Motive / Work
    ↓
Current Reality
    ↓
Current Plan
    ↓
determine next appropriate step
    ↓
Refinement / Design / Human Decision / SPG Production /
Verification / Acceptance as appropriate
    ↓
New Reality
    ↓
reassess
    ↓
preserve the Plan when Reality does not justify change
OR create a traceable Plan Revision when Reality does justify change
    ↓
repeat until the Work outcome is achieved
```

> **New model output alone is not New Reality.**

A different model preference is not sufficient reason to revise the Plan.

## Roadmap and Reality Principle

> **Roadmap guides production. Reality governs roadmap.**

The current Plan/Roadmap provides continuity and prevents needless replanning.
Verified Reality may legitimately require blocker insertion, step reordering,
scope refinement, risk escalation, Human Attention, or a Plan Revision. The
revision must cite the Reality that justified it.

For example:

```text
planned next step:
    continue feature work

new governed Reality:
    Trusted Baseline and Active Runtime diverge

legitimate revision:
    Runtime correctness work precedes the planned feature step
```

The Runtime divergence, not a new model preference, explains the revision.

## Anti-Drift Requirement

Reality-driven Plan Steering must actively resist:

- session drift;
- model-preference drift;
- context-loss drift;
- Executor-local optimization drift;
- "latest conversation wins" behavior;
- unnecessary Plan regeneration;
- feature expansion without Motive or Reality justification.

The default is:

```text
preserve the current admitted Plan
```

unless governed Reality justifies a change. Repeatedly asking an LLM to make a
new Plan from conversational context is not an adequate continuity mechanism.

## Model and Environment Decoupling

If governed Reality is unchanged, switching Model A to Model B, Provider A to
Provider B, or machine/session/runtime environment A to B should preserve the
material development direction.

Execution mechanics may differ when environment capabilities differ. The Plan
may change materially only when those capability differences become governed
Reality relevant to achieving the Work. Environment identity alone is not a
planning reason.

## Human Authority Boundary

Human remains the Governor. Reality-driven Plan Steering may recommend next
steps, explain rationale, preserve or revise the Plan within admitted
boundaries, and identify when Human judgment is required.

It must not silently redefine Motive, major product direction, admitted
constraints, major scope, risk tolerance, or explicit Human decisions.

> **Plan intelligence is not Goal Authority.**

## Relationship to SPG

```text
Plan Steering
    determines what should happen next from governed Reality.

SPG
    truthfully executes an admitted engineering-production step.
```

SPG results become new governed Reality consumed by Plan Steering. Plan
Steering does not duplicate SPG execution, observation, Verification, Commit,
Executor, or Runtime orchestration semantics, and it is not another Executor or
Orchestrator.

## Relationship to Interpretation Externalization

[Interpretation Externalization and Multimodal Alignment](interpretation-externalization-and-multimodal-alignment.md)
is a related but distinct future capability. It asks whether Watt's
reconstructed understanding of the Motive is materially aligned with the
Human's mental model; Plan Steering asks what should happen next from admitted
objective and Reality. Future Plan Steering may selectively request an
Alignment Artifact when semantic risk is material, but this record defines no
trigger, representation-selection algorithm, mandatory gate, or implementation
authorization.

## Fresh-session Reconstruction Requirement

A user may close the current AI session and later start a new session, change
model, change machine, or reconnect to the same Watt engineering Reality. Watt
should reconstruct:

```text
current Motive / Work
current Plan
current step
accepted decisions
open Findings
why the current step is next
relevant Trusted Baseline / Runtime Reality
```

and continue with materially consistent direction. This is a first-class
product requirement, not merely disaster recovery.

## Strategic Differentiation Thesis

Watt should not compete only on:

> Can the AI write the code?

It should also compete on:

> Can the software-production system preserve intent, direction, and
> engineering truth across a long-running development lifecycle?

Coding intelligence is replaceable and expected to evolve rapidly. Plan
continuity, governed Reality, traceable evolution, and resistance to
development drift are intended to form durable system-level differentiation.
This remains strategic intent, not a claim that other systems cannot implement
similar principles.

## Current Capability Gap

```text
Reality-driven Plan Steering
    MATERIAL MVP CORE PRODUCT CAPABILITY
    NOT YET IMPLEMENTED

MVP-PLAN-1B
    CLOSED / PASS
    Single-PWU Production Planner Lite only
```

PLAN-1B does not satisfy long-lived Plan Steering. This record adds no
implementation authorization.

## Reserved Next-stage Design Questions

The next architecture design stage must address, but this record does not
prematurely answer:

- What exact governed Reality forms the Plan Frame?
- What is persisted versus reconstructed?
- What constitutes a Plan Revision?
- What Next-Step classifications are required?
- When may AI continue automatically?
- When is Human Attention mandatory?
- How is Plan divergence between models detected?
- How is Work completion evaluated at a long horizon?
- How are large Plans progressively elaborated without freezing the future?
- How does Plan Steering invoke SPG without becoming SPG?
