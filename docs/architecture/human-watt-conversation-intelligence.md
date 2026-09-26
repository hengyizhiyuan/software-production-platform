# Human–Watt Conversation Intelligence

Status: **IMPLEMENTED / WIC INTERACTION MILESTONE HUMAN ACCEPTED / EXTERNAL RESEARCH QUALIFICATION IN PROGRESS**

WIC Interaction Intelligence Human Acceptance: **PASS (2026-09-22)**;
end-to-end production Human Acceptance: **NOT_EVALUATED**. The earlier
2026-09-16 failure remains historical evidence, not the current verdict.

## Purpose

Human–Watt Conversation Intelligence is Watt's shared Human-facing language
plane. It turns governed collaboration semantics plus bounded conversational
context into natural, direct, context-aware language without becoming a new
source of product or engineering truth.

It addresses findings preserved from the v2.x Human–Watt experience work:
responses could be technically correct yet stiff, report-like, overly shaped
by internal methodology, and below the conversational quality expected from a
mature general AI product.

## Architecture

WIC is an existing instance of the [governed Self-Refine convergence
contract](watt-native-executor-blueprint.md#a1-current-autonomous-production-intelligence-loop):
an intent hypothesis is checked against Human meaning and high-impact
ambiguity; contextual refinement or one minimum-sufficient clarification
precedes a response strategy. Question Budget, interaction-stage matching,
EXPLORE/EXECUTE and the Minimum Sufficient Answer remain authoritative WIC
rules. A clarification is not automatically an incident, and this calibration
does not add questions merely to generate a refinement event. Bounded
provider schema repair is recorded on the owning assessment; failed repair is
recorded on the Turn. Controlled final-response metadata also carries this
observation. Neither raw provider output nor a first interpretation becomes
canonical Human intent merely because it was generated.

```text
Human Turn
    -> WIC / relevant Watt domain capability
    -> Design Intent Frame when the turn concerns design/build/change/review
    -> StructuredCollaborationResult
    -> ConversationContextProvider
    -> policy / Repository Reality / Human Authority
    -> InteractionStrategy
    -> GovernedResponseEnvelope
    -> Conversation Realizer
    -> existing streaming Watt message
```

An explicit public search request is an evidence-acquisition obligation, not
an answer-from-memory obligation. After WIC interpretation, the Turn-local
research path maps Human wording or a model-produced information gap to
canonical read capabilities, a DISCOVERY Task Contract, Connector resolution,
real GitHub/Web providers, and persisted source Evidence. It then forms a
source-linked reply; the original WIC wording cannot be presented as a searched
finding. Provider limits and missing credentials are reported as limits.
See [Public external search and retrieval](watt-ai-native-software-production-architecture.md#public-external-search-and-retrieval-2026-09-25).

The implementation separates the WIC path into two Watt-owned Provider
contracts:

1. the WIC semantic capability interprets the exact persisted WIC
   basis and returns advisory domain/collaboration semantics. Its wire schema
   contains no Human-facing response.
2. the Conversation provider receives only the bounded
   `ConversationContext` and `StructuredCollaborationResult`. It owns natural
   wording, adaptive detail, conversational continuity, and turn-taking.

`WorkInteractionService` receives a compatibility facade that selects
coalesced pre-Work or staged transport,
while preserving both responsibilities, and returns the existing
`InteractionAssessmentCandidate`, and therefore does not change the persisted
Interaction, Work-admission, or streaming contracts.

### Provider-neutral model runtime (2026-09-13)

The default path now routes exact role profiles through `WattModelRuntime`:

```text
WIC_SEMANTIC -----------\
                        PurposeProfileRouter -> ModelProviderRegistry
CONVERSATION_RESPONSE --/                         |
                                              DeepSeek Responses
```

Both roles currently select `deepseek-flash` with low reasoning effort, but
remain independently configured. Compatible pre-Work profiles share one
request; active Work or differing profiles use the staged path. The Registry
owns Provider identity and capability metadata. The Responses adapter owns the
credential handle, endpoint, persistent keep-alive client, strict JSON Schema
transport, streaming events, normalized failures, request identity, usage and
timing. WIC business code contains no DeepSeek branch.

The WIC and Conversation runtime uses the DeepSeek API-key provider contract.
There is no external coding-agent SDK adapter or rollback path. Executor
profile selection remains independent; it may reuse the canonical
`SPG_DEEPSEEK_API_KEY` secret handle without sharing WIC or Executor high-level
inference contracts.

## Structured collaboration result

`StructuredCollaborationResult` is a provider-neutral advisory handoff. It can
express the current turn intent, a direct answer, relevant facts, current
objective/focus, the candidate Design Intent Frame, one recommended action and
concise basis, an unresolved
Human-owned decision, material alternatives, attention/progression hints,
requested detail, and response language.

It does not contain chain of thought and is not persisted as authoritative
Work, Design, Plan, Evidence, Runtime, or Human Authority. The existing WIC
assessment remains the persisted advisory interpretation, including the
reconstructable candidate frame; composed wording remains Conversation History.

## Turn intent behavior

The response-scoped intent set is `DIRECT_QUESTION`, `NEW_GOAL`,
`CONTEXT_ADDITION`, `CORRECTION`, `DISAGREEMENT`, `REQUEST_RECOMMENDATION`,
`REQUEST_DECISION_SUPPORT`, `REQUEST_DETAIL`, `SIDE_QUESTION`,
`CONTINUE_CURRENT_WORK`, `MATERIAL_BRANCH`, `FEEDBACK`, and `HUMAN_DECISION`.

Intent changes expression policy. Direct questions require an answer and put it
first. Context additions are used without forced progression. Corrections and
disagreement are accepted without defensiveness. Recommendation requests receive
a recommendation rather than a questionnaire. Detail requests explicitly enable
expanded explanation. Side questions remain bounded and may return to focus.
These intents do not replace WIC intent ownership or add authoritative state.

## Conversation context assembly

`WattNativeConversationContextAssembler` is the current native
`ConversationContextProvider`. For each response it selects a bounded view of:

- the latest Human message and up to eight recent relevant messages;
- up to twelve known facts;
- up to eight governing constraints and current requests;
- the current objective, collaboration focus, Work/Steering references, and
  unresolved Human attention relevant to the response;
- up to twelve Reality references plus requested language and detail mode.

Inputs come from persisted Interaction records, the prior assessment, and the
active Work context. The assembler does not inject the full conversation,
Design Schema, Work history, repository, or architecture corpus. It reuses
known information before asking for it again.

The `ConversationContextProvider` protocol is the future ECF seam. A later
ECF-backed provider may supply the same bounded contract. The Watt-native
assembler remains a useful fallback; this implementation is not ECF Lite and
does not create parallel context truth.

## Response composer and provider

`ConversationResponseComposer` joins the structured result and bounded context,
selects streaming or non-streaming realization, rejects an empty response, and
returns provider provenance plus text. It does not alter source semantics.

`ConversationProvider` is a dedicated, replaceable contract. The default
adapter uses DeepSeek's stateless Responses API and a response schema containing
only `natural_response`. Its model is independently configurable
through `SPG_CONVERSATION_PROVIDER_MODEL`; adapter selection is separated by
`SPG_CONVERSATION_PROVIDER_ADAPTER`. WIC semantic model configuration remains
independent.

Default realization is direct and concise; a direct answer may be one sentence.
Longer replies use short paragraphs, one primary action, and at most one material
question. Known facts must be reused. Explicit detail requests expand naturally.
Internal schema versions, stage identifiers, policy enums, Provider contracts,
and private reasoning remain hidden unless relevant system detail is requested.

Guided Design remains proactive: it may frame the problem, recommend discussion
order, identify the next material focus, and explain trade-offs. The language
plane changes expression, not who owns the next Step or product decision.

## Interaction strategy

`InteractionStrategy` is the bounded seam between admitted semantics and
Human-facing realization. It classifies the Human's current abstraction level,
cognitive maturity and conversation mode, then selects one primary move:
`ORIENT`, `EXPLAIN`, `PROPOSE`, `COMPARE`, `ANSWER`, `ASK`, `CONFIRM`, `CORRECT`
or `ESCALATE_HUMAN_DECISION`. It also sets the next useful granularity and
whether one question is warranted.

The strategy owns conversational advancement only. It cannot redefine Human
Intent, Work identity or readiness, Repository Reality, or a Human-owned
decision. It also does not author a domain interview or choose the case-specific
question. The configured model reasons from the actual object and supplied
context; deterministic policy only bounds the move, abstraction level, question
allowance, and governance constraints. `ASK` is not the fallback for
uncertainty: an early vague motive is oriented at its current level, a concrete
question is answered, and Human uncertainty receives useful framing or
alternatives before Watt asks for more. Explicit restatement is reserved for
correction, material ambiguity, Human Authority, or a costly constraint.

For a coalesced pre-Work call, the admitted natural wording already comes from
the configured Conversation role. The Realizer seam therefore uses bounded
deterministic streaming after strategy and policy admission instead of issuing
a second serial Provider request. Separately configured or custom pipelines
retain the replaceable Realizer contract.

The implemented [Design Intent Framing Layer](design-intent-framing-layer.md)
now precedes schema selection. It separates the object being designed from its
business context and supplies the same structured frame to Conversation
Intelligence without adding another Provider Turn.

## Watt domain integration

The implemented integration covers WIC/pre-Work Interaction and its existing
Guided Design inputs. Active Work facts, Steering revision references,
constraints, requests, and Human-decision context can enter through the existing
active-Work projection. Small policy hints support later Verification, Human
Attention, Guardian, production-status, and Work-evolution adapters.

Current Control Room Human Attention, Verification, and Runtime surfaces remain
structured projections where they do not presently emit a conversational Watt
message. They are not falsely claimed as migrated. Future conversational
emitters should produce `StructuredCollaborationResult` and use the shared
composer rather than inventing domain-specific personalities.

## Streaming and persistence

The existing v2.1/v2.2 lifecycle is preserved. Only the Conversation Provider's
`natural_response` JSON string is emitted incrementally. Deltas update the same
transient Watt message. Completion atomically persists one final Watt message,
and the UI replaces the transient projection with that persisted message.
Late/reconnected clients reconstruct from Conversation History. Partial deltas
remain bounded process-local presentation state.

## Machine-facing boundary

The language plane never rewrites PWU, Production or Execution Contracts,
Context Packages, Executor inputs, typed domain Provider results, Verification,
raw Guardian Findings/Evidence, repository or Runtime Reality, logs, metrics,
or production lineage.

The invariants are:

> Conversation != Truth

> Provider output != Authority

> Human-facing wording != governed domain state

WIC retains interpretation ownership. Work owns Work Reality. Guided Design
owns design structure/readiness. Plan Steering owns WHAT NEXT. SPG retains
production governance. Human remains the Authority owner.

## Conversation quality benchmark

`benchmarks/conversation_quality/` contains 49 Chinese and English cases across
all 13 intents and realistic Watt categories: vague goals, context reuse,
questions, corrections, disagreement, recommendations, decision support,
detail requests, side questions, frustration, Guided Design progression, Human
decisions, limitations, Verification, and Human Attention. Thirteen experience
recovery cases additionally span an enterprise site, consumer mini program,
mobile application, internal approval system, developer CLI, engineering
infrastructure, content site, vague business idea, domain context, specific
design and factual questions, Human uncertainty, and a long contextual turn.

Quality uses deterministic contract/structural assertions plus a bounded
real-Provider subset and Human-reviewable evidence. Dimensions are directness,
naturalness, concision, context fidelity, non-repetition, proactivity, relevance,
decision utility, appropriate detail, metadata leakage, and continuity.
Subjective quality is not reduced to one boolean or brittle exact strings.

## Known limitations

- The 2026-09-16 Human Product Acceptance result is `FAIL`; the experience
  recovery iteration requires a new Human retest.
- Design Intent Framing focused deterministic validation and its bounded real
  `gpt-5.6-sol` correction proof have passed.
- Active Work and separately configured providers still require two serial Turns.
- A coalesced pre-Work response remains provisional until its full semantic envelope
  validates and admission completes; field order is requested, not guaranteed.
- Context selection is bounded/native; semantic retrieval and full ECF are out
  of scope.
- Existing non-conversational Control Room projections are not redesigned.
- Provider structured output still fails closed; no permissive repair or hidden
  retry is introduced.

## References

- [Human–Watt Collaboration Layer](human-watt-collaboration-layer.md)
- [Guided Design Facilitation Layer](guided-design-facilitation-layer.md)
- [Design Intent Framing Layer](design-intent-framing-layer.md)
- [Work Interaction & Closed-loop Refinement](work-interaction-closed-loop-refinement.md)
- [Conversation Quality Benchmark](../../benchmarks/conversation_quality/README.md)
- [Focused Validation](../evidence/human-watt-conversation-intelligence-focused-validation.md)

## Human collaboration pipeline optimization (2026-09-09)

The [pipeline review](human-collaboration-pipeline-review.md) found two serial
model Turns in the original implementation. Framing remains inside WIC; Guided Design remains deterministic and
owns its schema/readiness. Conversation receives current candidate semantics
and eight actual persisted dialogue messages, including Watt replies. A legacy
source-only Human input is preserved even when no message projection exists.
The complete Human source ledger and exact basis fingerprint are unchanged.

Current advisory facts, constraints, and requests replace stale candidates.
Admitted Work facts/constraints/requests are separate fields in the response
context. The replaceable context-provider protocol is unchanged. Context limits
are selection bounds, not a token-limit or full-history compaction guarantee.

Provider transport omits redundant audit metadata and schema first-focus
priming. Prompts distinguish a business audience from the system's operators
and allow a single-sentence direct answer. The browser attaches SSE immediately
after durable acknowledgement. Independent model reasoning settings and a
collaboration timeout avoid coupling expression policy to Executor settings.

Ephemeral provider evidence records stage durations, prompt character counts,
configured models/efforts, and first non-whitespace response delta. Bounded
service telemetry records receipt, acknowledgement readiness, first server SSE
event, first response text, and committed terminal state. Unobserved milestones
remain null; restart does not invent historical timing. Client-side measurement
in the probe separately establishes delivery latency. No metric owns product
truth or changes the persisted lifecycle.

### Coalesced pre-Work inference

Measured two-stage first-response latency remained above one minute after
lowering reasoning effort. The default pre-Work transport therefore uses one
strict envelope containing `natural_response` and the unchanged WIC semantic
schema. The same invocation supplies one interpretation and its wording;
Conversation's expression policy is shared with the standalone adapter. It
uses the exact current source basis plus bounded actual dialogue, and does not
create a fabricated intermediate intent or a second context/Truth owner.

The provider is asked to emit `natural_response` first. Only that JSON string
is streamed. Complete envelope validation and exact-basis application admission
still precede durable assessment/final-message publication. A later invalid
semantic result fails the Turn and never persists the draft as a completed
Watt reply. JSON field ordering changes latency, never validation requirements.

Coalescing applies only without active Work and when both model and reasoning
settings agree and all provider/context seams use the native implementations.
Custom context/providers, different settings, active Work, or
`SPG_WIC_COALESCE_PRE_WORK=false` retain the separate context/composer/provider
path. The DeepSeek defaults use low effort for both roles. There is no shared
hidden provider memory, model replacement, or change to Human Authority.

Provider evidence reports `coalesced_pre_work` and one request ID, or `staged`
and two request IDs with separate provenance. The legacy adapter continues to
report thread/turn IDs. Stage-only timings/IDs are null in the single-call mode;
no unmeasured phase is inferred.

## Product intelligence and latency refinement v3.1 (2026-09-09)

The [pre-implementation assessment](human-collaboration-pipeline-v31-assessment.md)
identifies policy-induced procedural prose and repeated semantic serialization.
The existing application-owned Conversation policy now guides expression around
useful provisional understanding, a concrete recommendation, its rationale and
a tangible next action. It counts independent decisions rather than punctuation.
WIC still owns interpretation and proposed recommendations; Conversation expresses
them. Correction handling advances from the corrected object, and direct answers
translate product facts into plain language.

Eligible coalesced output can explicitly retain unchanged prior meanings by
validated indexes. The adapter expands those indexes against the exact persisted
basis into the existing complete candidate. Invalid, duplicated and out-of-basis
references fail before admission. Current facts, constraints, requests and frames
remain complete snapshots; no implicit union revives superseded assumptions.
The coalesced prompt omits its unused schema catalogue and prior readiness,
compacts indexed prior meanings, and removes a prior response only when identical
text is already present in recent dialogue. All source records remain available.

Natural-response closure, complete-envelope receipt, payload validation,
exact-basis candidate validation, assessment commit and final-message persistence
are separately observable. Partial text continues to be presentation only. Cached,
failed and restarted observations do not fabricate generation or success stages.
No new persistence schema, intelligence owner, admission authority or lifecycle
was introduced. See the [v3.1 evidence report](../evidence/human-collaboration-pipeline-v31.md)
for real Chinese comparisons and remaining Human Acceptance findings.

### v3.1 explicit frame reuse

The final coalesced transport may explicitly reuse an unchanged prior Design
Intent Frame. A strict reuse flag requires an existing prior frame and a null
replacement field; new/corrected frames remain complete. Correction intents or
new correction meanings cannot reuse a frame. When a prior frame exists, an
unspecified null replacement without explicit reuse is rejected before domain
validation, avoiding implicit restoration by legacy service fallback. Reuse is
expanded into the existing immutable full domain value; no new persisted frame
format or owner is introduced. Full current facts and source records remain.
