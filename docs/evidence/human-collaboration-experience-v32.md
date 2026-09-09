# Human collaboration experience v3.2

Dates: 2026-09-09–10. Starting checkpoint: `9228bf2`.

## Outcome and scope

This pass implements the Human-approved plan: prioritize useful early text,
continuous delivery, context-sensitive judgment and natural professional language.
It does not impose a short-answer quota. Architecture ownership stays with WIC
for understanding/proposals, Guided Design for structure, and Conversation for
expression. Human authority, exact-basis admission and committed completion remain.

Implementation and validation are distinct from Human product acceptance. The
existing running application and production databases were not replaced. Real
Provider checks used synthetic conversations and isolated acceptance databases.
No Work or execution is authorized by a draft response or browser pending input.

**The experiments do not establish consistently fast first text.** Reduced output
work and better browser behavior are useful improvements, but are not evidence
that model waiting has been solved. Model/default reasoning configuration is
unchanged; the faster experimental configuration did not justify its quality
trade-off in these samples.

## Changes

### Provider contract and expression

Eligible native pre-Work already used one text-first model call. This pass removes
the unused full second-model expression handoff from that call's output. Explicit
intent, direct answer, recommendation, reason, frame, detail mode and language
remain. Full current facts, constraints, requests and material unresolved questions
still reach the existing domain candidate. Compatibility facts/objective are
projected from those current values. Staged output retains its full handoff.

Prior-meaning index/source checks, full corrected frames, explicit frame reuse,
correction rejection of old-frame reuse and final validation are unchanged.
Partial text remains presentation only. There is no early success before the full
structured envelope is validated and the Turn is committed.

The shared wording policy now favors a useful answer in the first sentence, a
specific recommendation grounded in supplied circumstances, a relevant trade-off,
and zero or one material question. It discourages empty acknowledgements, internal
classification narration, repeated discovery, universalizing a recommendation,
flattery and invented user constraints. Two short Chinese wording examples use
unrelated scenarios and explicitly forbid importing their facts. These rules
also affect staged expression; real quality evidence here covers pre-Work only.

`pipeline_selection(basis)` exposes the route and reason without making a call.
Successful evidence includes the selection reason. Matching configured model and
effort values preserve eligible coalescing; changing only one side may introduce
two serial calls. Unset effort is recorded as unset, not asserted to be a known
per-call budget.

On the five immutable baseline inputs, the final instruction is 974 characters
smaller per case: 9,627→8,653; 11,471→10,497; 12,493→11,519;
13,159→12,185; 13,630→12,656 (7.1–10.1%). The JSON schema representation is
8,504→7,089 characters (16.6%). These are character counts, **not tokens** or
latency guarantees. Schema counts use `json.dumps(..., ensure_ascii=False)` with
default separators. Full Human history is retained; no truncation is introduced.

### Streaming and pending input

The UI preserves message DOM nodes and batches streamed changes with
`requestAnimationFrame`, updating the active reply instead of rebuilding history.
There is no artificial typing delay. The composer remains editable during a Turn.

The browser can hold three pending messages per Interaction, twelve per tab.
Pending messages are visibly separate from messages received by the server. They
never enter the running Turn's basis; automatic submission waits for the preceding
Turn's persisted `COMPLETED` state. Clearing a UI busy guard rechecks eligible
pending messages, including completion during Refresh.

Drafts and pending input use tab-scoped `sessionStorage`. Reload restores them but
pauses pending delivery. Failed turns and switching Interaction pause the queue;
resumption is explicit. Uncertain POST acknowledgements are never automatically
retried. Cancellation removes the local pending copy. Storage failure is visible;
closing the tab or clearing storage does not guarantee recovery. This is not
server-side durable queuing or an exactly-once delivery guarantee.

SSE loss falls back to read-only polling; the final persisted reply can be
recovered, but incremental streaming does not reconnect during that Turn. Stale
callbacks are checked against their source, Interaction and Turn.

## Measurement protocol

The original source was frozen before editing. All fixed-input replays reference
the original five-turn Chinese report and validate its complete immutable basis
hash. Replay generates candidates without HTTP, admission or persistence; it does
not feed its answers into subsequent cases. Thus it isolates historical input
drift, but does not demonstrate continuous conversation quality on its own.

HTTP first-text/completion timestamps are measured at client receipt from POST
start. Replay measures SDK-delivered text and candidate-validation completion.
The two boundaries must not be presented as the same end-to-end measurement.
HTTP delivery also includes SSE polling/batching. Provider generation/network
windows include remote waiting and application-requested output; they do not
isolate model compute or absolve the application contract.

The probe records first complete sentence, individual non-whitespace text deltas,
maximum inter-delta gap, natural-text closure, successful completion, resets,
call attempts, prompt sizes and source/script hashes. Sentence completion is a
punctuation heuristic, not a judgment that the sentence is useful. Gaps exclude
initial waiting and the structured tail; those are measured separately. Failures
cannot retain successful completion/tail timestamps.

## Exploratory evidence

All rows below preserve the experiments, including slower or rejected ones.
Each replay row contains A/C/D/E once, on the same original bases. Times are
seconds. These four observations are not a stable latency distribution or p95.

| Condition | First-text median | Candidate-completion median | Text-closed-to-completion median |
| --- | ---: | ---: | ---: |
| Original source, sol, explicit low/low | 23.53 | 54.75 | 27.33 |
| First compact-contract trial, sol, inherited effort | 19.63 | 41.11 | 17.78 |
| Compressed instructions + examples, sol, inherited | 24.75 | 46.05 | 17.85 |
| Same candidate + experimental runtime base instructions | 21.51 | 44.65 | 19.21 |
| Same candidate, luna, inherited | 19.71 | 29.19 | 8.58 |
| Same candidate, luna, explicit low/low | 15.20 | 26.17 | 9.00 |

The initial HTTP baseline (five sequential A–E turns) has first-text median
23.18 s and client completion median 57.34 s. It is not directly comparable to
the replay completion column above. Intermediate source hashes differ from the
delivered source and are retained as experiments, not final-source acceptance.

The installed SDK's model catalogue advertised sol's default effort as low and
luna's as medium. That metadata does not prove the effective inherited budget of
each call. Explicit low did not reliably improve sol. Luna/low was faster in this
small set, but produced more generic direction and repeated object/audience/operator
classification after correction. It was not selected as the new default.

The pinned SDK supports per-thread base instructions, but its Python layer does
not reveal the full inherited runtime prompt. An isolated override did not show
stable benefit and is not part of the product. No priority service tier, global
Codex configuration, authentication change or additional fast-response model is
introduced.

## Final-source sequential evidence

Both runs below use sol with inherited effort and the same five Human A–E inputs.
The final run then continues for four additional turns. Each condition uses its
own generated history, so this table describes the product samples; it does not
isolate instruction changes from history drift. All times are client seconds.

| A–E metric | Original | Final |
| --- | ---: | ---: |
| Median acknowledgement | 0.021 | 0.047 |
| Median first text | 23.175 | 26.606 |
| Mean first text | 23.886 | 23.833 |
| Median first complete sentence | 23.994 | 27.226 |
| Median persisted completion received | 57.345 | 51.888 |
| Mean persisted completion received | 55.462 | 50.570 |
| Median text-closure to completion | 29.975 | 21.261 |
| Median per-turn maximum text-delta gap | 0.207 | 0.216 |

Completion is about 9.5% lower by median in this sample; first-text median is
about 14.8% higher and its mean is effectively unchanged. There is no measured
improvement in network-delivered inter-delta gaps. The browser change reduces
render work; it is not credited with Provider or network acceleration.

| Final turn | First text | Full completion | Text-closure tail | Reply characters |
| --- | ---: | ---: | ---: | ---: |
| A: goal | 27.543 | 51.557 | 21.261 | 110 |
| B: context | 21.627 | 53.921 | 28.460 | 149 |
| C: backend correction | 26.606 | 58.417 | 28.230 | 156 |
| D: document location | 16.697 | 37.066 | 18.842 | 69 |
| E: recommendation | 26.690 | 51.888 | 21.120 | 167 |
| F: budget and deadline | 25.375 | 67.433 | 37.522 | 175 |
| G: rejected attribution / no questions | 24.647 | 70.116 | 38.735 | 255 |
| H: personal-use correction | 26.612 | 59.502 | 30.185 | 159 |
| I: detailed explanation | 15.047 | 66.726 | 26.981 | 991 |

The detailed answer contains substantially more useful text, without a
proportional increase in total time. Conversely, the 37–39 s structured tails
after shorter constraint-heavy replies remain a real product limitation.
Prompt size grows from 8,653 to 15,194 characters across the nine-turn sequence.
This is an observation of retained history, not a long-context stress guarantee.

Delivered product source fingerprint:
`90b5e90556697bb7e0612cd243a8c23603b712360018f69115bf309904f4df6d`.
The complete final HTTP report matches every delivered `.py`, `.js`, `.css` and
`.html` file under `src`. Documentation and benchmark script hashes are tracked
separately.

## Final-source fixed-input comparison

The final check replays A/C/D/E once on the exact original bases, first on the
original source and then on the delivered source. Both use sol, unset efforts,
one call per input and the same corrected observation scripts. Eight calls were
made sequentially, without retry. Input-file and per-case basis hashes match.

| Case | Original first text | Final first text | Original successful completion | Final successful completion |
| --- | ---: | ---: | ---: | ---: |
| A | 23.817 | 22.332 | 48.194 | 45.119 |
| C | 29.148 | 27.273 | 60.870 | 55.628 |
| D | 21.235 | 30.933 | **Failed at 64.265** | 49.073 |
| E | 27.021 | 23.337 | 57.751 | 46.631 |

All-four first-text median is **25.419→25.305 s**; mean is
**25.305→25.969 s**. First text was observed in D before original validation
failed. That does not make it a successful answer. The original failure message
is `Coalesced frame reuse is not allowed for a correction`; its first sentence,
delta timings, failure and source evidence are retained, but the complete rejected
response/envelope was not archived by the probe.

Only A/C/E succeeded in both conditions. On those three matched cases, candidate
completion median is **57.751→46.631 s**, mean **55.605→49.126 s**; text-closure
tail median is **26.734→19.830 s**. Their per-turn maximum delta-gap median changes
**0.128→0.523 s**, so continuous Provider delivery did not consistently improve.
These are candidate-validation clocks, not HTTP committed-completion clocks.

The final source passed all four candidates; the original passed three. One
original failure is insufficient to establish a reliability improvement. This
check supports reduced successful completion/tail work in the matched samples,
with first-text variability still unresolved. It is not a stable benchmark or
evidence of a new first-token SLA.

## Quality review

A separate agent compared four original/candidate replies without seeing their
version mapping. After unblinding: candidate preferred in A/C/E, D tied. This is
four qualitative observations, not a statistical win rate or Human acceptance.
The reviewed candidate preceded two final wording refinements.

The strongest improvement was moving from naming a capability-map document to
choosing a specific workflow and explaining what to defer. The reviewer still
found formal product vocabulary, an empty “可以。” opening and a claim that all
channels necessarily depended on one proposed workflow. The last two prompted
the final policy refinements. Compactness alone was not counted as quality.

The final frozen source then completed all nine Chinese turns in one persisted
conversation, using its own preceding answers. The additional sequence covers
single-developer / 5,000 yuan / two-week constraints, manual maintenance, rejection
of channel attribution and further questions, correction to personal use without
team permissions, and a detailed page/data/workflow explanation. Each input made
one Provider call, produced a final reply matching its reconciled stream, and
created zero Work/Runtime rows. These are synthetic product checks, not Human
acceptance.

The final detailed answer uses three main pages, four suggested data entities,
manual publication records and lead follow-up, and defers integrations, channel
attribution and team/permission features. It retains useful implementation detail
instead of merely becoming shorter. Remaining formality and repeated workflow
language are recorded by the independent review in the comparison artifact.

That final review also found concrete weaknesses: the second reply still sounds
partly like planning an activity; the third and fifth reuse much of the same
workflow; “最符合” is stronger than the comparison evidence supports. In the last
reply, team/permission features are listed as later work even though they should
only be reconsidered if a future multi-user need appears. The content-detail view
is not clearly located within the stated three-page layout. These are remaining
quality issues, not hidden as passed structural checks. Mature advisor quality
and a consistent “understands me immediately” experience are not established.

## Validation and retained limits

Final-source results, source hashes and complete successful replies accompany
this report in the [comparison artifact](human-collaboration-experience-v32-samples.json).
It retains 46 real-call attempts across all conditions (45 succeeded, one original
candidate failed), immutable replay inputs and both independent quality reviews.
The final source completed nine HTTP turns plus four fixed-input candidates.
Automated tests check contracts and
failure behavior; they do not score subjective intelligence or naturalness.

- **350 Python tests passed:** `python -m pytest tests --ignore=tests/integration -m 'not real_codex'`.
- **17 PostgreSQL/HTTP tests passed** on frozen final source in a fresh isolated
  database: pipeline latency, conversation context continuity and WIC pre-Work.
  Real-Provider-marked tests were excluded from this deterministic suite.
- **35 JavaScript tests passed**, including batched stream rendering, pending
  delivery, refresh/failure/stale-event guards and completion during a UI refresh.
- JavaScript syntax and `git diff --check` passed.

The first full-suite invocation through the standalone `pytest` entry point
failed collection because repository namespace packages were absent from
`sys.path`; the documented `python -m pytest` invocation passed. The probe's
failure-bookkeeping edge case was fixed and regression-tested after the frozen
HTTP run had started. Its successful observations are unaffected. Later replays
use the corrected scripts; script hashes are distinct from product source hashes.

The isolated Browser fixture verified typing during streaming, pending-versus-
received display, reload recovery with paused pending input, explicit resume,
one POST per message and no console errors. The fixture used in-memory responses;
it does not replace the separate real HTTP/database/Provider check.

Human product acceptance remains open. Provider first-text variability, vocabulary
that can still sound formal, full-history growth, tab-local queue recovery and
single-worker runtime coordination remain practical limits. Multi-worker claims,
distributed streaming and active-Work model quality need their own bounded work.

See the [implementation assessment](../architecture/human-collaboration-experience-v32-assessment.md)
and [reproduction instructions](../../benchmarks/conversation_quality/README.md).
