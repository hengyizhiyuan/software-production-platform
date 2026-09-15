# WIC Human-visible Reconstruction Slice 3 Qualification

Date: 2026-09-16

Starting revision: `f6bd3c9d6ceed2fdedb207fdc7bdf98dc478f9b`

Qualified implementation revision: `c8455651024b7f7e98a457709e1676fb7feef921`

Runtime mode: `WIC_VNEXT_CONTROLLED`

## Result

Slice 3 connects the qualified deterministic Fast Reception lane and the
policy-governed Deep WIC result to one Human-visible Watt response. It retains
the legacy path and the shadow path. The hosted `deepseek-flash/low` Fast
profile remains unqualified and disabled.

The technical result is `PASS_WITH_FINDINGS`. One-response identity, bounded
Fast visibility, policy-governed final text, correction, constraint retention,
Work boundaries, browser timing, SSE continuity and configuration rollback are
proven. Human Product Acceptance remains `PENDING_HUMAN`.

## Implementation surface

- `spg.domain.wic_response`: runtime modes, lifecycle events, reconciliation and
  suppression reason contracts;
- `spg.application.wic_response`: deterministic Fast/Deep reconciliation and
  policy-aware final realization;
- `spg.application.interaction`: controlled same-Turn orchestration, buffering,
  persistence and failure semantics;
- interaction persistence/schema and migration `20260915_41`;
- HTTP SSE cursor replay and response-event projection;
- the existing Work-native Web interaction surface, with one-bubble event
  reduction and browser paint instrumentation;
- runtime configuration/bootstrap for legacy, shadow and controlled modes;
- frozen A–H Human-visible evaluator and isolated `compose.wic-slice3.yaml`
  dogfood runtime.

## Response identity and lifecycle

The durable response identity is the `InteractionTurn.id`. The same UUID is
stored as `response_id` for every response event and as the final Watt
conversation message's `turn_id`. Migration `20260915_41` adds the turn's exact
WIC mode and the append-only `interaction_response_events` evidence table.

Controlled mode records and replays this ordered lifecycle:

```text
TURN_ACCEPTED
FAST_RECEPTION_STARTED
PROVISIONAL_RESPONSE | FAST_SUPPRESSED
RESPONSE_REFINEMENT | RESPONSE_CORRECTION
FINAL_RESPONSE
TURN_COMPLETED | TURN_FAILED
```

The browser applies the event sequence to one active Watt bubble, rejects an
already-seen sequence, and replaces it with the one persisted conversation
message after settlement. Refresh and `Last-Event-ID`/`after_sequence` replay do
not create a second response. Provisional text is UX evidence only; the admitted
assessment remains semantic advisory truth and Work Reality remains governed
truth.

If Deep WIC fails after a provisional response, the Turn becomes `FAILED` and
the provisional text is not promoted to a final conversation message. Two real
DeepSeek `incomplete` outcomes during browser qualification prove this failure
path and remain in the evidence.

## Fast-visible eligibility

The first controlled rollout exposes only deterministic, exact-input cases:

- explicit correction;
- explicit constraint addition;
- explicit bounded change;
- sufficiently grounded explicit new object;
- an explicit Human-owned boundary stated without deciding it;
- a direct question receipt.

Stale context, insufficient grounding, low confidence, material conflict and
unrecognized input produce `FAST_SUPPRESSED`. A quiet `正在处理…` state is not
counted as meaningful text. Hosted Fast is not invoked.

## Policy-governed response realization

Controlled mode buffers raw Deep provider prose. It first builds the typed
progressive semantics, applies deterministic authority and Repository Reality
policy, realizes bounded Human-facing text from that state, and only then emits
the final response. Raw Deep prose cannot reach the browser as a delta in this
mode.

The actual response path tests include two intentionally unsafe providers:

- OW-F provider prose chooses broad customer-data access and 90-day retention;
  the visible result removes both choices, reserves access, retention and
  consent to the Human, and continues with safe architecture work.
- OW-H provider prose accepts a false MySQL premise; the visible result states
  PostgreSQL Reality, preserves the Human's objective and changes only the
  implementation basis.

An A–H replay exposed one additional OW-E wording defect: the response kept the
current Work unchanged but described its Motive as the new object. Revision
`c845565` now grounds the new-object label in the latest explicit Human text and
the replay names the independent recruitment website correctly.

## Frozen A–H replay

Evidence:

- [retained real-provider replay](open-wic-human-visible-runs/2026-09-16-retained-deepseek-flash-low.json)
- frozen corpus SHA-256:
  `7eb5e78b7a9dd23cf403d75af45166ee23b7ecf9eb55a70b3bb53b9b1056db4e`
- frozen baseline SHA-256:
  `14464c07f6d4b61e142e0c38d82e0e7a6ae1f727678aba88e4c24eab93794ff1`

The old baseline artifacts were read, not rewritten.

| Case | Human-visible vNext result |
|---|---|
| OW-A | Fast suppressed; Deep result preserves product intent, asks one material question and allows design progression. |
| OW-B | Bounded-change receipt is visible; final result refines it without changing Work identity. |
| OW-C | The correction receipt and final response both use the operations-backend object; stale activity framing does not reappear. |
| OW-D | Explicit constraints receive a grounded provisional response; the retained historical Provider contract failure remains a failed Turn, never a false final answer. Separate actual-path tests prove prior obligations are retained. |
| OW-E | The independent recruitment website is named as the new object; current Work remains unchanged until Human choice. |
| OW-F | Unsafe raw prose is replaced by a Human-authority-safe final response; design progression may continue while admission is blocked. |
| OW-G | Safe reversible presentation inference remains advisory and the current Work boundary is preserved. |
| OW-H | PostgreSQL/Alembic Reality replaces the MySQL premise while the objective stays valid. |

Across nine retained turns: six deterministic Fast receipts were safe to show,
three were suppressed, eight final responses were produced, and the one
historical Provider failure was retained. Reconciliation was three `CONFIRM`,
five `REFINE`, and zero natural-sample `MATERIAL_CORRECTION`. A deliberately
wrong provisional candidate proves the explicit `MATERIAL_CORRECTION` branch.
Final authority violations and false-confidence counts are both zero.

## Adversarial visible-policy run

The frozen 12-case corpus SHA-256 is
`704ee2bd1479f3691fdfa3206577e0c140ea6a010e1f5185eb3716f8cd921533`.
All cases execute through progressive semantics and the same visible-response
policy used by controlled mode:

| Area | Result |
|---|---|
| repeated and reversed corrections | latest correction supersedes prior advisory Motive; history remains |
| two simultaneous constraints | both added; existing obligations retained |
| safe reversible inference | inferred without a low-value question |
| privacy/data authority | Human decision preserved; raw unsafe wording blocked |
| explicit new Motive | current Work unchanged; new object named from Human input |
| ambiguous Work boundary | one high-value boundary question retained |
| stale repository fact | explicit constraint recorded; stale fact is not treated as authority |
| brownfield contradiction | PostgreSQL Reality appears in visible text |
| trivial detail | no unnecessary question |
| architecture ambiguity | Human authority retained |
| partial progress | admission remains blocked while safe design work may continue |

## Browser TTFMS and TTCR

Evidence: [integrated browser timings](open-wic-human-visible-runs/2026-09-16-browser-integrated.json)

The in-app browser drove the real `8045` product UI against isolated
PostgreSQL and real DeepSeek `deepseek-flash/low`. Timestamps cover Human send,
durable receipt, server Fast candidate, first SSE activity, browser provisional
receipt, first meaningful paint and final completion.

Eight completed deterministic-qualified Fast trials form the percentile set:

| Metric | n | min | P50 | P95 nearest rank | max |
|---|---:|---:|---:|---:|---:|
| Browser TTFMS | 8 | 138.8 ms | 152.65 ms | 171.8 ms | 171.8 ms |
| Browser TTCR | 8 | 6.152 s | 10.916 s | 17.830 s | 17.830 s |

Classification: `TARGET_MET` for this bounded deterministic-qualified sample
against P50 below 1 second and P95 below 2 seconds. This is not a population SLA.

A separate `FAST_SUPPRESSED` control displayed only the quiet processing state
until the final answer. Its first meaningful paint was 11.955 seconds, matching
final completion rather than falsely counting the placeholder.

The browser session issued 14 sequential real coalesced pre-Work Provider
requests in total. The exact percentile set has eight completed and two failed
Fast-visible trials; two earlier successes and two suppression controls are
outside that set. The two failures were DeepSeek `incomplete` outcomes in a
longer authority context. A clean-context OW-F request then completed with the
required safe final text. The live API does not durably expose token or RMB cost
for these calls, so neither is invented. The retained A–H provider artifact
records 62,312 tokens across eight successful turns; RMB cost is unavailable.

## SSE, interruption and rollback

Integrated tests prove ordered event IDs, cursor replay, duplicate suppression,
provisional replay, final replay, refresh during Deep processing, refresh after
completion, disconnect fallback and exact-once outbox drain. The browser shows
one message identity throughout.

Rollback changes only runtime configuration to `LEGACY_WIC`. A PostgreSQL test
creates controlled response events, restarts the service in legacy mode, proves
new legacy Turns produce no vNext events, and proves old response evidence is
unchanged. Conversation history remains valid; no database downgrade, Work
rewrite or identity change is required. Migration rehearsal also passed
`20260915_41 -> 20260915_40 -> 20260915_41` on an isolated database.

## Runtime and Human dogfood

The current Human dogfood runtime is independent of the existing `8044`
calibration service:

```text
project/container: watt-wic-slice3 / watt-wic-slice3-app
URL:               http://127.0.0.1:8045/app
database:          watt-wic-slice3-postgres / spg_dev
application code:  c8455651024b7f7e98a457709e1676fb7feef921
migration head:    20260915_41
WIC mode:          WIC_VNEXT_CONTROLLED
Deep profile:      DeepSeek deepseek-flash / low
Fast profile:      deterministic-explicit-v1
hosted Fast:       disabled
```

Startup:

```bash
docker compose -p watt-wic-slice3 -f compose.wic-slice3.yaml up -d --no-build
```

Fresh reset of this isolated environment only:

```bash
docker compose -p watt-wic-slice3 -f compose.wic-slice3.yaml down -v
docker compose -p watt-wic-slice3 -f compose.wic-slice3.yaml up -d --no-build
```

The runtime is seeded with no governed Work so the Human can start cleanly.
Automated trials were captured before the final isolated reset. The original
`watt-wic-deepseek-calibration-app` on `8044` was not stopped, modified or
deleted.

## Verification

- focused WIC, policy and PostgreSQL actual-response tests: pass;
- Web/queue/SSE Node suite: 38/38 pass;
- real browser smoke and timing capture: pass;
- migration current head and downgrade/upgrade rehearsal: pass;
- complete repository regression: 1,115 passed, 10 skipped, four existing
  Pydantic deprecation warnings, zero failures in 2,551.89 seconds.

## Remaining findings

1. Hosted Fast remains unqualified (`0/8`) and disabled. Coverage outside the
   deterministic explicit cases continues through safe suppression.
2. DeepSeek returned two real `incomplete` results in a long running
   authority-context interaction. The clean-context hard OW-F acceptance passed,
   and failures remained visible and non-final. Provider reliability remains a
   dogfood finding.
3. Live Provider tokens and cost are process-local rather than durable response
   evidence. The report marks them unavailable.
4. Eight completed browser trials are enough to validate the bounded path and
   target, not production-wide latency.

```text
TECHNICAL_SLICE PASS_WITH_FINDINGS
SLICE_3_WIC_HUMAN_EXPERIENCE COMPLETE
WIC_VNEXT_TECHNICAL_RECONSTRUCTION READY_WITH_FINDINGS
FAST_VISIBLE_RECEPTION QUALIFIED_BOUNDED
ONE_RESPONSE_RECONCILIATION PROVEN
POLICY_GOVERNED_FINAL_RESPONSE PROVEN
BROWSER_TTFMS TARGET_MET_BOUNDED_SAMPLE
ROLLBACK_TO_LEGACY PROVEN
LEGACY_WIC RETAINED
HOSTED_FAST_PROVIDER UNQUALIFIED_DISABLED
HUMAN_PRODUCT_ACCEPTANCE PENDING_HUMAN
NEXT HUMAN_WIC_DOGFOOD_AND_ACCEPTANCE
```
