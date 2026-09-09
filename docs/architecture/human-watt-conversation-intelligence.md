# Human–Watt Conversation Intelligence

Status: **IMPLEMENTED / FOCUSED VALIDATION PASS / REAL PROVIDER PROOF PASS**

Human Product Acceptance: **PENDING**

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

```text
Human Turn
    -> WIC / relevant Watt domain capability
    -> StructuredCollaborationResult
    -> ConversationContextProvider
    -> ConversationResponseComposer
    -> ConversationProvider
    -> existing streaming Watt message
```

The first implementation separates the existing WIC path into two Provider
contracts:

1. `CodexSdkInteractionSemanticCapability` interprets the exact persisted WIC
   basis and returns advisory domain/collaboration semantics. Its wire schema
   contains no Human-facing response.
2. `CodexSdkConversationProvider` receives only the bounded
   `ConversationContext` and `StructuredCollaborationResult`. It owns natural
   wording, adaptive detail, conversational continuity, and turn-taking.

`CodexSdkWorkInteractionCapability` remains the compatibility facade expected
by `WorkInteractionService`. It composes those two stages, returns the existing
`InteractionAssessmentCandidate`, and therefore does not change the persisted
Interaction, Work-admission, or streaming contracts.

## Structured collaboration result

`StructuredCollaborationResult` is a provider-neutral advisory handoff. It can
express the current turn intent, a direct answer, relevant facts, current
objective/focus, one recommended action and concise basis, an unresolved
Human-owned decision, material alternatives, attention/progression hints,
requested detail, and response language.

It does not contain chain of thought and is not persisted as authoritative
Work, Design, Plan, Evidence, Runtime, or Human Authority. The existing WIC
assessment remains the persisted advisory interpretation; composed wording
remains Conversation History.

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

`ConversationProvider` is a dedicated, replaceable contract. The current Codex
SDK adapter uses an ephemeral read-only, deny-all Turn and a response schema
containing only `natural_response`. Its model is independently configurable
through `SPG_CONVERSATION_PROVIDER_MODEL`; adapter selection is separated by
`SPG_CONVERSATION_PROVIDER_ADAPTER`. WIC semantic model configuration remains
independent.

Default realization is direct and concise, normally two to five short
paragraphs, one primary recommendation/action, and no more than one material
question. Known facts must be reused. Explicit detail requests expand naturally.
Internal schema versions, stage identifiers, policy enums, Provider contracts,
and private reasoning remain hidden unless relevant system detail is requested.

Guided Design remains proactive: it may frame the problem, recommend discussion
order, identify the next material focus, and explain trade-offs. The language
plane changes expression, not who owns the next Step or product decision.

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

`benchmarks/conversation_quality/` contains 30 Chinese and English cases across
all 13 intents and realistic Watt categories: vague goals, context reuse,
questions, corrections, disagreement, recommendations, decision support,
detail requests, side questions, frustration, Guided Design progression, Human
decisions, limitations, Verification, and Human Attention.

Quality uses deterministic contract/structural assertions plus a bounded
real-Provider subset and Human-reviewable evidence. Dimensions are directness,
naturalness, concision, context fidelity, non-repetition, proactivity, relevance,
decision utility, appropriate detail, metadata leakage, and continuity.
Subjective quality is not reduced to one boolean or brittle exact strings.

## Known limitations

- Human Product Acceptance remains pending.
- Two independent Provider Turns preserve separation but increase latency.
- Context selection is bounded/native; semantic retrieval and full ECF are out
  of scope.
- Existing non-conversational Control Room projections are not redesigned.
- Provider structured output still fails closed; no permissive repair or hidden
  retry is introduced.

## References

- [Human–Watt Collaboration Layer](human-watt-collaboration-layer.md)
- [Guided Design Facilitation Layer](guided-design-facilitation-layer.md)
- [Work Interaction & Closed-loop Refinement](work-interaction-closed-loop-refinement.md)
- [Conversation Quality Benchmark](../../benchmarks/conversation_quality/README.md)
- [Focused Validation](../evidence/human-watt-conversation-intelligence-focused-validation.md)
