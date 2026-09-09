# Human Collaboration Pipeline v3.1 — Product Intelligence and Latency Refinement

Date: 2026-09-09. Scope: bounded refinement of the completed v3 pipeline.

## A. Current Pipeline Reality

Eligible native pre-Work conversations still use one ephemeral Provider Turn to
produce a natural response and WIC semantics. Shared model/effort settings, native
provider/context/composer identity and no active Work are required. Active Work,
custom seams, differing settings and explicit opt-out retain the staged path.
WIC owns understanding and framing; Guided Design owns structure and readiness;
Conversation owns expression. The transport optimization does not combine their
authority. The durable acknowledgement is prepared before provider work; SSE begins without
waiting for provider output.

Useful natural text can arrive first, followed by completion of the same semantic
envelope, full validation, exact-basis admission and final committed persistence.
This is progressive presentation inside the existing call, not a new background
intelligence service. Partial text is never an admitted candidate or completion.

## B. Root Causes Found

The [assessment written before implementation](../architecture/human-collaboration-pipeline-v31-assessment.md)
records the investigation and the decision to refine the first measured trial.

- Response policy encouraged classification and next-stage narration. WIC supplied
  procedural document-answer wording. Counting question marks allowed multiple
  independent questions; brevity alone compressed questionnaires without advice.
- Coalesced input repeated schema descriptions, prior readiness, prior reply and
  historical interpretation metadata. Output reserialized unchanged meanings and
  frames. Full current facts are useful; repeated serialization is not inherently
  useful reasoning.
- Existing provider totals combined startup, generation/network, teardown and
  validation. New observations locate the main wait inside the provider window;
  they do not measure pure model compute or prove all delay is caused by a model.
- The first v3.1 trial improved guidance but grew prompts and regressed median
  first text. Its results are retained, not presented as a performance success.

## C. Implemented Improvements

The application-owned shared expression policy now asks for grounded provisional
understanding, concrete recommendations with rationale and a tangible next action,
at most one independent clarification, productive correction handling and plain
direct answers. It preserves useful detail. The final pass condensed the policy
by about 30% from the first trial and discourages reciting internal classifications.

The eligible coalesced wire explicitly selects retained prior meaning indexes.
Indexes must be unique, valid and tied to the exact immutable basis. New meanings
retain source IDs; existing meanings retain their original provenance. All current
facts, constraints and requests remain full snapshots, with no automatic union of
superseded assumptions.

An explicit strict boolean can reuse an unchanged prior frame, with a null wire
replacement. Reuse requires a prior frame, rejects simultaneous replacement and
rejects a correction intent or new correction meaning. If a prior frame exists,
false reuse plus null replacement is rejected so the service cannot silently
restore an old frame. The adapter expands to the existing complete domain
candidate before validation/admission. New or corrected frames are complete.

Coalesced input omits unused schema catalogue/readiness, compacts indexed prior
meanings and removes an identical previous reply only when recent dialogue already
contains it. Pre-Work excludes active-cycle instructions. Full Human source records
and exact-basis checks remain. Staged contracts and context replacement seams remain.

Ephemeral observations distinguish basis preparation, SDK setup, text closure,
semantic receipt, validation, assessment commit and final-message persistence.
Cache, failure and restart never manufacture successful stages. Review also fixed
legacy composer keyword compatibility, stale provenance after replacing only a
composer provider, and false file-absence guidance for active Work. Active Work
answers now distinguish a requested path, an observed artifact and an unknown path.

## D. Latency Evidence

Three complete, sequential Chinese A–E runs used `gpt-5.6-sol`, inherited effort
(null), the same native single-call path and separate empty migrated databases.
Each run made five Provider Turns, persisted one final Watt response per input
matching its reconciled stream, and created zero Work/Runtime rows. The final
source fingerprint exactly matches the delivered product source.

All times below are seconds from client POST start unless noted.

| Observed median | v3 baseline | First v3.1 trial | Final v3.1 |
| --- | ---: | ---: | ---: |
| Acknowledgement | 0.016 | 0.018 | 0.028 |
| First SSE event | 0.022 | 0.024 | 0.036 |
| First natural text | 23.836 | 26.510 | 18.798 |
| Natural response closed | 25.920 | 31.650 | 22.988 |
| Complete envelope received | 63.423 | 57.466 | 52.739 |
| Final completion received | 63.568 | 57.632 | 52.886 |

| Case | First text before → final | Envelope before → final | Committed success before → final* | Completion received before → final |
| --- | ---: | ---: | ---: | ---: |
| A | 24.052 → 40.944 | 44.058 → 70.079 | 44.129 → 70.187 | 44.217 → 70.261 |
| B | 29.755 → 16.156 | 63.423 → 52.739 | 63.491 → 52.842 | 63.568 → 52.886 |
| C | 16.115 → 39.176 | 52.643 → 72.058 | 52.733 → 72.173 | 52.767 → 72.220 |
| D | 23.643 → 18.798 | 64.413 → 45.796 | 64.474 → 45.900 | 64.557 → 46.076 |
| E | 23.836 → 16.339 | 66.686 → 52.661 | 66.745 → 52.735 | 66.790 → 52.801 |

*Committed success is the service marker after final message/Turn commit, relative to server receipt. The persisted `completed_at` is assigned before that transaction and is not used as its commit clock.

Final first natural text: median 23.836 → 18.798 s (+21.1% reduction); mean 23.480 → 26.283 s (**11.9% slower**).
Final completion: median 63.568 → 52.886 s (+16.8% reduction); mean 58.380 → 58.849 s (**0.8% slower**, effectively unchanged in this small sample).

| Context/output characters | v3 baseline A–E | Final A–E |
| --- | --- | --- |
| Total prompt including policy | 9532, 11890, 13094, 13642, 14109 | 9627, 11519, 12517, 13173, 13671 |
| Raw output envelope | unavailable | 2067, 2534, 2236, 1837, 2222 |
| Explicit frame reuse | unavailable (full output) | False, False, False, True, True |

Provider Turns remain **5 per condition / 1 per Human message**. The first trial had median first text 26.510 s and mean completion 58.793 s, versus 23.836 s and 58.380 s before; that trial is retained as a failed performance hypothesis.

Final observed stage durations (ranges across five turns; seconds):

- Basis preparation: 0.0047–0.0084.
- SDK entry + thread/turn setup: 0.3315–2.8508.
- Provider generation/network window: 45.3327–71.5958.
- After response closure until envelope receipt: 25.3696–31.8934.
- SDK teardown: 0.0328–0.0645.
- Full payload validation + expansion: 0.0003–0.0073.
- Admission through assessment commit: 0.0160–0.0214.
- Final persistence transaction: 0.0082–0.0254.
- Terminal receipt through client completion: 0.1402–0.2800.

These measurements identify the provider generation/network window as the dominant observed wait; they do not isolate remote queuing from model reasoning/serialization. Remaining post-response wait is not database work by default.

Final source fingerprint: `8b7862420ed24a2724f694d8f3afc35707160d683ccf98034612466b61257551`. The final real probe matches all delivered Python/JavaScript/CSS/HTML source hashes exactly; no product source changed after the snapshot.


Same-basis offline comparison (six serialized fixtures, zero Provider calls):
historical basis payloads are 22–23% smaller and whole prompts with history are
3.7–4.0% smaller. The initial prompt is 1.0% larger; the output schema grows from
7,696 to 7,974 characters (+3.61%). This isolates metadata/context trimming from
variable real conversation histories. It does not establish a token or latency
reduction. Source/input hashes and per-fixture counts are in the sample artifact.


The initial baseline SDK did not emit the expected final agent-message item.
Its recorded terminal receipt supplies the conservative full-envelope boundary;
raw wire size is unavailable. Subsequent benchmark versions explicitly record
that fallback and guard failed terminals. Script/source fingerprints and all
samples are retained in the [comparison artifact](human-collaboration-pipeline-v31-samples.json).
Client receipt, server yield, response closure and committed completion are distinct.
A response-string closing quote is presentation completion, not semantic approval.

## E. Conversation Quality Evidence

Reviewed all five Chinese turns in `collaboration-pipeline-v31-before.json` and `collaboration-pipeline-v31-final.json`. This is qualitative agent review of one sequential run per condition, not Human Product Acceptance or a general model-quality guarantee. The intermediate first pass remains separate evidence.

### Per-case observations

| Case | Before → final observation |
| --- | --- |
| A — new platform | Before asks both who operates it and what their work is. Final offers the explicitly provisional “先按一个可修正的假设推进” and a concrete “制定计划—分派执行—跟踪进度—复盘结果” workflow, followed by one workflow question. This adds a useful hypothesis and sketch rationale. “形成闭环” and “下一步适合先产出” remain somewhat formal. |
| B — business context | Before mostly restates fact classifications and repeats the operator/work question. Final uses the supplied channels to propose “渠道发布或直播执行—线索与效果跟踪—复盘” and a workflow sketch. Watt, both audience groups, and all three channels are preserved. The sole explicit question concerns operator roles. The long recap and single dense paragraph still reduce naturalness. |
| C — correction | Both runs accept the backend-system correction. Final advances to “系统边界与核心模块草图” and states responsibilities, channel connections and non-goals, rather than merely asking for users/work. The frame remains the corrected backend in D/E. Residual formality is clear in “设计对象” and “不自动视为后台操作人员”: the response still narrates an internal distinction. |
| D — document location | Before exposes “Work 前引导式设计” and “可审查的生产提案”. Final begins “目前还没有生成或保存设计方案文档，因此尚未确定输出路径”. It answers plainly, invents no path, and explains that file/location will be established before writing. This is a clear direct-answer and naturalness improvement. |
| E — recommendation | Before recommends clarifying operators/workflow, then asks those same questions. Final recommends “系统边界与核心模块草图”, supplies “五个候选模块”, explains why scope precedes detailed pages, and proposes drawing an end-to-end workflow. These are explicitly provisional design suggestions, not implemented features or admitted scope. The answer is more useful despite being longer, but repeats the classification safeguard and ends with a broad roles/access-boundary confirmation. It does not establish that the one-independent-decision policy is universally satisfied. |

### Six quality criteria

| Criterion | Qualitative conclusion |
| --- | --- |
| Naturalness | Improved most clearly in D; only partial improvement overall. A/B/C/E still use formal facilitation phrasing, and C/E repeat classification safeguards. |
| Focus | The platform/backend object remains stable and suggestions concern its workflows, boundaries and modules. E's five-module list is broader than a single first-version priority, so focus is improved over interrogation but not fully resolved. |
| Proactive guidance | Material improvement: supplied facts now support provisional hypotheses, concrete sketches/workflows, rationale and next actions. E is advice rather than another questionnaire. |
| Correction handling | Preserved: C accepts the correction without defense and the corrected frame persists through D/E. No return to designing an operational campaign itself was observed. |
| Context reuse | Preserved and made more useful: Watt, individual developers/small teams, and 公众号/小红书/直播 inform cross-channel design suggestions. The audience is not silently declared to be the operator; internal operators remain an assumption. |
| Direct answering | Improved in D, which states the actual no-file/no-path condition first in ordinary language. E also leads with the requested recommendation. |

No material wrong-object, ignored-correction, invented-file-path or false-authority claim was observed in this five-turn sample. `PRODUCT_SYSTEM` and the general product-system schema remain stable; backend framing survives C through E. Proposed modules are hypotheses, and no response claims they have been built. This sample does not exercise arbitrary constraints or active-Work authority changes; those rely on separate contract tests.

The result supports improved useful guidance and plain direct answers, with residual formality and unresolved product acceptance. Concision, punctuation counts, passing automated tests, and the absence of schema IDs alone are insufficient to establish mature conversation quality.

This is qualitative agent review of representative real replies and frames, supported by
structural checks. It is not a claim that test passage establishes naturalness or
that mature-assistant quality/Human product acceptance is closed. Full replies are
retained for independent review; longer useful recommendations are not penalized
merely for being longer than the original questionnaires.

## F. Architecture Boundary Review

No new intelligence owner, Agent hierarchy, Truth owner, Work lifecycle, Project,
ECF, Executor, Guardian or production capability was added. Work remains the
production center; Human retains Authority. No runtime deployment, repository
integration effect or Trusted Baseline transition was performed by the product.
No database migration was required for these refinements.

Meaning/frame reuse changes only the eligible provider wire. Existing full domain
values are reconstructed and validated before admission. Tests reject foreign
source references, invalid indexes, conflicting/missing frame reuse, correction
reuse, invalid envelopes and stale bases. Live HTTP tests independently gate text,
semantic completion, assessment commit and final-message commit. Cache reuse and
restart preserve honest unknown telemetry and durable failure state.

Validation: **128 focused Python contract tests passed** against final source,
including provider schema, retained meaning/frame guards, staged compatibility,
context fidelity, UI/bootstrap/config and benchmark observation contracts.
**41 PostgreSQL integration tests passed** during the mission (7 separately gated
real tests deselected); the **6 live phase tests were rerun and passed against
final source**. **25 JavaScript tests passed**. The three real runs completed
**15 Human messages / 15 Provider Turns** with all expected intents/product frames,
reconciled persisted replies and no Work/Runtime rows. `git diff --check` passed.
Final stream timeout for the matched probe was 180 seconds in all conditions;
application default remains 120 seconds, with SDK startup outside that limit.

## G. Remaining Limitations

This is one five-turn interaction per condition, not a p95/SLA estimate, concurrency
benchmark or universal causal proof. Multi-turn histories differ because earlier
answers differ. Inherited effort does not establish the provider's effective
reasoning budget. Prompt characters are not tokens; raw wire bytes and model
reasoning are different quantities. First text means first non-whitespace natural
text, not proof that the first fragment already answers the question.

Stable speed improvement is **not demonstrated**. Final B, D and E improve, but
A/C first text regress to 40.94/39.18 seconds and completion to 70.26/72.22 seconds.
Median improvements must be read alongside the worse first-text mean and nearly
unchanged completion mean. The after-text semantic tail still spans 25–32 seconds.
No claim is made that this achieves ChatGPT/Doubao responsiveness. Recommendations
and direct answers improve, while some formal labels and dense recaps persist,
especially in the correction response. Human product acceptance remains pending.

Full source history remains uncapped, and the first turn has no prior meanings or
frame to reuse. Existing single-worker queuing, synchronous SSE polling, startup
outside the stream timeout and lack of a cross-process claim lease remain outside
this bounded change. These are retained limitations, not newly implemented work.

## H. Documentation Updates

Added the pre-implementation assessment, this A–I report and complete sanitized
three-condition Chinese samples. Updated Conversation Intelligence architecture,
README, benchmark instructions, AI_context and the roadmap. The previous pipeline
assessment, English samples, failed low-effort trial and historical unresolved
style/latency findings remain intact. This checkpoint includes the previously
uncommitted v3 implementation plus the present v3.1 refinement.

## I. Commit / Push

The user explicitly authorized a clean checkpoint and normal push after successful
implementation, validation and boundary review. Starting HEAD and remote branch
were `af1d29595a8f352d0fa0ec6135612895c0347623` on
`feature/spg-first-vertical-slice`. This report is included in that checkpoint;
its exact commit ID and verified push result are recorded in the final task
response. No production deployment or Trusted Baseline transition is included.
