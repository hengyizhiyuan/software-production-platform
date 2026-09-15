# Design Intent Framing Layer

Status: **IMPLEMENTED / FOCUSED DETERMINISTIC VALIDATION PASS / REAL PROVIDER PROOF PASS**

Real Provider Validation: **PASS — `gpt-5.6-sol`**

Human Product Acceptance: **PENDING**

## Purpose

Design Intent Framing helps Watt understand what the Human is actually trying
to design, build, change, or review before Guided Design chooses a methodology
and begins facilitation. Fluent conversation cannot compensate for entering
the wrong problem space.

The originating acceptance finding was that an operations-management platform
used to promote Watt could be mistaken for an operations campaign. Promotion,
audiences, social channels, and livestreaming describe business context; they
do not by themselves identify the object being designed.

## Architecture flow

```text
Human Input
    -> WIC interpretation
    -> Design Intent Framing
    -> Guided Design schema selection and facilitation
    -> Conversation Intelligence
    -> Human-facing response
```

Framing is integrated into the WIC semantic Provider result and adds no model
call. Eligible pre-Work interactions now coalesce semantic interpretation and
Conversation expression into one strict Provider envelope; active Work or
separately configured model/effort settings retain two Provider Turns. The
[pipeline review](human-collaboration-pipeline-review.md) records the measured
reason for this transport refinement. WIC continues to own the candidate frame.

## Ownership boundary

| Capability | Responsibility |
| --- | --- |
| WIC | Understand Human input, extract interaction facts, and own advisory interpretation. |
| Design Intent Framing | Candidate design object, scope level, collaboration mode, ambiguity, assumptions, and confidence. |
| Guided Design | Design schema, process, stage, focus, progression, and readiness. |
| Conversation Intelligence | Human-facing wording, conversational coherence, and progressive disclosure. |

The frame is an advisory part of a persisted `InteractionAssessment`. It is not
Work Reality, Design Reality, Human Authority, or a new lifecycle. Persistence
exists so the current understanding, its correction, and its provenance can be
reconstructed after restart.

## Design Intent Frame

The minimum provider-neutral representation is:

```yaml
design_subject: concise description of what the Human wants to create/change
object_type:
  PRODUCT_SYSTEM | BUSINESS_PROCESS | FEATURE |
  OPERATIONAL_ACTIVITY | REVIEW_ANALYSIS | UNKNOWN
business_context: why the object exists
desired_outcome: what success means, when known
scope_level: strategic | product | capability | implementation
collaboration_mode: exploration | design | execution | review
candidate_assumptions: concise provisional assumptions
ambiguities: unresolved framing issues
confidence: calibrated value from 0 to 1
```

The frame contains concise product-relevant interpretation only. It never
stores private chain of thought. `UNKNOWN` requires an explicit ambiguity so
uncertainty cannot be hidden behind an empty classification.

## Object and context separation

The framing rule is to identify the object first, then attach business context:

- “我要做一个电商系统” is `PRODUCT_SYSTEM`;
- “我要给现有运营后台增加直播排期” is `FEATURE`;
- “我想策划一次 Watt 发布直播” is `OPERATIONAL_ACTIVITY`;
- “我要优化研发效率” remains `UNKNOWN` until the Human distinguishes a
  tool, process, AI workflow, or organizational change;
- a Watt-promotion platform remains `PRODUCT_SYSTEM`; promotion channels and
  target audiences remain context.

These are reusable framing classes, not hard-coded product cases.

## Candidate interpretation and Human correction

The frame expresses current understanding, not forced judgment. Ambiguity is
made visible through assumptions, ambiguity statements, calibrated confidence,
and material clarification questions. Conversation should say what Watt
currently believes the object to be and offer one concise correction boundary
when uncertainty matters.

A Human correction supersedes the affected candidate frame in the next
append-only assessment. Historical assessments remain evidence. Watt accepts
the correction without defending its previous interpretation, and Guided
Design selection is recomputed from the corrected frame.

## Guided Design integration

Schema selection now consumes the frame rather than routing directly from
keywords in the Motive text:

- `PRODUCT_SYSTEM` selects the general product/system schema, or the technical
  schema when the framed subject is explicitly technical/architectural;
- `FEATURE` selects existing-product evolution;
- `UNKNOWN`, `BUSINESS_PROCESS`, `OPERATIONAL_ACTIVITY`, and
  `REVIEW_ANALYSIS` do not get forced into the current product/system seed
  schemas. Selection is deferred until an applicable object/schema exists.

This does not create a new schema system. Post-admission Work compatibility is
preserved by the existing text-based Work schema resolver; pre-Work entry now
uses the more precise framed basis.

## Conversation Intelligence integration

`StructuredCollaborationResult` carries the candidate frame to the existing
Conversation Provider. The provider naturally distinguishes what is being
built from why it exists, avoids exposing enum names or confidence numbers in
ordinary prose, and uses candidate language when certainty is limited.

The existing `SharedUnderstanding` API projects the frame read-only alongside
Human expression, Watt interpretation, and governed Reality. No new API route,
frontend state owner, or admission path is introduced.

## Performance and context boundary

- No framing-specific LLM Turn is added.
- The WIC semantic Turn creates the frame together with existing interpretation
  and collaboration semantics.
- Conversation Intelligence receives only the structured result and its
  bounded persisted context.
- No repository inspection, full conversation dump, ECF implementation, or
  provider-specific memory is introduced.

## Persistence and compatibility

Migration `20260909_29` adds one nullable JSONB column,
`interaction_assessments.design_intent_frame`. Historical assessments remain
valid with `null`. New assessments use schema version `wic-assessment-v4`, which
adds the progressive semantic projection without changing Design Intent ownership.

The Watt-native deterministic fallback conservatively produces a frame for
legacy/test capabilities that do not yet emit one. It preserves an unchanged
prior frame and recomputes when the interpreted Motive changes.

## Explicit boundaries

This layer adds no Project entity, Work lifecycle, Design Truth, schema
administration system, agent orchestration, ECF, Work Asset Intake, Plan
ownership, PWU ownership, Guardian ownership, or production authority.

## Validation

Focused deterministic evidence covers product/system, ambiguous improvement,
existing-feature evolution, operational activity, context/object separation,
strict Provider wire schema, persistence, restart reconstruction, Human
correction, schema reselection, and zero Work/production facts. See
[Design Intent Framing Focused Validation](../evidence/design-intent-framing-focused-validation.md).

The bounded real Provider proof used three Human turns to establish an
operations-management platform, add Watt-promotion context, and correct a
possible activity interpretation to an explicit backend-system intent. The
persisted frame remained `PRODUCT_SYSTEM`, Guided Design retained the general
product/system schema, the Human-facing response acknowledged the correction,
and no Work or production fact was created.

## References

- [Work Interaction & Closed-loop Refinement](work-interaction-closed-loop-refinement.md)
- [Guided Design Core](guided-design-core.md)
- [Guided Design Facilitation Layer](guided-design-facilitation-layer.md)
- [Human–Watt Conversation Intelligence](human-watt-conversation-intelligence.md)

## Pipeline review refinement (2026-09-09)

The [Human collaboration pipeline review](human-collaboration-pipeline-review.md)
retains framing inside the single WIC semantic Turn. Technical-methodology
selection now uses the framed design subject alone; incidental database or
performance vocabulary in business context cannot select a technical schema.
The expression handoff receives current candidate semantics and preserves the
difference between promotion audiences and actual system operators. No framing
owner, persistence column, or additional Provider Turn is introduced.
