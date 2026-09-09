# Human collaboration experience v3.2 — implementation assessment

Date: 2026-09-09. Starting checkpoint: `9228bf2`.

The Human approved implementation after reviewing the latency/quality plan and
the input-to-response architecture. Priorities are an early useful response,
continuous delivery, time proportional to useful content, grounded professional
judgment, natural warmth, and durable correction/context fidelity. Shortness is
not a quality target in itself.

## Scope and architecture

Keep WIC interpretation/proposals, integrated framing, Guided Design structure,
Conversation expression, and Human authority. Eligible native pre-Work still uses
one physical Provider call; active Work, custom seams, explicit opt-out and
different model/effort settings retain staged execution. No production lifecycle,
database schema, deployment, provider authentication or global SDK settings are
changed by this refinement.

The observed Provider window includes work the application asks the model to do.
It does not exonerate the input/output contract or isolate model compute. Existing
text-first streaming is the baseline, not a new feature. Full structured results
still gate validation and committed completion.

## Implementation hypotheses

1. Coalesced output does not need the full second-model expression handoff after
   the natural response is already generated. Retain explicit WIC answer,
   recommendation and rationale, intent, frame, language and detail mode. Current
   candidate facts/constraints/requests remain full snapshots; current facts and
   objective can populate the compatibility projection without asking the model
   to repeat them. Preserve full staged contracts and all reuse/provenance guards.
2. Replace repeated abstract style requirements with short rules and two small,
   unrelated language examples. Keep schema classifications in structured fields.
   Recommendations should choose a priority using actual user constraints and
   explain a material trade-off, not merely name the next design artifact.
3. Give pending input a separate browser outbox. Do not insert it into the active
   Turn's source basis. Submit only after observing committed prior completion;
   pause after failure, uncertain acknowledgement or refresh. This is a local
   continuation aid, not durable server-side queuing or exactly-once delivery.
4. Reuse conversation DOM nodes and render stream deltas at animation-frame
   boundaries. No artificial typing delays. Preserve drafts, scroll and session
   identity across delivery and asynchronous refreshes.
5. Expose the effective pipeline route and reason before a call. Compare common
   model/effort settings on the same route; changing only one side can introduce
   an additional serial call. Do not lower defaults solely on expectation.

## Validation design

The exact starting source was frozen before edits. A fresh isolated
`spg_pipeline_*` database supplies the built-in Chinese A–E sequence. New probe
observations record true delta times, first complete sentence, maximum inter-delta
gap, text closure, committed completion and the full immutable basis/hash. A
punctuation-detected first sentence is not automatically a useful answer.

Fixed-basis replay isolates conversation-history drift. It emits unadmitted
candidates only, so its completion clock must not be compared as if it included
HTTP delivery and database commits. Keep failed and intermediate hypotheses.
Additional multi-turn cases cover one-person/deadline constraints, rejected
directions, persistent corrections, deferred questions and requested detail.

Structural tests protect contracts; complete real replies require separate
qualitative review. Browser tests use a local in-memory fixture and do not
exercise a production database. Human product acceptance remains separate.

## Retained constraints

Full Human source history remains available; no unproven truncation or extra
summarizing model is introduced. Long-context payload growth is measured as a
remaining limitation. Single-worker scheduling, cross-process claims and
cross-instance streaming require a coordinated multi-user design, not a worker
count change, and are outside this bounded pass.

Official guidance used to frame experiments, not as performance evidence:
[latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization)
and [reasoning controls](https://developers.openai.com/api/docs/guides/reasoning).
The installed pinned SDK is the authority for available transport parameters.

The [v3.2 implementation evidence](../evidence/human-collaboration-experience-v32.md)
records completed validation, unsuccessful hypotheses and the unresolved
first-text and naturalness limits.
