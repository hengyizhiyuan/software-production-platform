# WIC Response Contract

Date: 2026-09-21

Status: **IMPLEMENTED / HUMAN_ACCEPTED_WITHIN_WIC_INTERACTION_SCOPE** for the
bounded WIC Interaction Intelligence optimization milestone closed on
2026-09-22. The acceptance applies to sampled intent understanding, response
form, exploration, clarification, Question Budget, judgment, Capability
Alignment, and entry usability. End-to-end production Human acceptance was not
evaluated; the status does not claim that WIC, rich response rendering,
long-horizon evaluation, or production experience is complete.

Current qualification observations and their limits are recorded in
[Response Contract Human Review evidence](../evidence/wic-response-contract-review-20260921.md).

## Purpose

Response Contract makes one question explicit before Watt realizes its reply:

> What does Watt owe the Human on this turn?

Correct content can still be a poor response when it opens with background
instead of the answer, asks for unnecessary detail, discusses a settled plan
instead of proceeding, or prematurely executes an exploration. This layer
selects the collaboration posture, information order, and minimum sufficient
depth for the current turn. Conversation still chooses the natural wording.

Three principles govern the layer:

> Explore when the Human is exploring. Design when the Human is designing.
> Execute when the Human is executing.

> Once intent is sufficiently executable, conversational overhead should
> collapse.

This is a turn-scoped interaction contract, not a Work lifecycle state, a new
production pipeline, or a fixed collection of answer templates.

## Ownership and authority

| Owner | Responsibility | Response Contract boundary |
|---|---|---|
| WIC | Interpret the current turn and propose collaboration semantics | Owns the turn's Response Contract |
| Engineering Semantic Truth | Governed engineering meaning, source, epistemic status, and supersession | Consumed; never rewritten by answer form |
| Work / Repository / Runtime Reality | Actual admitted goal and engineering state | Referenced for facts; not inferred from conversational confidence |
| Work Admission / Work Revision / Human authority | Accept the appropriate bounded change | Existing mechanisms still decide whether a proposed move may proceed |
| Steering | Formal `WHAT NEXT` for the Work | An advancement obligation cannot select or dispatch a Plan step |
| Executor | Perform admitted implementation | Receives no execution authority from the contract |
| Conversation | Express the governed answer naturally | Receives and satisfies the contract inside the Safe Response Envelope |
| Guardian | Future assurance sufficiency, independent challenge, and gates | Repeated-failure signal is a seam, not Guardian implementation |

A contract may request `ACK_AND_EXECUTE`; it cannot create a Work, approve a
Candidate, accept delivery, or authorize external effects. An exploration
contract means the current turn requests discussion; it cannot cancel already
admitted production or rewrite the Work's purpose.

Persisting a contract does not make it Product Truth. Its provenance records
why the system selected an answer posture, not proof that its substantive
claims are correct.

## Processing path

```text
Persisted Human turn
    + interpreted TurnIntent / cognitive context
    + current Semantic / Work / Runtime Reality
    + relevant conversation trajectory
    -> turn-scoped Interaction Mode and Response Contract
    -> existing semantic validation, policy, authority, reconciliation
    -> Safe Response Envelope
    -> Conversation Realizer
    -> governed response deltas
    -> API transport and progressive browser text

Requested advancement
    -> existing admission / governance / Steering mechanisms
```

Existing `ConversationTurnIntent`, cognitive maturity, and interaction strategy
remain useful inputs and compatibility structures. They do not become Work
states. The richer contract specifies the response obligation without requiring
the Human to choose an internal mode.

Selection uses contextual interpretation rather than a mapping from exact
fixture sentences to prepared answers. Explicit discussion or execution intent
must be considered together with unresolved authority and current Work Reality.
A topic name such as “login” is not a mode: the same topic can support
exploration, design, assessment, or an executable instruction.

## Contract dimensions

The contract is an immutable, provider-neutral structured value. Its dimensions
are composable; they do not select canned prose.

The first implementation lives in `src/spg/domain/response_contract.py`:
`ResponseIntent` is the semantic interpreter's advisory proposal and
`ResponseContract` is the admitted turn expression decision. The pure
`build_response_contract` function in
`src/spg/application/response_contract.py` consumes the assessment, proposed
response intent, source Human records, and previous turn contract. It does not open a database
transaction or call a production mutator.

`ResponseContract` carries revision `wic-response-contract-v4`, literal
`authority=ADVISORY_ONLY`, the exact `basis_fingerprint`, and source-record
references. Existing `TurnIntent` provides compatibility selection when an older
candidate has no `ResponseIntent`; current interpretation supplies explicit
mode and rationale. The builder contains no Human phrase-matching registry.

| Dimension | Meaning |
|---|---|
| Interaction mode | Kind of collaboration expected now |
| EXPLORE interaction strategy | `OPEN_EXPLORATION` or `INTENT_REFINEMENT`; a turn-local collaboration posture, not a subsystem |
| Design collaboration mode | Optional refinement for divergent exploration, critical review, or convergent decision |
| Primary obligation | The answer or action the turn owes the Human |
| Opening move | Kind of useful information that must come first |
| Response moves | Ordered communication duties, not section headings or fixed sentences |
| Reasoning sequence | Ordered intent for presenting cognition to the Human, not private chain-of-thought or a prose template |
| Information budget | Depth and breadth justified by this turn |
| Question budget | Zero by default; at most one material unresolved decision |
| Judgment stance and basis | Fact, inference, recommendation, assumption, preference, or uncertainty, with the supporting basis |
| Advancement obligation | Requested interaction/progression posture within existing authority |
| Adjacent-insight budget | Optional small extension after the primary obligation is met |
| Provenance and failure signal | Source basis and evidence for selection, prior judgment, or changed diagnostic strategy |

The fields are `interaction_mode`, `explore_strategy`, `design_collaboration_mode`,
`primary_obligation`, `opening_move`, `response_moves`, `reasoning_sequence`,
`information_budget`, `question_budget`, `selected_question`,
`judgment_stance`, `judgment_subject`, `judgment_proposition`, `judgment_basis`,
`judgment_change_accepted`, `material_grounding_snapshot`, `advancement_obligation`,
`adjacent_insight_budget`, `repeated_failure_signature`,
`prior_strategy_failed`, `strategy_revision`, and `decision_basis`.

Domain validation rejects an inconsistent question allowance, a factual
judgment without a proposition and cited basis, direct execution obligations
for exploration/status/answer, adjacent insight before the primary obligation,
and an executable-mode contract with a non-minimal information budget. These
are structural guardrails; they do not certify substantive answer quality.

Obligations cover answering, explaining, diagnosing, recommending, comparing,
assessing, reporting Reality, proposing, executing, correcting, and clarifying a
material blocker. An obligation says what must be delivered. An opening and move
sequence say how to order it. They do not determine the engineering facts.

## Interaction modes and proportional information

### Capability alignment

Before final response strategy selection, the contract records an advisory
Capability Alignment Context derived from the admitted turn intent, production
relevance, current Work context, and the versioned System Capability Reality.
It has three response modes:

- **KNOWLEDGE** — answer the question normally. A technical subject alone does
  not justify mentioning Watt or redirecting the Human into production;
- **PRODUCTION_ADVISORY** — answer the software-domain question first, then make
  one brief factual connection to Watt's governed production workflow when the
  object matches Watt's capability; and
- **PRODUCTION** — route an explicit create/modify/execute goal into the existing
  governed preparation and admission path instead of substituting a generic
  tutorial or large copy-paste implementation.

Capability alignment is expression and routing context only. It cannot admit
Work, change Semantic Truth, select a Steering transition, widen Executor
permissions, or claim execution. It must not become promotional language.

| Mode | Expected contribution | Information budget |
|---|---|---|
| `EXPLORE` | Offer useful possibilities and help structure an open search | Relevant divergence; enough alternatives to advance thinking |
| `ANALYZE` | Explain or assess with grounded reasoning | The rationale and material trade-offs needed to understand or judge |
| `DESIGN` | Shape a coherent solution and its boundaries | Enough detail to evaluate the design and its consequences |
| `DECIDE` | Compare decisive factors and recommend a choice | Focus on differences that matter under the actual constraints |
| `ANSWER` | Answer a bounded question directly | Minimum sufficient explanation |
| `DIAGNOSE` | Explain a symptom using current evidence and a repair/verification path | Focused cause, evidence, uncertainty, and next diagnostic action |
| `EXECUTE` | Briefly acknowledge and request governed progression | Minimal conversational overhead; do not replay settled design |
| `CORRECT` | Address the correction and continue on the justified basis | Acknowledge the changed fact or goal without redoing discovery |
| `STATUS` | Report current Work/Runtime facts | Concise Reality first; no speculative progress claims |

Budgets are semantic rather than a universal word or character limit. An
architecture discussion can require several material trade-offs; an execution
instruction usually needs a short acknowledgement and the actual next step.
Conversely, exploration cannot be reduced to “OK” simply to appear fast.

### EXPLORE interaction strategies

`EXPLORE` supports two explicit, extensible interaction strategies:

| Strategy | Use | Behavior |
|---|---|---|
| `OPEN_EXPLORATION` | The Human benefits from useful divergence and no material decision currently blocks progress | Contribute concrete possibilities and distinctions without manufacturing a clarification gate |
| `INTENT_REFINEMENT` | One admitted unresolved decision materially changes the next product or engineering choice | Preserve what is already clear, explain the decision impact, and ask only the single highest-value question |

Intent Refinement is a Response Contract collaboration strategy, not an
`Intent Refinement Engine`, Agent, Skill, workflow, or new source of truth. The
existing progressive semantic policy ranks admitted question candidates by
decision value and cognitive cost. It selects at most one question and stops
when a safe reversible assumption is available or the next useful decision is
sufficiently clear.

Refinement may clarify the goal, target user, material constraints, success
criteria, and important open decisions. Those concepts remain in the existing
structured understanding, Design Intent Frame, and Semantic Truth governance;
the Response Contract neither duplicates nor promotes them into governed Work
facts. Implementation details are not requested early unless they materially
change the next decision. A settled execution request has no EXPLORE strategy
and therefore cannot reopen discovery through this mechanism.

### Design collaboration refinement

`DESIGN` remains the top-level interaction mode. An optional composable
refinement expresses which kind of design collaboration the turn requires:

| Refinement | Human intent | Response behavior |
|---|---|---|
| `DESIGN_EXPLORE` | Brainstorm or widen possibilities before convergence | Map context, expand the option space, compare, then surface risks and a decision point |
| `DESIGN_REVIEW` | Review an existing proposal or challenge assumptions | State the judgment first, show evidence and weak points, then trade-offs and recommendation |
| `DESIGN_DECIDE` | Compare viable choices and converge | Restate the goal and constraints, compare decisive options, then recommend |

The refinement is not a parallel lifecycle or a replacement taxonomy. It may
be paired with an `EXPLORE`, `ANALYZE`, `DESIGN`, or `DECIDE` top-level mode and
is absent where design collaboration is not relevant.

### Minimum Sufficient Answer

Provide enough information for the Human to understand the issue, make the
current decision, or continue the work; then stop. More explanation is not
automatically better.

Do not append routine tutorials, background, summaries, or extensive option
lists. An adjacent insight is optional and comes only after the current
obligation is satisfied. It must materially help the nearby decision; a small
budget is not a requirement to add a section to every answer. When admitted,
it may advance at most half a step beyond the completed answer.

### Reasoning sequence, opening, and response moves

`reasoning_sequence` governs the order in which useful cognition is presented
to the Human. It does not request hidden chain-of-thought, prescribe headings,
or select canned prose. The Realizer may phrase and compress naturally while
preserving the admitted order. Typical sequences include:

- design exploration: context map → option space → comparison → risks and
  constraints → decision point;
- design: goal → constraints → architecture options → trade-offs →
  recommendation;
- diagnosis: observed symptom → evidence → hypothesis → root cause → fix;
- status: current conclusion → key progress → current owner or next step →
  important limitation;
- executable instruction: acknowledgement → governed progression → result.

These are communication obligations, not wording templates. The Realizer must
preserve natural language and must not display contract field names or enum
assignments to the Human.

## Questions and refinement horizon

A question consumes Human effort. The normal question budget is zero. One
question is justified when the missing answer materially affects the current
result, authority, safety, irreversibility, cost, scope, or acceptance meaning.
Potentially useful information is not automatically a blocker.

Where current policy permits a reversible assumption, proceed on that explicit
basis and accept later corrections. Do not demand full specification before the
next governed step. When a material question is necessary, explain its bounded
purpose: what is already clear, what decision remains, and what can happen once
it is resolved. Prefer a high-information formulation: state the bounded
assumption and explain how the answer would change the next decision, rather
than asking a vague “what do you mean?”. Avoid internal state-machine language
or bundled questionnaires.

The contract's question budget overrides weaker legacy conversational advice.
It does not override Human-owned authority. A zero-question execution posture
must never silently approve an unresolved budget or destructive scope.

The builder admits a question only from an existing selected semantic question
whose disposition is `ASK_HUMAN_NOW`, which blocks the next governed step and
affects a material dimension. Already-available answers, safe reversible
assumptions, or choices Watt is authorized to make exclude the question. A
Human-owned governance boundary takes precedence over execution posture even
when no question has been selected.

## Judgment consistency

> Consistency does not mean stubbornness. Adaptability does not mean
> agreeableness.

A Human challenge is a request to inspect the judgment, not evidence that the
judgment is wrong. Distinguish an unsupported disagreement from a corrected fact,
changed goal, disconfirmed observation, or demonstrated invalid inference.

The prior judgment may change when its basis changes. If no meaningful basis
changed, retain the supported position and explain what the objection does or
does not alter. Do not reflexively apologize and reverse the conclusion; do not
defend a disproven assumption merely for consistency.

Judgment subject distinguishes a new topic from reversal of an existing
position. The material-grounding snapshot records the evidence inventory at the
time the judgment was established: citing a previously available but omitted
fact is not automatically new evidence. A provider's change flag or a new Human
record alone is insufficient. Changed admitted grounds and a stated reason are
needed to accept a revision of the same judgment.

Unbound model-authored facts, constraints, motives, outcomes, and deltas remain
expression material unless grounded in the actual Human source records. Delta
grounding must match its cited source identities. Existing bound Engineering
Semantic Facts and typed supporting Reality references retain their governed
authority. This prevents an interpreter from inventing a new fact and using its
own invention to justify reversing the previous judgment.

Unsupported disagreement uses a decisive-factors budget and a compact
old/new-judgment expression context. A supported basis change can justify deeper
reasoning. Disagreement alone neither admits a Work change nor turns a Fast/Deep
category mismatch into a visible claim that the Human's correction was accepted.

Epistemic expression preserves the difference between:

- `FACT`: grounded current knowledge;
- `INFERENCE`: a conclusion derived from evidence;
- `RECOMMENDATION`: a professional choice under stated goals and constraints;
- `WORKING_ASSUMPTION`: a provisional, revisable basis;
- `PREFERENCE`: an expressed priority or taste;
- `UNCERTAINTY`: a limitation that matters to the conclusion.

Where available, the basis references current Engineering Semantic Facts,
Work/Runtime Reality, source records, or accepted policy. Conversation history
is relevant evidence of a prior position; repeating a model statement does not
turn it into a verified engineering fact. Response Contract does not parse and
bind semantic quantities again or duplicate the Semantic Truth ledger.

## Advancement without new authority

Advancement obligations express the semantic equivalents of answer only,
answer and proceed, propose and wait, ask one blocking question, continue
production, acknowledge and execute, pause for Human authority, and request
replanning.

“Continue” in executable context should request the existing continuation path
with low conversational overhead. “Let's brainstorm” should contribute ideas
without converting tentative suggestions into Work revisions or dispatching a
new production cycle. An execution request in PRE_WORK still respects Work
admission. An active Work request still respects current revision, Human
decisions, and Steering ownership.

The contract can frame or constrain the interaction request; it cannot bypass
the authoritative mechanism that accepts the actual transition. Existing
production is not stopped merely because the Human asks a side question.

### Execute consumes current governed meaning

An `EXECUTE` contract consumes the current Engineering Semantic Truth and Work
Reality. It does not independently reinterpret the original Human phrase,
reopen a settled constraint, or silently replace governed cardinality, scope,
or layout meaning with a convenient implementation assumption. The Safe
Response Envelope therefore projects current semantic facts separately as
`semantic_truth_to_preserve`; the compact execution Realizer input retains
them even when settled design conversation is omitted.

An unspecified implementation detail may use a bounded, reversible default.
That default must not contradict governed meaning and does not become Product
Truth merely because it was convenient during realization. Corrections and
supersession continue through Engineering Semantic Truth and Work Reality,
never through the Response Contract.

## Reality-first status and diagnosis

The existing Watt-owned Work Reality query path remains the preferred path for
current status where deterministic facts are available. It reports persisted
Plan/production/attention state without speculative model reasoning or Work
mutation. A status answer must not claim execution began because a conversation
acknowledged a command.

The Human-facing projection is ordered as current conclusion, key progress,
current owner or next step, and an important limitation only when one matters.
Internal queue states, table names, revision records, and enum labels are not a
substitute for that answer and remain hidden unless the Human requests them.

Diagnosis must similarly separate observed Reality from hypotheses. “Why is
this queued?” calls for the actual waiting condition or an explicit gap in the
available evidence, not a general lesson about queue systems. Missing Runtime
evidence is uncertainty; it is not permission to invent a root cause.

## Repeated-failure signal

Response Contract accepts a signal equivalent to a repeated failure signature
and prior strategy failure. Repeated observation of the same symptom after a
repair changes the diagnostic posture: inspect the failed assumption, seek
independent evidence, or propose a different diagnostic route before repeating
the same fix.

This is a turn-level collaboration response to evidence. It is not a new retry
engine, autonomous escalation authority, or a CSP-specific branch. The
[waterfall Preview case](case-studies/waterfall-demo-csp-loop-and-guardian-recovery.md)
motivates the signal, but the representation must apply to other repeated
failures without recognizing that case by name.

The contract change provides a future Software Production SOP or Guardian
consumer with inspectable evidence that the prior route failed. It does not
itself prove root cause, repair success, or assurance sufficiency.

The first failed strategy asks for challenged assumptions and independent
evidence. A repeated matching signature advances `strategy_revision` and asks
to stop the unproductive route. `REPLAN_REQUEST` remains advisory and cannot
override an unresolved Human authority boundary or a material blocking
question.

## Persistence and governed streaming

Contracts belong to turn-scoped interaction evidence. Existing turn/response
metadata provides replay and diagnostics without creating a new Product Truth
table. The persisted value retains the basis of the selection; it must not be
replayed onto a different turn or Work revision as an evergreen instruction.

`RESPONSE_CONTRACT_READY` records the admitted value alongside the assessment in
the existing append-only response event store. Realization reads the contract
for the exact assessment basis; a mismatched envelope basis is rejected. The
next turn's interpretation receives the previous completed turn's contract as
trajectory. A contract from a failed realization remains failure evidence and
does not replace that completed trajectory.

The Safe Response Envelope carries the contract to the Realizer along with
governed semantic content, reconciliation, and source references. The Realizer
gets the current question and relevant trajectory so it can satisfy the
obligation naturally. Contract-aware expression applies to PRE_WORK and active
Work.

The governed response trust boundary is explicit:

- **PROVISIONAL** — provider text may be visible for responsiveness, but it is
  unadmitted, replaceable, and must not be treated as Conversation or Product
  Truth;
- **GOVERNED** — structured semantics and emitted clauses have passed their
  applicable validation and policy gates, but the response is not yet the
  persisted final Conversation record; and
- **FINAL** — the settled response has been persisted for the exact turn and is
  replayable as governed Conversation evidence.

The normal governed streaming sequence remains:

1. Interpret and validate structured semantics against the exact turn basis.
2. Reconcile policy and authority before final Human-facing realization.
3. Validate bounded realization clauses and emit accepted deltas progressively.
4. Persist/replay response events and render progressive browser text.

In the controlled path, raw Deep WIC prose is not streamed directly to the
Human; accepted Realizer clauses are streamed after governance. A qualified
shadow path may expose text marked `PROVISIONAL` for latency, but it cannot be
promoted to final truth until strict structured validation, reconciliation, and
settlement complete. Adding the contract must not introduce a new
whole-response buffer after governed realization begins. The clause gate can
enforce question allowance and prevent internal contract-label leakage without
waiting for the complete final answer. Suppressing a disallowed question must
not discard a later substantive clause.

### Failure recovery

Provider `response.incomplete` is a failed response, not an empty or successful
answer. The runtime preserves a stable failure class and safe diagnostic
metadata, including provider status, a bounded termination reason, provider
request identity when available, occurrence time, and retryability. Raw
provider payloads and internal exception text are not exposed as Human-facing
Conversation truth.

If a provider completed but violates the strict structured response schema, the
structured boundary permits one bounded repair attempt. That repair may only
restore schema conformance: it must preserve the original business meaning,
must not add facts or authority, must not bypass Semantic Truth or Production
Proposal validation, and must still pass the same strict schema. Exhaustion is
recorded as a schema-violation failure; the invalid payload is never admitted.

A recoverable failed turn retains the Human input and its append-only failure
evidence. The UI may retry that exact turn without asking the Human to resend
the message. Recovery creates a new recovery event and re-enters the normal
governed path; it does not rewrite history, duplicate the Human turn, or convert
provisional text into settled truth.

The shared `response_contract_expression_guidance` function in
`src/spg/application/response_contract_expression.py` supplies the same
obligation and budget guidance to replaceable Realizer providers. The existing
`GovernedDeltaGate` checks bounded clauses against governance constraints and
the contract's question allowance before release. It rejects internal
contract-label assignments before emission. These checks protect mechanically
observable constraints; reasoning quality and naturalness still require the
scenario observations and Human Review.

For a clear executable turn with no material question, Human-owned boundary, or
failed-strategy signal, `governed_contract_realizer_instruction` sends a smaller
expression projection. It retains the current input, controlling contract
dimensions, authority/governance state, constraints, and forbidden claims while
excluding settled design prose and prior dialogue that would invite a recap.
The complete immutable envelope remains available as evidence. Blocked,
uncertain, repeated-failure, and other modes retain their fuller expression
context. This reduces avoidable conversation at its source rather than cutting
off generated text or changing Semantic Truth.

## Verification and regression obligations

Focused verification must cover the contract and its consumption, not merely
construction of an object. It must distinguish generated contract assertions,
deterministic rendering checks, provider-backed observations, and actual Human
Acceptance; one category cannot stand in for another.

| Scenario | Required contract and observable result |
|---|---|
| A. Current queue stall | Diagnosis opens with current cause/evidence, questions normally zero, no scheduling lecture |
| B. One-branch Git question | Answer opens directly, minimum sufficient detail, at most one relevant adjacent insight |
| C. Architecture assessment | Judgment and material trade-offs, enough rationale for a decision |
| D. A/B choice | Decisive comparison and recommendation based on known constraints |
| E. Current progress | Deterministic status, Reality first, no Work mutation |
| F. Continue current work | Brief acknowledgement and existing governed progression |
| G. Unsupported challenge | Review prior basis; no automatic reversal |
| H. Same failed repair | Changed diagnostic posture rather than identical repair advice |
| I. Brainstorm login | Relevant divergence and useful contribution, no premature production |
| J. Implement settled login design | Minimal execution reply, no design recap or unnecessary question |
| K. Broken button, fix it | Focused diagnosis/repair/verification posture under current authority |
| L. Login across modes | Explore, design, and execute produce materially different response duties |

Anti-pattern protection checks that no universal answer structure or closing
question returns; unsupported disagreement does not mutate truth; status does
not invent progress; adjacent insight does not precede the answer; and exact
scenario text is not used as a hard-coded answer registry. PostgreSQL coverage
must check persistence and PRE_WORK/active Work integration. Streaming checks
must cover emitted events and Human-visible progression, not `stream=true`
alone.

Follow the [regression and Golden Journey policy](watt-regression-protection-and-golden-journey-governance.md):
protect the invariant at the cheapest sufficient layer, then use bounded
integration/browser evidence for cross-layer behavior. Full Regression and
the final milestone decision are recorded in the
[WIC optimization closure evidence](../evidence/wic-interaction-intelligence-phase-closure.md).

## Future layers and non-goals

The bounded Software Domain Grounding and Software Production SOP foundations
now supply provider-neutral Pattern, activity, checkpoint, and evidence
contracts consumed through Context Orchestration and Task Contract projection.
They consume the contract's explicit obligations without reinterpreting its
communication preferences as product facts. Full adaptive Pattern/SOP runtime,
management, and evaluation infrastructure remain future work; see
[WIC Software Production SOP × LLM](wic-software-production-sop-and-llm-direction.md).

WIC Evaluation Corpus is a future supporting capability, not part of this
implementation. Its intended purpose is long-term evaluation of interaction
quality, regression, and Human collaboration behavior using Watt Dogfood cases,
adapted public software benchmarks, and expert-designed scenarios. No benchmark
framework, corpus storage, or evaluation pipeline is introduced here.

This milestone does not implement a full domain library, production SOP library,
Guardian engine, ECF, replacement lifecycle, new scheduler, or revised Executor,
Preview, or Delivery architecture. It preserves those existing boundaries.

```text
RESPONSE_CONTRACT = IMPLEMENTED
RESPONSE_CONTRACT_REFINEMENT = IMPLEMENTED
READY_FOR_HUMAN_REVIEW = COMPLETE
SOFTWARE_DOMAIN_GROUNDING = FOUNDATION_IMPLEMENTED
SOFTWARE_PRODUCTION_SOP = FOUNDATION_IMPLEMENTED / FULL_RUNTIME_PENDING
WIC_EVALUATION_CORPUS = FUTURE_SUPPORTING_CAPABILITY
ENGINEERING_SEMANTIC_TRUTH_BOUNDARY = PRESERVED
STEERING_AUTHORITY = PRESERVED
WIC_INTERACTION_INTELLIGENCE_HUMAN_ACCEPTANCE = PASS
END_TO_END_PRODUCTION_HUMAN_ACCEPTANCE = NOT_EVALUATED
```
