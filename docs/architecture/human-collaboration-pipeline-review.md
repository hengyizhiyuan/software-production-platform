# Human collaboration pipeline review

Date: 2026-09-09. Assessment recorded before implementation.

## Observed pipeline

The current path is `POST /turns -> durable Human message + RECEIVED ->
single-worker background queue -> exact WIC basis -> WIC semantic Provider
Turn -> Conversation Provider Turn -> candidate admission -> final Watt
message + COMPLETED`. SSE projects status, transient response deltas, and the
persisted final message. The browser currently fetches Shared Understanding
before attaching SSE.

There are **two serial model Turns, not four**. Design Intent Framing is
already part of WIC's semantic result. Pre-Work Guided Design schema selection
and readiness are deterministic. No evidence justifies merging their owners
or adding a reasoning layer. Both model stages create an independent ephemeral
Codex client and thread; semantic output is buffered and never shown to Human.

Evidence: `providers/codex_interaction.py` (semantic capability, conversation
provider, compatibility facade), `application/interaction.py` (submit_turn,
_process_turn, _assess_current, admit_candidate), `api/http.py` (turn SSE),
`web/app.js` (interaction submission), `application/conversation.py` (assembler).

## Findings and implementation decision

1. Quick durable acknowledgement already exists. Meaningful text still waits
   for semantic completion plus expression startup and generation. Each stage
   inherits an Executor timeout and SDK-default model reasoning settings;
   actual provider delay needs measurement, not an assumed model diagnosis.
2. Semantic context serializes the entire persisted basis, including repeated
   storage/provenance metadata. Preserve source records and authoritative Work
   references; compact transport without inventing a second summary truth.
3. Expression receives stale prior constraints/requests rather than the current
   semantic candidate. Corrections can merge contradictory old and new facts.
4. Expression receives recent Human messages but only one previous Watt reply,
   losing the actual dialogue needed for follow-up questions.
5. Shared service workers serialize unrelated interactions. Concurrency cannot
   safely increase while provider provenance is shared mutable instance state;
   defer that change rather than weaken ordering or evidence.
6. Existing lifecycle timestamps and streaming booleans do not measure first
   meaningful text or attribute time to semantic versus expression stages.

The minimal implementation will keep the two provider-neutral contracts and
ownership boundaries; deliver current semantic context and bounded real
dialogue; reduce avoidable transport/prompt repetition; expose independent
bounded reasoning configuration if supported by the pinned SDK; attach SSE
immediately after acknowledgement; and measure stage and delivery latency.
Default model replacement and a fused semantic/wording schema are not justified
without comparative quality evidence. Shared process reuse may be evaluated,
but must preserve replaceable providers and fail-closed transport behavior.

## Recommended responsibilities and scheduling

| Capability | Responsibility | Execution |
| --- | --- | --- |
| WIC + integrated framing | One advisory interpretation; object/context distinction; corrected candidate facts | One model Turn, background after durable receipt |
| Guided Design | Schema, focus, readiness and governed progression | Deterministic existing application/domain processing |
| Context assembly | Exact source selection, current semantics, bounded ordered dialogue | Deterministic; no summarizing model |
| Conversation Intelligence | Grounded wording, coherence, adaptive detail and turn-taking | One expression Turn; stream validated string field only |
| Admission / persistence | Exact basis validation, append-only assessment, final message | Synchronous bounded transactions outside provider waits |
| Delivery / telemetry | Immediate receipt/status, transient deltas, final reconciliation, durations | Asynchronous projection; no truth ownership |

Cache only immutable schema data or exact-basis completed assessments (the latter
already exists). Do not cache responses across corrections, reuse hidden model
memory, parallelize dependent semantic/expression calls, or admit unfinished
model output. No new Work lifecycle, Project concept, Agent hierarchy, Truth
owner, PWU, Executor, Guardian or SPG change is planned.

## Validation plan

Record request receipt, first status/event, first meaningful response delta,
semantic completion, expression completion and persisted terminal state.
Deterministic transport/HTTP tests prove delivery and ordering; real-provider
samples separately measure provider latency and retain reviewable wording.
Exercise a new operations-management platform, Watt-promotion audience context,
correction to a Web application system, a direct question, and a detailed
explanation request. Preserve failures and distinguish measured observations
from subjective Human acceptance or general latency guarantees.

## Measured refinement decision (before coalesced implementation)

The original source `af1d29595a8f352d0fa0ec6135612895c0347623` completed
five real HTTP/SSE cases. Median first text was 58.447 seconds and median
completion 63.547 seconds. Metadata/context fixes with low/low reasoning did
not reliably remove the delay: correction and direct-question first text still
took 61.361 and 61.533 seconds. Lower effort alone is therefore not a supported
solution; its default will remain unspecified.

This evidence justifies a second, bounded optimization: coalesce the two
physical model calls for pre-Work conversations when their configured models
agree. One strict envelope carries `natural_response` first and WIC `semantics`.
WIC continues to own interpretation and its schema; Conversation continues to
own expression policy; Guided Design still selects structure deterministically;
existing application admission validates the complete candidate against the
exact current basis before persistence. Streaming wording remains provisional
presentation, just as it was before; no partial model output grants Authority.

The single invocation interprets the input once and produces both outputs. It
does not wait for a full semantic JSON ledger to be serialized and a second
Provider to start before emitting wording. This is physical call coalescing,
not a new intelligence owner. Standalone adapters and active-Work semantics
remain supported. Different configured models or an explicit opt-out retain
the separated pipeline, preserving independent-provider selection. Evidence
must distinguish one coalesced Turn from two separate Turns and never invent
separate provenance. Test the full-envelope failure case after streamed prose.

Validate this refinement with the same five scenarios and source provenance.
The earlier two-stage/low-effort samples remain historical evidence, including
regressions. No model replacement or active-Work governance change is justified.
