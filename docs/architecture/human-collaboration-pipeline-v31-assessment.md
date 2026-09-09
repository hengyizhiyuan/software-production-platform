# Human Collaboration Pipeline v3.1 — pre-implementation assessment

Date: 2026-09-09. Baseline: the completed, uncommitted v3 coalesced pipeline on af1d295; frozen before v3.1 edits in the acceptance container at /tmp/collaboration-pipeline-v31-before-src. This assessment precedes v3.1 implementation.

## Findings and ownership

1. Conversation-owned shared response policy encourages naming the design object and next decision. WIC direct-answer guidance supplies procedural vocabulary. Together they produce system explanations and compound questionnaires. One question mark does not mean one decision. WIC must continue owning proposed hypotheses and recommendations; Conversation translates them into plain, useful expression.
2. Useful internal framing, readiness, schema and provenance data should remain internal. Human-facing answers need the product understanding, a grounded provisional recommendation, its reason, and a concrete next action. Proposals must not become confirmed Human requirements.
3. Existing real v3 samples show prompts growing from 9,606 to 17,703 characters. Persisted semantic payload excluding reply grows from 2,011 to 4,674 characters: historical meanings account for 2,276 characters in turn five, and an unchanged frame adds 1,010. Raw wire also includes transient collaboration fields. Full source evidence remains necessary; repeated prior responses and schema catalogues are not all necessary in the coalesced prompt.
4. First-text-to-completion tails were 22.46, 31.44, 38.49, 44.38 and 56.00 seconds. Provider duration accounts for approximately 99.6–99.9% of those end-to-end runs. These aggregates cannot distinguish SDK startup, generation, teardown and payload validation. Database or outer orchestration is unlikely to dominate those samples, but fresh Chinese measurements must verify attribution. Model compute itself is not directly observable.
5. Existing streaming already allows presentation text before complete semantic validation. It must continue to withhold candidate admission until full validation and exact-basis checks; final completion follows committed persistence.

## Bounded implementation decisions

- Refine the existing shared Conversation policy and WIC guidance: helpful provisional understanding; at most one independent clarification; supported recommendation, rationale and next action; direct plain answers; productive correction handling.
- Keep complete current facts and source records. Do not incrementally union candidate facts, which could revive corrected assumptions.
- In the eligible coalesced provider wire only, allow explicitly selected, validated indexes to retain unchanged prior meanings. Reconstruct the existing full domain candidate against the immutable basis. Reject invalid or duplicated indexes. Corrections can omit old meanings. Preserve staged/custom-provider contracts.
- Trim only demonstrable coalesced context redundancy, such as schema catalogue, prior readiness and an identical prior reply already present in dialogue. Preserve current intent, Human history, evidence IDs and existing exact-basis fingerprinting.
- Add ephemeral stage observations for natural-response closure, semantic-envelope receipt, validation, admission and persistence. Failed, cached and restarted observations must not fabricate successful timings.
- Benchmark the exact five Chinese A–E turns before and after with the same native provider/model/effort settings, isolated databases, full replies and source fingerprints. Capture SDK/setup/terminal/teardown where observable; label generation windows as provider/network observations, not pure model compute.

No new intelligence owner, lifecycle, production capability, Agent hierarchy or authority is introduced. Historical evidence remains intact. Real quality review and boundary validation precede the user-authorized checkpoint and push.

## First measured v3.1 refinement: decision before a second bounded pass

The first Chinese A–E comparison completed successfully with one Provider Turn
per message and no Work/Runtime rows. Quality is more useful, but speed is mixed:
median first text regressed from 23.84 to 26.51 seconds; median completion moved
from 63.57 to 57.63 seconds, while the mean barely changed. Total prompts grew
because the expanded style policy exceeded removed context. This does not meet
the intended first-response refinement and is retained as an intermediate trial.

A second bounded pass will condense the same expression requirements, remove
active-Work instructions from the eligible pre-Work prompt, and allow explicit
reuse of an unchanged prior frame in the coalesced wire. Reuse must validate an
existing prior frame, require a null replacement field, and be rejected on any
correction turn. The adapter reconstructs the same complete domain frame before
candidate validation. New/corrected frames and all current facts remain complete.
This is transport/context refinement, not a new owner or lifecycle. Repeat all
five Chinese cases with the same model/effort and preserve both measured trials.
