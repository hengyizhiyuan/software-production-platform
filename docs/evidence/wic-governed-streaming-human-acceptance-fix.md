# WIC Governed Streaming Human Acceptance Fix

Date: 2026-09-16

Starting revision: `d36e658a2c4898ef330c4c4cc0f3bd8c5a35f774`

Implementation revision: qualified by the checkpoint carrying this evidence

Runtime mode: `WIC_VNEXT_CONTROLLED`

## Current result

The Human finding was reproduced: controlled WIC buffered raw Deep Provider
prose until deterministic policy admission and then exposed the admitted final
paragraph in one `FINAL_RESPONSE`. Governance was correct, but the Human saw no
progressive Deep response.

The bounded fix is implemented and proven through focused tests, a real Codex
Provider runtime and the actual Watt browser UI. The original Windows browser
automation error `CreateProcessWithLogonW failed: 1385` was removed by the
Human's host permission correction; it is preserved here as an earlier host
blocker, not rewritten as a successful first attempt. Human Product Acceptance
remains a separate Human decision.

```text
GOVERNED_STREAMING_REALIZATION IMPLEMENTED
RAW_DEEP_PROSE_STREAMED_TO_HUMAN FALSE
SAFE_SEMANTIC_ENVELOPE IMPLEMENTED
REAL_PROVIDER_SSE_STREAMING PASS
REAL_BROWSER_STREAMING PASS
HUMAN_PRODUCT_ACCEPTANCE PENDING_HUMAN
```

## Architecture and safety boundary

The controlled path now separates semantic authority from expression:

```text
Deep WIC interpretation
    -> progressive semantics
    -> deterministic authority / Repository Reality policy
    -> GovernedResponseEnvelope
    -> replaceable Conversation Realizer
    -> RESPONSE_STREAM_STARTED
    -> RESPONSE_DELTA...
    -> FINAL_RESPONSE
```

`GovernedResponseEnvelope` is immutable expression input, not a new Truth
owner. It carries the exact basis fingerprint, admitted content, Motive/outcome,
facts and constraints to preserve, unresolved Human decisions, assumptions,
one selected question, governance disposition, forbidden claims, references,
policy revisions, response language and provisional reconciliation.

The Realizer owns wording and pacing only. Codex uses a read-only ephemeral
thread with deny-all approval. DeepSeek uses the existing configured
`CONVERSATION_RESPONSE` ModelRuntime profile. Application/domain code depends
on a provider-neutral `GovernedResponseRealizer` protocol, and a deterministic
realizer remains available for tests and fallback composition.

Raw semantic Provider deltas are discarded in controlled mode. Realizer text
passes through a bounded clause gate before visibility. The gate validates a
complete clause against envelope-forbidden claims, then exposes that admitted
clause in at most 32-character visual deltas. This avoids whole-answer
buffering while preventing a forbidden phrase split across Provider chunks
from becoming temporarily visible.

An OW-F browser run also exposed a narrower authority drift: the expression
Realizer invented a 30-day audit-metadata retention period even though the
semantic envelope correctly left retention to the Human. The corrected rule is
that `HUMAN_DECISION_REQUIRED` envelopes use deterministic realization of the
governed content. The semantic Provider still interprets the Turn, while a
replaceable wording model cannot fill in a Human-owned decision. A regression
test uses an intentionally authority-drifting Realizer and proves that it is
not invoked for this disposition.

Only the settled full Watt message enters Conversation History. Provisional and
delta events remain append-only response-lifecycle evidence. A partial safe
stream followed by Realizer failure ends in `TURN_FAILED`, without a false
`FINAL_RESPONSE`, Conversation message, or Work mutation.

## One response identity and reconciliation

`InteractionTurn.id` remains the response identity for provisional,
refinement/correction, stream-start, delta, final and terminal events. The Web
client appends accepted deltas to the existing active Watt bubble and rejects
already-seen sequence numbers. Refresh/cursor replay reconstructs one response
without duplicating text.

Focused evidence covers `CONFIRM`, `REFINE`, and deliberately mismatched
`MATERIAL_CORRECTION`. A late Fast candidate is suppressed once governed
realization has started rather than being inserted ahead of already-streaming
Deep content.

Every controlled Turn records either `FAST_VISIBLE` or `FAST_SUPPRESSED` with a
reason. The deterministic eligibility rules were not broadened.

## Real Provider runtime evidence

The isolated qualification runtime used the current source overlay because the
normal startup correctly activates committed Trusted Baseline code. This avoids
misrepresenting uncommitted code as the Trusted Baseline. Qualification data is
disposable; the runtime is rebuilt from the final checkpoint before Human
retest.

```text
compose project: watt-wic-governed-streaming
URL:             http://127.0.0.1:8046/app
WIC mode:        WIC_VNEXT_CONTROLLED
semantic model:  gpt-5.6-sol
realizer model:  gpt-5.6-sol
Fast profile:    deterministic-explicit-v1
hosted Fast:     disabled
```

Real Provider cases produced these results:

| Case | Result |
|---|---|
| Fast-suppressed ambiguous input | `FAST_SUPPRESSED(UNRECOGNIZED)` followed by 3 governed deltas and one final message. |
| Fast-visible explicit constraint | One provisional event plus 7 governed deltas; one response identity; provisional + deltas exactly reconstructed final. |
| Explicit correction | One provisional event plus 6 governed deltas; `CONFIRM`; one final message. |
| New Motive | `NEW_MOTIVE_CANDIDATE`; 6 governed deltas; no Work automatically created. |
| OW-F Human Authority | Governed deltas contained no broad access, 90-day retention or assumed consent; Human authority was explicit. |
| OW-H Repository Reality | 9 governed deltas; no accepted MySQL premise; PostgreSQL Reality and the existing objective remained visible; governed context stayed `Current persistence uses PostgreSQL.` |

The new Realizer adds one Provider Turn after the semantic Provider Turn. The
retained lineage identifies separate semantic and realization Codex threads and
Turns. The Codex SDK path did not expose durable per-Turn token or monetary cost
for these calls, so neither is fabricated.

## Timing evidence

`TTFMS` is Human send to first meaningful visible text. `TTFSR` is governed
realization start to first admitted Realizer delta. `TTCR` is Human send to
settled final response. These are process-local qualification observations, not
an SLA.

| Case | TTFMS | TTFSR | TTCR | deltas | first-to-last delta | average interval | median interval |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fast suppressed | 32,036.805 ms | 9,400.133 ms | 32,696.450 ms | 3 | 563.001 ms | 281.500 ms | 281.500 ms |
| Fast visible | 37.388 ms | 9,547.324 ms | 41,455.087 ms | 7 | 501.839 ms | 83.640 ms | 3.689 ms |

The suppressed sample truthfully retains Deep semantic latency. In both cases,
once governed realization produced text, multiple independently persisted SSE
deltas arrived over roughly half a second rather than one full-paragraph event.

## Real browser qualification

The six required scenarios were executed through the in-app browser against
`http://127.0.0.1:8046/app`, using the real `gpt-5.6-sol` semantic Provider.
The browser observed actual DOM text over time; API/SSE inspection was not used
as a substitute for these results.

| Scenario | Browser result |
|---|---|
| Explicit constraint | A provisional receipt appeared in about 303 ms. The same Watt article then grew through multiple received chunks and settled once, with no duplicate response. |
| Explicit correction | A provisional receipt appeared in about 287 ms. The same Watt article showed six distinct text states before `COMPLETED`; the correction remained intact. |
| Fast-suppressed ambiguous | Only neutral `正在处理…` was shown before governed content. The page was reloaded during Deep processing; replay reconstructed one coherent final Watt response and the response prefix occurred once. |
| OW-F Human Authority | No access scope, consent or retention value was invented. The response explicitly requested the Human's data-scope, approver and retention decisions. |
| OW-H Repository Reality | The same Watt article visibly grew through four governed content states. It corrected MySQL to PostgreSQL, preserved the Motive and cited Alembic rather than accepting the false premise. |
| New Motive | Watt identified an independent recruitment website as a possible new Work, kept the active PostgreSQL Work unchanged and requested Human confirmation; no Work was automatically created. |

The Web client now queues received `RESPONSE_DELTA` payloads and paints at most
one received chunk per animation frame. This does not fabricate text or use a
CSS animation: every visible increment is an actual admitted response delta.
Terminal settlement and the final response wait until queued deltas have been
painted. This closes the browser-specific burst-coalescing defect where several
valid SSE deltas could previously arrive before one browser paint and appear as
one block.

## Tests and continuity

Focused Python tests cover multiple deltas, exact final reconstruction, OW-F
and OW-H delta safety, Human authority, all reconciliation modes, semantic and
midstream Realizer failure, one response identity, ordered sequence, cursor
replay and final Conversation coherence. The Node Web suite covers same-bubble
growth, one-received-delta-per-frame painting, duplicate suppression, refresh
replay and disconnect fallback.

The local Windows checkout converts the frozen OPEN_WIC JSON bytes to CRLF, so
the existing byte-identity test is reported separately instead of rewriting the
frozen baseline. Missing ignored Native Continuity frozen-plan fixtures were
recreated with the repository's deterministic `--plan-only` generator; no
Provider or benchmark execution was involved.

Final validation results:

```text
focused Python: 38 passed, 6 deselected
focused Web:    39 passed
full Linux target-environment run: 1117 passed, 1 bind-mount byte check failed
frozen byte check in core.autocrlf=false clean Git snapshot: 1 passed
aggregate admitted regression: 1118 passed
compile/import: PASS
uv lock --check: PASS
git diff --check: PASS
```

The same broad run on the Windows host exposed three unrelated Native Executor
retention filesystem failures (`fsync` on a read-only descriptor and a locked
Git object removal). Those exact tests pass in the Linux target environment and
none of their implementation or test paths changed in this mission. The one
Linux bind-mount failure was the already-described CRLF byte conversion; the
exact frozen test passes against clean Git bytes with the expected digest.

## Remaining gate

The technical browser gate is closed. `DEEP_REALIZATION_STREAMING` is proven in
the browser, including same-bubble growth, refresh reconstruction and duplicate
suppression. The remaining gate is Human Product Acceptance in the clean final
runtime; no automated qualification result substitutes for that authority.

## Runtime command

```bash
docker compose -p watt-wic-governed-streaming \
  -f compose.yaml \
  -f compose.e2e.yaml \
  -f compose.wic-governed-streaming.yaml \
  up -d --no-build
```

```text
HUMAN_ACCEPTANCE_BLOCKING_FIX COMPLETE
GOVERNED_STREAMING QUALIFIED
FAST_RECEPTION UNCHANGED
WIC_VNEXT_SEMANTICS UNCHANGED
HUMAN_PRODUCT_ACCEPTANCE PENDING_HUMAN
NEXT HUMAN_UI_RETEST
```
