# WIC Software Production SOP × LLM — Architecture and Foundation

Date: 2026-09-18

Updated: 2026-09-21 for the WIC Response Contract Phase 1 refinement.

This document records the architecture direction discovered through recent Watt
Human Dogfood. The bounded Software Domain Grounding, Context Orchestrator, SOP,
Task Contract, and Decision/Evidence foundations are now implemented under
separate authorization. Full adaptive SOP runtime, management tooling, Pattern
evolution, and evaluation infrastructure remain future work. The
[WIC Response Contract](wic-response-contract.md) supplies the turn-scoped
collaboration input consumed by these foundations while preserving the closed
Work Admission, Engineering Semantic Truth, Steering, Production, and delivery
boundaries.

The consolidated layer relationships, SOP guidance principles, Task Contract
direction, and implementation sequence are recorded in the
[Watt AI-Native Software Production Architecture](watt-ai-native-software-production-architecture.md).

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

The current Response Contract layer and the future WIC direction fit together as
follows:

```text
Human free-form expression
    -> LLM semantic interpretation
       + current Semantic / Work / Runtime Reality
       + conversation trajectory
    -> turn-scoped Response Contract: what this answer owes the Human
    -> existing governed semantic / authority / progression boundaries
       [future: Software Domain Grounding and Software Production SOP]
    -> Safe Response Envelope
    -> natural, progressive Conversation realization
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

## 6. Relationship to Engineering Semantic Truth and Response Contract

Engineering Semantic Truth was implemented, qualified, and Human-accepted in
the 2026-09-20 milestone. Its responsibility is:

> What does Watt currently know or believe about the Human's
> software-production intent?

That truth may cover explicit constraints, inferred engineering semantics,
working assumptions, references, quantities, scope, superseded facts, and
provenance.

The intended separation is:

```text
Engineering Semantic Truth
    -> WHAT DO WE KNOW / BELIEVE?

WIC Response Contract
    -> WHAT KIND OF ANSWER / COLLABORATION DOES THIS TURN REQUIRE?

WIC Software Production SOP
    -> FUTURE POLICY INPUTS FOR RELIABLE PROGRESSION / SUFFICIENCY

Steering
    -> FORMAL WHAT NEXT FOR THIS WORK

LLM realization
    -> HOW SHOULD WATT EXPRESS THE GOVERNED TURN NATURALLY?
```

Future WIC SOP logic should consume the implemented Engineering Semantic Truth
wherever possible instead of independently reinterpreting the original Human
text for each decision. Neither Response Contract nor a future SOP replaces
Steering as the owner of formal Work progression.

Response Contract decides turn-scoped interaction form: explore, analyze,
design, decide, answer, diagnose, execute, correct, or report current status. It
sets the primary answer obligation, opening, information and question budgets,
judgment basis, and requested advancement posture. It is interaction evidence,
not a new source of Engineering Semantic Truth or authority to execute. A
request to proceed still uses existing admission and governance mechanisms.

Software Domain Grounding is the next independent layer: richer software-domain
concepts and constraints may inform interpretation and judgment, but must retain
their source and epistemic status. Its architecture direction is captured in
[WIC Software Domain Grounding](wic-software-domain-grounding.md). The related
[Context Orchestration](wic-context-orchestration.md) direction selects what is
needed now without absorbing ECF, while
[Decision and Evidence Architecture](wic-decision-evidence-architecture.md)
keeps rationale, decisions, and evidence distinct. These documents implement no
domain library, Context Orchestrator, Decision Memory service, SOP library, or
Guardian escalation engine.

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

The revised sequence is:

1. Stabilize the current Work / Production / Control Room Human journey.
2. Implement and validate Engineering Semantic Truth for software-production
   semantics as a separate task. **Completed in the 2026-09-20 milestone.**
3. Close the current Human-experience / production phase. **Completed.**
4. Establish WIC Response Contract under its separate authorization.
   **Implemented and ready for Human Review under focused qualification;
   Human Acceptance remains pending.**
5. Implement the bounded Software Domain Grounding foundation while preserving
   Pattern as advisory cognitive structure. **Foundation implemented.**
6. Implement the bounded `Software Production SOP × LLM` foundation, consuming
   Semantic Truth and Response Contract while preserving Steering. **Activity,
   checkpoint, evidence-expectation, Context, and Task Contract foundations
   implemented; full adaptive SOP runtime remains future work.**
7. Establish a WIC Evaluation Corpus as a future supporting capability after
   the architecture it evaluates is sufficiently stable. Candidate sources are
   Watt Dogfood cases, adapted public software benchmarks, and expert-designed
   scenarios. This records direction only; no benchmark infrastructure is
   implemented by the Response Contract phase.

## 10. Status

```text
WIC_SOFTWARE_PRODUCTION_SOP_REDESIGN = ARCHITECTURE_BASELINE / FOUNDATION_IMPLEMENTED

ENGINEERING_SEMANTIC_TRUTH = IMPLEMENTED / QUALIFIED / HUMAN_ACCEPTED

RESPONSE_CONTRACT = IMPLEMENTED / REFINING

RESPONSE_CONTRACT_HUMAN_REVIEW = READY / PENDING_HUMAN

SOFTWARE_DOMAIN_GROUNDING = FOUNDATION_IMPLEMENTED

SOFTWARE_PRODUCTION_SOP = FOUNDATION_IMPLEMENTED / FULL_RUNTIME_PENDING

WIC_EVALUATION_CORPUS = FUTURE_SUPPORTING_CAPABILITY

CLOSED_MILESTONE_BOUNDARIES = PRESERVED

ORIGINAL_FREE_EXPRESSION_PRINCIPLE = PRESERVED

DETERMINISTIC_SKELETON_PLUS_PROBABILISTIC_INTELLIGENCE = FUTURE_ARCHITECTURE_DIRECTION

RESPONSE_CONTRACT_IMPLEMENTATION = SEPARATELY_AUTHORIZED

DOMAIN_GROUNDING_AND_SOP_IMPLEMENTATION_AUTHORIZED = NO

NOT_IMPLEMENTED = PATTERN_STUDIO / PATTERN_MANAGEMENT_UI / PATTERN_EVOLUTION_ENGINE

NOT_IMPLEMENTED = BENCHMARK_OR_EVALUATION_CORPUS / AUTOMATED_KNOWLEDGE_MINING

NOT_IMPLEMENTED = FULL_SOFTWARE_PRODUCTION_SOP
```
