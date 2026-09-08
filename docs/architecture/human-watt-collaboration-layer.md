# Human–Watt Collaboration Layer

Status: **IMPLEMENTED / DETERMINISTIC VALIDATION PASS / REAL PROVIDER PROOF PASS**

Closure: **PENDING ARCHITECTURE LEAD REALITY REVIEW.**

## Purpose

The Human–Watt Collaboration Layer turns the existing Work Interaction and
Closed-loop Refinement boundary into a responsive, reconstructable Human-facing
collaboration experience. A Human message is acknowledged immediately, work
continues asynchronously, and the resulting Watt response is persisted and
projected without turning conversation into engineering truth.

The normative boundary is:

> Conversation != Truth.

Conversation records what Human and Watt communicated. WIC assessments remain
advisory interpretations. Work Reality, Design Reality, Plan Reality,
Authority, Verification, and Runtime remain governed by their existing owners.

## Conversation thread model

One `Interaction` remains the durable Human–Watt relationship. Its
`ConversationMessage` records preserve:

- `HUMAN` or `WATT` authorship;
- message content and timestamp;
- delivery/processing status;
- the originating Interaction and Turn;
- interpretation, design-result, and governance references when applicable.

An `InteractionTurn` represents asynchronous processing of one Human message.
The implemented lifecycle is:

```text
RECEIVED -> PROCESSING -> COMPLETED
                       \-> FAILED
```

`WAITING_HUMAN`, `WAITING_PROVIDER`, and `WAITING_REVIEW` remain compatible
future states; they are not implemented by this slice. A second outstanding
Turn for the same Interaction is rejected so persisted order remains explicit.

The previous synchronous record endpoint remains available for compatibility.
The Human-facing UI uses the asynchronous Turn endpoint.

## Async processing and response delivery

Submitting a Turn atomically persists the Human message and `RECEIVED` Turn,
returns an immediate acknowledgement, and schedules bounded background
processing. The application then claims `PROCESSING`, invokes the existing Watt
Native interpretation capability, persists either the Watt message and
`COMPLETED` state or a typed `FAILED` result, and exposes status through the
read API.

The web application subscribes to a Server-Sent Events stream. It receives Turn
status, incremental `message.delta` events, and a final `message.completed`
event. Polling remains a compatibility fallback. This is deliberately SSE over
the current HTTP architecture; it does not add WebSocket infrastructure, an
event bus, or a new workflow system.

The current Codex interpretation adapter exposes a final typed result rather
than provider token events. Consequently, processing status is live, while
message deltas are emitted from the persisted final Watt response after
completion. Provider-token streaming is a known limitation, not a claimed
current capability.

## Persistence and restart

PostgreSQL persists Interaction, Turn, message, status, references, timestamps,
and selected design-schema identity/version/rationale. On startup, persisted
`RECEIVED` or `PROCESSING` Turns are rescheduled through the application seam.
The UI reconstructs conversation and processing state from persisted records.

No part of the reconstruction depends on a provider thread, model session,
chain-of-thought, or the original browser process. Provider output alone still
cannot create Work, Design, Plan, production, or Authority truth.

## Human Authority

Human remains Governor of product direction, material trade-offs, scope, risk,
Work admission, production admission, and acceptance. Watt may organize the
design process, recommend focus, and select an information-gathering strategy
within the admitted interaction boundary. Human approval is not required for
every small reasoning step, but no conversational response silently transfers
governed Authority.

## Control Room projection

The existing Control Room projects the conversation, Turn status, selected
schema, stage, current design focus, rationale, facilitation guidance, progress,
and unresolved areas. These are projections over WIC and Guided Design Reality;
the Control Room does not own or duplicate them.

## Non-goals and limitations

This slice does not implement full ECF, Production Execution Package,
Production Passport, Guardian redesign, external design intake, schema
management UI/backend, a schema marketplace, BPM/workflow editing, multi-user
governance, Workspace hierarchy, or provider-session continuity. Background
work uses one in-process worker and is not a distributed durable queue.

## References

- [Work Interaction & Closed-loop Refinement](work-interaction-closed-loop-refinement.md)
- [Guided Design Core](guided-design-core.md)
- [Guided Design Facilitation Layer](guided-design-facilitation-layer.md)
- [Focused Validation](../evidence/human-watt-collaboration-layer-focused-validation.md)
