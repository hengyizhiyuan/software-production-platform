# WIC Fast Semantic Reception Slice 1 Qualification

Date: 2026-09-15

Starting revision: `9621821a5330c557769e9d057b0ae3d5a2085ad5`

Frozen corpus digest: `21027361579216bc88ecdcddf9c355f489080cc2ff118fb17052da13519a9f97`

## Implemented architecture

Slice 1 adds a rebuildable Fast Context Card, typed `FastReceptionCandidate`,
deterministic extraction and grounding policy, bounded hosted-model capability,
independent shadow execution, failure observations, and browser timing. Fast
reception receives no database, Work, Plan, PWU, Executor, governance, or
admission service. Its authority is structurally fixed to
`PROVISIONAL_READ_ONLY`; product visibility is `SHADOW`.

The product starts shadow reception after exact basis preparation, submits it to
an independent executor, and immediately continues Deep WIC. It never waits for,
reads, or persists the candidate into product truth. Fast failure cannot fail the
Turn, and only existing Deep WIC creates the single final Watt message.

No schema or migration was needed. Cards are deterministic projections and
shadow observations are bounded process-local evidence. Qualification evidence
is stored offline. Cross-process operational telemetry remains an additive
migration decision.

## Fast Context

Across frozen A–H, cards ranged from 644 to 1,092 serialized bytes, median 894.5
bytes. They retain interaction sequence, basis/source fingerprint, active Work
revision, selected facts and constraints, Human decisions, and governed
references. Full conversation and repository contents are excluded. A sequence,
Work revision, reference, or correction-source change invalidates freshness.

## Qualification lanes

Raw evidence: [`open-wic-fast-reception-runs/2026-09-15-deepseek-flash-low.json`](open-wic-fast-reception-runs/2026-09-15-deepseek-flash-low.json)

| Case | Deterministic lane | Hosted lane | Adjudication |
|---|---|---|---|
| OW-A vague goal | no emission | failed/incomplete | `NO_EMISSION`; no object invented |
| OW-B narrow change | candidate | failed/incomplete | `CORRECT_GROUNDED` |
| OW-C correction | candidate | failed/incomplete | `CORRECT_GROUNDED` |
| OW-D added constraint | candidate | failed/incomplete | `CORRECT_GROUNDED` |
| OW-E possible new object | candidate | failed/incomplete | `CORRECT_GROUNDED`; Work remains Human-owned |
| OW-F privacy authority | candidate | failed/incomplete | `CORRECT_GROUNDED`; violation prevented |
| OW-G low-risk change | candidate | failed/incomplete | `CORRECT_GROUNDED` |
| OW-H reality conflict | no emission | failed/incomplete | `NO_EMISSION`; conflict not guessed |

Deterministic readiness was 0.006–0.017 ms, median 0.015 ms. Six of eight cases
produced safe receipts; two deliberately used Lane C. There were no material
misunderstandings, authority violations, false-confidence emissions, or generic
acknowledgements in deterministic evidence.

## Hosted Provider

The exact profile was DeepSeek `deepseek-flash/low`, 8-second timeout, 256 output
tokens, one tiny seven-field schema, and no retries. All eight requests returned
terminal `incomplete` in 1.92–2.85 seconds (P50 2.12 seconds; observed P95 2.85
seconds). No hosted candidate passed validation. Failure observations retain
purpose, Provider/model/profile, start/terminal time, terminal stage,
request-sent state, usage-known state, retryability, and retry count.

DeepSeek returned no retained usage for the failures. Tokens and RMB cost are
unavailable; they are not claimed as zero. The hosted path is not qualified, and
its terminal time is not successful TTFMS. Another hosted lightweight profile,
or one that completes the tiny schema without consuming its output budget in
reasoning, must be qualified.

## Baseline and latency

Old Deep WIC valid server TTFMS was 9.07–18.93 seconds, median 11.62 seconds.
Deterministic reception safely covers 75% of frozen cases below one millisecond
without Provider cost. OW-A and OW-H remain suppressed. The hosted lane adds
eight failed calls and no safe receipt, so it remains out of product runtime.

`FAST_RECEPTION_LATENCY = PROVIDER_CHANGE_REQUIRED` for the hosted lane. The
architecture remains useful because deterministic explicit reception reaches
the target while suppression is treated as correct behavior.

## Observability

Server timing distinguishes Fast start, candidate ready, no emission, and
failure on the Turn correlation id. Fast observations distinguish first delta,
terminal time, request purpose/profile, usage, failure kind, and retry state.

The browser now records Human send, durable acceptance, first SSE text receipt,
first meaningful text rendered after `requestAnimationFrame`, and final response
under the Turn id. Meaningful text requires sentence closure and at least eight
non-whitespace characters and rejects acknowledgement-only phrases. No visible
debug UI was added. The deterministic Node browser harness passed; no live
production browser sample was persisted, so the gap is **MATERIALLY_NARROWED**.

## Recommendation

- Keep deterministic reception in shadow and extend only explicit grounded forms.
- Keep this DeepSeek hosted Fast profile disabled after its 0/8 qualification.
- Qualify another hosted lightweight profile for OW-A and OW-H.
- In Slice 2 add correction/delta semantics and question-value policy while
  preserving Lane C and OW-F authority.
- Before Slice 3 display rollout, persist correlated browser/server timings and
  rehearse one-response reconciliation.

```text
SLICE_1_RECEPTION_OBSERVABILITY COMPLETE
FAST_CONTEXT_CARD IMPLEMENTED
FAST_SEMANTIC_RECEPTION IMPLEMENTED
FAST_PATH_AUTHORITY PROVISIONAL_READ_ONLY
FAST_PATH_VISIBILITY SHADOW_ONLY
DEEP_WIC_INDEPENDENCE PROVEN
TTFMS_OBSERVABILITY MATERIALLY_NARROWED
FAST_RECEPTION_LATENCY PROVIDER_CHANGE_REQUIRED
SEMANTIC_GROUNDING IMPLEMENTED
OW_F_AUTHORITY_GUARD PASS
OPEN_WIC_BASELINE UNCHANGED
CURRENT_PRODUCTION_WIC UNCHANGED
SLICE_2_READINESS READY_WITH_FINDINGS
```
