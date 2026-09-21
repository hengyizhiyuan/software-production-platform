# WIC Response Contract

Date: 2026-09-21

Status: **IMPLEMENTED / READY_FOR_HUMAN_REVIEW** under the current focused
qualification and sampled real observations. Human Review remains a separate
gate; this document does not claim Human Acceptance or milestone closure.

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

Two principles govern the layer:

> Explore when the Human is exploring. Execute when the Human is executing.

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

`ResponseContract` carries revision `wic-response-contract-v1`, literal
`authority=ADVISORY_ONLY`, the exact `basis_fingerprint`, and source-record
references. Existing `TurnIntent` provides compatibility selection when an older
candidate has no `ResponseIntent`; current interpretation supplies explicit
mode and rationale. The builder contains no Human phrase-matching registry.

| Dimension | Meaning |
|---|---|
| Interaction mode | Kind of collaboration expected now |
| Primary obligation | The answer or action the turn owes the Human |
| Opening move | Kind of useful information that must come first |
| Response moves | Ordered communication duties, not section headings or fixed sentences |
| Information budget | Depth and breadth justified by this turn |
| Question budget | Zero by default; at most one material unresolved decision |
| Judgment stance and basis | Fact, inference, recommendation, assumption, preference, or uncertainty, with the supporting basis |
| Advancement obligation | Requested interaction/progression posture within existing authority |
| Adjacent-insight budget | Optional small extension after the primary obligation is met |
| Provenance and failure signal | Source basis and evidence for selection, prior judgment, or changed diagnostic strategy |

The fields are `interaction_mode`, `primary_obligation`, `opening_move`,
`response_moves`, `information_budget`, `question_budget`, `selected_question`,
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

### Minimum Sufficient Answer

Provide enough information for the Human to understand the issue, make the
current decision, or continue the work; then stop. More explanation is not
automatically better.

Do not append routine tutorials, background, summaries, or extensive option
lists. An adjacent insight is optional and comes only after the current
obligation is satisfied. It must materially help the nearby decision; a small
budget is not a requirement to add a section to every answer.

### Opening and response moves

Open with the information the turn requests. Typical moves include:

- diagnosis: current cause or evidenced uncertainty → evidence → fix or next
  diagnostic check;
- assessment: judgment → decisive rationale/trade-off → recommendation;
- status: current Reality → material gap → next owner/action;
- bounded question: direct answer → optional adjacent insight;
- comparison: decisive difference → recommendation under the known constraints;
- executable instruction: acknowledgement → governed progression.

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
it is resolved. Avoid internal state-machine language or bundled questionnaires.

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

## Reality-first status and diagnosis

The existing Watt-owned Work Reality query path remains the preferred path for
current status where deterministic facts are available. It reports persisted
Plan/production/attention state without speculative model reasoning or Work
mutation. A status answer must not claim execution began because a conversation
acknowledged a command.

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

The existing governed streaming boundary remains:

1. Interpret and validate structured semantics against the exact turn basis.
2. Reconcile policy and authority before final Human-facing realization.
3. Validate bounded realization clauses and emit accepted deltas progressively.
4. Persist/replay response events and render progressive browser text.

Raw Deep WIC prose is not streamed directly to the Human to reduce latency.
Conversely, adding the contract must not introduce a new whole-response buffer
after governed realization begins. The clause gate can enforce question
allowance and prevent internal contract-label leakage without waiting for the
complete final answer. Suppressing a disallowed question must not discard a
later substantive clause.

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
milestone closure are outside this task.

## Future layers and non-goals

Software Domain Grounding may later improve the concepts and evidence consumed
by WIC; Software Production SOP may later supply reusable sufficiency and
escalation policy. They should consume the contract's explicit obligations
without reinterpreting its communication preferences as product facts. The
[future WIC direction](wic-software-production-sop-and-llm-direction.md) records
both layers as next work, not completed capabilities.

This task does not implement a full domain library, production SOP library,
Guardian engine, ECF, replacement lifecycle, new scheduler, or revised Executor,
DeepSeek transport, Preview, or Delivery architecture. It neither reopens the
closed prior milestone nor declares Human Acceptance for this new one.

```text
RESPONSE_CONTRACT = IMPLEMENTED
READY_FOR_HUMAN_REVIEW = YES
SOFTWARE_DOMAIN_GROUNDING = NEXT
SOFTWARE_PRODUCTION_SOP = NEXT
ENGINEERING_SEMANTIC_TRUTH_BOUNDARY = PRESERVED
STEERING_AUTHORITY = PRESERVED
HUMAN_ACCEPTANCE = PENDING_HUMAN
```
