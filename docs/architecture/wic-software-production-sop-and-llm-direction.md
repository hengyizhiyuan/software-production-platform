# WIC Software Production SOP × LLM — Future Architecture Direction

Date: 2026-09-18

This document records a future architecture direction discovered through recent
Watt Human Dogfood. It is not an implementation specification, does not reopen
the current WIC architecture, and authorizes no change to prompts, runtime
behavior, Work Admission, Steering, Production, Conversation, or UI.

Repository Reality remains authoritative.

## 1. Why this direction exists

Watt intentionally lets Human expression remain free-form. WIC uses language
intelligence to infer intent, refine understanding, propose useful next moves,
and respond naturally. This avoids turning Watt into a traditional workflow
system with an AI chat shell, and that principle remains valuable.

Recent Human Dogfood shows that a commercial software-production system cannot
depend too heavily on an LLM independently and probabilistically deciding:

- what the Human meant and which facts are currently true;
- whether enough is known for the current step;
- whether production may proceed or Human confirmation is required;
- what should happen next; and
- how the same expression should later be understood by Production and
  Verification.

Observed failure evidence includes repeated ceremonial confirmation; “开始 / 继续”
causing another explanation of how to start; `8×5` receiving inconsistent
meanings across conversation and implementation; side questions disturbing the
Work path; status questions entering unnecessary semantic/provider paths;
malformed Provider output affecting progression; inconsistent Attention/Action
ownership; and semantic output carrying too much production-control meaning.

These findings calibrate the original assumption: production-critical truth and
control semantics should not remain mostly implicit inside LLM output.

## 2. Candidate architecture principle

> Human expression may remain free. Production semantics should become
> increasingly structured. LLM expression may remain natural.

The future WIC direction should study this cooperation:

```text
Human free-form expression
    -> LLM semantic interpretation
    -> governed structured semantic state
    -> deterministic SOP / sufficiency / policy / transition logic
    -> selected interaction or production move
    -> LLM natural realization
```

The structured state and deterministic decisions belong inside Watt. They
should improve consistency and progression without making the Human complete
traditional forms.

The existing principle is preserved and strengthened:

> Pattern constrains AI's search space, not Human expression space.

Pattern, Schema, SOP, and Policy may become part of a deterministic production
skeleton rather than optional prompting assistance alone. Their role is to
protect semantic consistency, progression, authority, sufficiency, state
transition, evidence, and quality. The exact representation and ownership are
not decided here.

## 3. Deterministic skeleton and probabilistic intelligence

The candidate boundary for later study is:

| Deterministic skeleton tends to own | Probabilistic intelligence tends to own |
|---|---|
| Governed truth, authority, and state | Natural-language understanding |
| Semantic facts and constraints | Interpretation proposals |
| Lifecycle and allowed transitions | Solution generation and creative exploration |
| Step-scoped sufficiency and material blockers | Professional judgment within bounded authority |
| Evidence linkage and quality gates | Recommendations and contextual adaptation |
| Next-owner responsibility | Explanation and natural conversational realization |

This table is directional, not frozen ownership. A future architecture phase
must determine the correct boundary and preserve existing domain authority.

LLMs remain central to understanding, contextual reasoning, options,
recommendations, explanation, and natural interaction. Watt-owned structures
should carry the production-critical truth and control that must remain stable
across model calls and downstream consumers.

## 4. Guardrail: do not build a traditional workflow engine

This direction must not evolve Watt into:

```text
traditional requirement forms
    -> rigid category trees
    -> large rule tables
    -> fixed workflows
    -> AI writes friendly wording
```

The target is an adaptive AI-native production experience:

> Human is not constrained by the SOP, while the production system internally
> uses enough SOP to make AI behavior reliable.

Structure must earn its cost. It should constrain production reasoning where
consistency, authority, or evidence matters while leaving Human interaction
natural and responsive.

## 5. Software-production boundary

This future study is specific to Watt's software-production domain. It is not a
universal Human-language SOP framework.

Candidate concerns include Motive interpretation; target/object identification;
desired outcome; engineering semantic facts; constraints; working assumptions;
unresolved questions; material versus non-material unknowns; Work formation;
next-step sufficiency; refinement strategy; Work correction; side-question
routing; new-Motive detection; Human Authority; production readiness;
next-owner selection; clarification necessity; safe defaults; and acceptance
meaning.

## 6. Relationship to Engineering Semantic Truth

Engineering Semantic Truth is a separate near-term architecture task. Its
approximate responsibility is:

> What does Watt currently know or believe about the Human's
> software-production intent?

That truth may cover explicit constraints, inferred engineering semantics,
working assumptions, references, quantities, scope, superseded facts, and
provenance.

The intended separation is:

```text
Engineering Semantic Truth
    -> WHAT DO WE KNOW / BELIEVE?

WIC Software Production SOP
    -> WHAT SHOULD HAPPEN NEXT GIVEN WHAT WE KNOW?

LLM realization
    -> HOW SHOULD WATT COMMUNICATE / CONTRIBUTE NATURALLY?
```

Future WIC SOP logic should consume Engineering Semantic Truth wherever
possible instead of independently reinterpreting the original Human text for
each decision. This document neither designs nor starts that implementation.

## 7. Relationship to Progressive Admission

The future direction builds on, and does not replace, the approved Early
Workspace and Progressive Structuring model:

- `READY_FOR_NEXT_GOVERNED_STEP != WORK_FULLY_KNOWN`;
- sufficiency is scoped to the next governed step;
- reversible unknowns may remain unresolved;
- material blockers for the current step may require Human input;
- the Human may begin under the current explicit understanding; and
- refinement may continue during Work.

Software Production SOP must not restore a “fully refine before production”
gate. Its purpose is reliable progression under bounded uncertainty.

## 8. Questions for the future architecture phase

The later study should investigate, rather than assume answers to:

- Which cognitive steps must always be structurally evaluated?
- Which semantic facts require explicit system state, and which may remain
  natural-language context?
- When may Watt choose a working assumption, and when must it ask the Human?
- How should “开始 / 继续 / 按这个做” map to governed action?
- When should refinement stop and production begin without repetitive
  confirmation?
- How should side questions be routed without disrupting Work?
- How should new-Motive detection interact with one-Work-one-Motive?
- Who selects the next interaction move: deterministic rules, an LLM, or a
  bounded combination?
- How should response form vary by Work stage?
- Which SOP is global to software production, and which is derived from current
  context?
- How can stronger future models receive greater autonomy without redesigning
  the production system?

Real Dogfood failures should be primary architecture evidence for this work,
alongside explicit evaluation and replay, rather than hypothetical examples
alone.

## 9. Sequence

This work is not started now. The intended order is:

1. Stabilize the current Work / Production / Control Room Human journey.
2. Implement and validate Engineering Semantic Truth for software-production
   semantics as a separate task.
3. Close the current Human-experience / production phase.
4. Reopen WIC as a dedicated architecture topic.
5. Study and design `Software Production SOP × LLM` from Dogfood evidence.

## 10. Status

```text
WIC_SOFTWARE_PRODUCTION_SOP_REDESIGN = NOT_STARTED

ENGINEERING_SEMANTIC_TRUTH = SEPARATE_NEAR_TERM_TASK

CURRENT_WIC = PRESERVED

ORIGINAL_FREE_EXPRESSION_PRINCIPLE = PRESERVED

DETERMINISTIC_SKELETON_PLUS_PROBABILISTIC_INTELLIGENCE = FUTURE_ARCHITECTURE_DIRECTION

IMPLEMENTATION_AUTHORIZED = NO
```
