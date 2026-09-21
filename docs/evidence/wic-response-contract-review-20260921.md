# WIC Response Contract — Focused Qualification and Human Review

Date: 2026-09-21

Status: **IMPLEMENTED / READY_FOR_HUMAN_REVIEW**.

This document records the separately authorized Response Contract task after the
closed Watt milestone. It distinguishes domain/integration proof, actual
Provider observations, browser observations, and pending Human Review. A
completed Provider turn is not automatically a product-quality pass. The
classification below applies to this implementation, focused checks, and sampled
responses; it is neither a guarantee about all model outputs nor Human Acceptance.

## Repository and scope

```text
START_HEAD = 964f7b6c88cb9e3d216a2674713c1096753d510a
CURRENT_HEAD = 964f7b6c88cb9e3d216a2674713c1096753d510a
BRANCH = feature/spg-first-vertical-slice
WORKTREE = UNCOMMITTED_RESPONSE_CONTRACT_IMPLEMENTATION
COMMIT = NOT_CREATED
PUSH = NOT_PERFORMED
FULL_REGRESSION = NOT_RUN_BY_DESIGN
CLOSURE = NOT_PERFORMED
HUMAN_ACCEPTANCE = PENDING_HUMAN
```

No claim is made that PRE_WORK, Engineering Semantic Truth, Queue/Scheduler,
Native Executor, DeepSeek transport, Preview/Delivery, Guardian, or ECF was
reimplemented or reopened. No domain-knowledge library or full Software
Production SOP was implemented. Current changes add turn-scoped interaction
intelligence and its integration with existing governance.

Canonical architecture:
[WIC Response Contract](../architecture/wic-response-contract.md).
Future-layer status:
[WIC Software Production SOP × LLM direction](../architecture/wic-software-production-sop-and-llm-direction.md).

## Implementation and boundaries

`src/spg/domain/response_contract.py` defines immutable `ResponseIntent` and
`ResponseContract`. Semantic interpretation proposes how to collaborate;
`build_response_contract` in `src/spg/application/response_contract.py` reconciles
that proposal with admitted semantics and completed conversation trajectory.

The contract includes mode, obligation, opening, ordered communication moves,
mode-specific information budget, question budget, judgment subject/stance/basis,
material-grounding snapshot, advancement obligation, optional adjacent insight,
and repeated-failure strategy evidence. Its authority is `ADVISORY_ONLY`.

`ResponseContract` is not a Work revision, semantic fact, Steering decision,
execution grant, or assurance result. Existing admission and authority paths
still decide actual progression. In particular:

- Exploration or a status answer cannot use proposed wording as a Work change.
- A brief execution acknowledgement does not establish that production began.
- Judgment persistence preserves an inspectable position, not engineering truth.
- A prior failed strategy changes diagnostic posture without granting a retry
  or Guardian authority.

The existing response-event store persists `RESPONSE_CONTRACT_READY` with the
assessment. The exact-basis contract reaches the Safe Response Envelope. Only a
completed turn's contract supplies the next turn's trajectory; failed
realization remains historical failure evidence.

Judgment revision additionally checks source records: model-invented unbound
facts cannot become new grounds for reversal simply because the interpreter
wrote them into a semantic proposal. Unsupported disagreement preserves the
supported position, stays non-mutating, and cannot manufacture an accepted
correction through Fast/Deep category mismatch.

The provider-neutral Realizer instruction consumes the contract. Clear
execution uses a smaller expression projection that retains the current input,
controlling contract, authority/governance boundaries, constraints, and forbidden
claims while excluding settled design prose and dialogue that invited recaps.
The full immutable envelope remains evidence. This is context selection, not
truncation of an already-generated response.

The clause gate preserves existing forbidden-claim protection, enforces zero or
one material question, prevents internal contract-label assignments, and emits
accepted text before Realizer completion. English sentence boundaries,
paragraphs, literal quoted questions, code, and URL query strings receive
focused coverage. Raw ungoverned semantic prose is not streamed to the Human.

## Evidence classes and limits

| Class | What it establishes | What it does not establish |
|---|---|---|
| Domain / expression tests | Contract invariants, selection, budgets, judgment and gate behavior under controlled inputs | Unbounded model understanding or Human satisfaction |
| PostgreSQL integration | Persisted turn/event behavior, source-basis retention, non-mutation, real service flow and replay | A live production incident's cause |
| Provider + API observations | Actual model-selected contract, generated language, progressive server events | Browser paint timing unless separately measured |
| Browser DOM observations | Actual visible text grows before completion | Human Acceptance or a latency SLA |
| Human Review | Human assessment of the live experience | Pending; not performed by the agent |

The durable [machine-readable qualification evidence](wic-response-contract-review-20260921.json)
contains 25 complete sequential Provider observations, including failures and
superseded observations; exact A/E PostgreSQL Reality observations; initial and
final browser samples; runtime configuration and source identity; and final
focused unit/integration results. No credentials are included.

Working artifacts were also retained during execution at:

- `/tmp/watt-response-contract-scenarios.json`: sequential actual Provider turns,
  including unsuccessful and superseded observations;
- `/tmp/watt-response-contract-browser.json`: browser DOM samples and final
  observed exploration text;
- `/tmp/watt-response-contract-reality.json`: exact A/E contract and Human-facing
  text from the real PostgreSQL deterministic Work Reality path;
- `/tmp/wic-response-contract-unit.xml`,
  `/tmp/wic-response-contract-postgres.xml`,
  `/tmp/wic-response-contract-status.xml`, and
  `/tmp/wic-response-contract-reality.xml`: focused test results.

These temporary paths are execution artifacts, not durable repository links.
The JSON and selected observations below preserve the substantive evidence in
the repository, separate earlier findings from later observations, and identify
the final source overlay.

## Focused test evidence

| Test selection | Observed result | Scope / qualification |
|---|---|---|
| Final Response Contract / conversation / provider / interaction / status unit selection | 185 passed, 0 failed, 0 errors | Final source after judgment grounding, challenge consistency, and Realizer context changes |
| `tests/integration/test_wic_response_contract.py` | 9 passed | Real disposable PostgreSQL `spg_test`, port 55448; no review database used |
| Related PostgreSQL integration selection after the final boundary changes | 58 passed, 7 skipped | The 7 existing opt-in live-Provider/Guided Design cases were not enabled; skipped cases are not claimed as passes |
| `tests/test_wic_response_contract_status.py` | 5 passed | Isolated read-store projections for current-binding status and stale history |
| A/E integration evidence capture after the current-queue filter change | 2 passed, selected from the above integration module | Re-verification and exact prose capture, not two additional distinct tests |

The nine integration cases prove:

1. PRE_WORK contract survives service reconstruction and reaches the next
   semantic call without becoming Engineering Semantic Truth.
2. Explicit exploration with a proposed new constraint and misleading `ON_TOPIC`
   provider focus remains non-mutating.
3. Status and queue diagnosis use Watt's read-only path without an external
   semantic or Realizer call (two cases).
4. Executable intent stays advisory until existing explicit Work admission runs;
   admission does not itself dispatch production.
5. PRE_WORK and active Work persist the contract before the first accepted delta,
   while the Realizer remains blocked before completion (two cases).
6. A failed realization's contract remains evidence but does not become the next
   completed trajectory.
7. Human SSE skips the internal contract-ready event, replays exact deltas from
   the cursor, and does not recall the model.

Status-specific tests reject a newer queue entry from an old PWU/Attempt, label a
terminal entry as the most recent execution rather than current running work,
decline to reuse an old waiting cause when current evidence is absent, and do not
infer a running execution from a historical queue without a current binding.

The original test assumption that every Runtime table stays empty after Work
admission was corrected: a managed repository baseline may legitimately create
snapshot records. The protected invariants are unchanged Runtime counts across
read-only turns and no production run/PWU/Attempt/dispatch merely from an
execution response. This test correction did not change product behavior.

The final selected total is **252 passed, 7 skipped**: 185 unit + 9 new
PostgreSQL + 58 related PostgreSQL cases. The 185-unit final selection supersedes
the earlier 157-unit snapshot; it is not added to that count. The five status
tests are part of the final unit selection, not five additional final cases.
Compile/import, `uv lock --check`, and
`git diff --check` passed. Runtime Alembic current and head both equal
`20260919_44`. All 164 source files checked inside the running source overlay
matched the working tree.

## Scenario matrix A–L

The table records the final selected observations and their limits. `q=0` means no
question is permitted; an execution advancement is a request within existing
authority, not evidence of dispatched production.

| Case | Produced contract / evidence class | Observed Human-facing behavior and current limitation |
|---|---|---|
| A. “为什么一直卡在 QUEUED？” | Real PostgreSQL deterministic path: `DIAGNOSE`, cause first, focused diagnosis, q=0, answer only | Reports that this fixture has no current production queue evidence rather than inventing a queue cause. It does not qualify a real capacity-stall repair. Exact text below. |
| B. One-branch Git question | Actual Provider `ANSWER`, answer first, minimum sufficient, q=0, adjacent budget 1, answer only | Answers yes, gives the single-branch command, then briefly covers shallow history and existing-repository fetch. No question. Early and revised attempts are both retained. |
| C. Architecture assessment | Final Provider + browser `ANALYZE` / `ASSESS`, judgment first, reasoned trade-offs, q=0 | `C-final` opens “合理”, grounds the modular-monolith/PostgreSQL recommendation in a two-person team, and explains boundaries and costs. Browser shows progressive text. The earlier failed realization remains history. |
| D. A/B comparison | Later actual Provider `DECIDE` / `COMPARE`, judgment first, decisive factors, q=0, propose and wait | `D` selects A and compares maintenance/operations costs under the known team constraint. Earlier wrong-mode output remains retained. The 512-character reply is broader than strictly necessary; final brevity/tone is for Human review. |
| E. Current progress | Real PostgreSQL deterministic path: `STATUS`, Reality first, concise Reality, q=0, answer only | Reports the admitted goal and absence of a production cycle; zero external Provider calls and no Work/Runtime mutation. Exact text below. |
| F. “继续做吧。” | Revised actual Provider `EXECUTE`, acknowledgement/proceed, minimal overhead, q=0 | Latest recorded text is one short sentence identifying the agreed next implementation direction. Earlier design recaps are retained as failed quality observations. |
| G. Unsupported judgment challenge | Final actual Provider `ANALYZE` / `ASSESS`, judgment first, objection/evidence, decisive-factors budget, q=0, `judgment_change_accepted=false` | `G-final` calmly retains the recommendation and names facts that would change it. The 214-character persisted text includes an existing generic Fast acknowledgement; no false correction or Work mutation is claimed. |
| H. Same failure after previous repair | Later Provider `DIAGNOSE`, Reality first, q=0, `REPLAN_REQUEST`; strategy revision 1 then 2 | `H-first` challenges assumptions; `H` stops the unproductive route and proposes independent evidence checks. No invented log-sharing question remains. Cause-exclusion wording is still too strong for the supplied evidence; this proves strategy change, not root-cause correctness. |
| I. Brainstorm login | Provider + browser `EXPLORE` / `PROPOSE`, contribution first, relevant divergence, q=0, answer only | Supplies several relevant directions in 626 characters rather than a one-line confirmation or production claim. Missing timing metadata was recovered from persisted response events read-only; no extra Provider request was needed. |
| J. Implement settled login design | Revised actual Provider `EXECUTE`, acknowledgement/proceed, minimal overhead, q=0 | “好，按已定方案继续推进登录功能的实现。” Earlier responses repeated the settled design; the revised expression context removed that recap. |
| K. Broken button, directly fix | Final actual Provider `EXECUTE`, acknowledgement/proceed, minimal overhead, q=0 | `K-final` briefly commits to diagnose and repair the button event path without inventing an already-approved plan. This expression sample does not claim the button was actually repaired; admission/progression authority is separately tested. |
| L. Same login topic across modes | I `EXPLORE` + `L-design` `DESIGN` + J `EXECUTE` in retained same-topic history | Exploration offers possibilities (626 characters), design gives a concrete three-state solution and rationale (358), execution collapses to 19 characters. These are observations, not hard-coded length limits. |

### Exact deterministic A/E records

Both cases ran against the disposable PostgreSQL fixture: admitted Work with
goal “A working sign-in form shows validation and submission feedback.” No
production cycle, PWU, or queue entry existed. The English goal is a test fixture,
not an inferred Chinese product requirement.

**A — Turn `4ffeb085-98fb-42a5-9f9b-fa1c02aaf748`:**

```text
mode = DIAGNOSE
obligation = DIAGNOSE
opening = CAUSE_FIRST
moves = CAUSE → EVIDENCE → FIX → VERIFY
information = FOCUSED_DIAGNOSIS
question_budget = 0
advancement = ANSWER_ONLY
external_provider_requests = 0
```

Observed Human-facing text:

> 当前生产周期没有对应的执行队列记录，现有证据不足以确认你描述的原因。尚未创建生产周期或 PWU，生产执行还未开始。当前没有需要你执行的决定。

This demonstrates bounded, evidence-honest diagnosis when the Human premise is
not supported by the current fixture. It does not claim that a real queue was
unstuck or that a cause was found.

**E — Turn `821bfa62-4205-4310-9325-a7badc828142`:**

```text
mode = STATUS
obligation = REPORT_REALITY
opening = REALITY_FIRST
moves = CURRENT_REALITY → GAP → NEXT_STEP
information = CONCISE_REALITY
question_budget = 0
advancement = ANSWER_ONLY
external_provider_requests = 0
```

Observed Human-facing text, including fixture punctuation:

> 当前目标：A working sign-in form shows validation and submission feedback.。目前处于「等待下一步」：尚无当前步骤。尚未创建生产周期或 PWU，生产执行还未开始。当前没有需要你执行的决定。

For both turns, the Work projection and all Runtime table counts matched their
pre-turn state. Contract stance remained `UNCERTAINTY` because no separate
professional judgment proposition was established; the deterministic response
itself was drawn from persisted Work/Runtime facts.

## Browser streaming observation

For the initial login exploration, browser observation of the current-interaction
DOM reported 83 characters at 295 ms (the panel and Human input), then 91 at
17,255 ms, 108 at 17,420 ms, and continued growth to 704 at 19,917 ms.

The 295 ms sample is not first meaningful WATT text and is not reported as a
TTFMS. The later sequence demonstrates actual progressive visible growth,
not merely `stream=true` or many server events. It also shows the still-visible
semantic wait before response text starts. This task makes no claim to have
solved overall Provider latency or established a population performance SLA.

The final-source architecture assessment (`C-final`, turn
`a5a9ad39-f2e0-40d5-91d8-df55daf2972e`) supplies the additional browser check after
the expression/gate changes. Sampling began late: the 15,220 ms sample still
showed “正在处理…”. The 20,837 ms sample showed “合理。”; at 20,997 ms the first
paragraph and following rationale were visible. Samples continued to grow until
the full response and paragraph layout were observed at 23,094 ms.

These are exact sample offsets, not an exact TTFMS measurement: sampling was
not continuous from send to first text, and the gap before 20,837 ms prevents an
exact first-paint claim. The evidence does prove Human-visible progressive
rendering before the final completed response, with no whole-response buffering
introduced by Response Contract.

## Historical findings retained during qualification

| Finding | Retained evidence | Bounded response |
|---|---|---|
| Execution contract existed but answer still recapped the design | `J-initial`, `F-initial`, and the before-context-projection records | Reduce execution expression context; keep authority and constraints, preserve full evidence; do not truncate the generated answer |
| One Realizer result was invalid | `C-initial`, turn `36d4581e-2052-4db5-9c9c-1d8acd377e99`, `FAILED`, message “Governed Response Realizer returned an invalid result” | Keep the failure as historical evidence; a later successful C does not erase it |
| Comparison mode and response size did not satisfy the requested contract | `D-before-context-projection` | Later `D` selected `DECIDE` / `COMPARE`; answer size remains a Human review point |
| Unsupported challenge preserved the conclusion but sounded defensive | `G-before-context-projection` | Compact challenge context plus source-grounded revision checks; `G-final` retains the recommendation with a calmer concise basis |
| Repeated-failure answer added a speculative privacy permission blocker | H before-context-projection records | Later H cases use q=0 and distinct independent-evidence routes; overconfident cause-exclusion wording is retained as a limitation |
| English clause waited for completion | The new blocking integration test originally saw no delta before release | Gate now recognizes an English sentence boundary; both PRE_WORK and active Work blocking tests pass |

No failure is converted into a pass merely by renaming it as a historical run.
The later evidence qualifies the repaired boundary and is retained alongside
the unsuccessful attempt. The focused structural tests also cover fabricated
grounds for judgment reversal, stale Runtime history, and non-mutating
unsupported disagreement.

Remaining Human review limits are explicit: architecture/comparison answers can
still run longer than necessary; a generic provisional Fast acknowledgement can
precede the final judgment; the H response overstates what unsuccessful
cache/restart actions establish about cause; and sample lengths are not quality
or latency guarantees. This mission qualifies a reusable contract and its
observed consumption, not a complete Guardian diagnosis system or flawless
professional judgment on arbitrary inputs.

## Human Review runtime

```text
COMPOSE_PROJECT = watt-response-contract-review
HUMAN_RETEST_URL = http://127.0.0.1:8048/app
SOURCE = current working-tree source overlay
SOURCE_OVERLAY_MATCH = YES / 164 FILES
REVIEW_RUNTIME_VERSION = 39aeb50adf156aaf3e27887f47b9b7ab46b3887eb8ac79999d79252afdf2534e
BASE_REVISION = 964f7b6c88cb9e3d216a2674713c1096753d510a
WIC_PROVIDER = deepseek / deepseek-flash / low
CONVERSATION_PROVIDER = deepseek / deepseek-flash / low
WIC_MODE = WIC_VNEXT_CONTROLLED
ACTIVATION = HUMAN_REVIEW
AUTH_AVAILABLE = YES / VALUE_NOT_RECORDED
APP_HEALTH = AVAILABLE / INITIALIZED
DATABASE_HEALTH = AVAILABLE
ALEMBIC_CURRENT = 20260919_44
ALEMBIC_HEAD = 20260919_44
READY_FOR_HUMAN_REVIEW = YES
```

The review database is separate from the disposable PostgreSQL test database.
The Human can compare exploration, architecture discussion, a bounded question,
execution, status, challenge, and repeated failure/correction. Only the Human
can accept the product experience.

The temporary test PostgreSQL container was stopped after focused qualification.
Only the five-container Review runtime remains running; no existing service was
stopped or rewritten to make room for it. The local isolated Compose description
is `/tmp/watt-response-contract.compose.json`; it uses credential-variable
references and does not record credential values.

The Provider profiles above reproduce the existing WIC/Conversation
configuration; they were not changed to improve qualification samples. The
application imports `response_contract.py` from `/acceptance-source`, with
`PYTHONPATH=/acceptance-source`. The independent review runtime leaves existing
services unchanged.

Final environment calibration mapped delivery ports to the existing 8010–8019
URL defaults and included the actual isolated Compose configuration under
`/review-config` in runtime identity. This changed the runtime version, not
product source or Provider mode; source digest remains
`950859dcc270597f069a48176c00b74d098e8f6fa05a9c36b819a4acd447f829`.
It is review-environment configuration, not a reopening of Preview/Delivery.

## Focused qualification classification

The following PASS values mean this task's implemented boundary and focused
scenario evidence meet the stated review-readiness bar, subject to the explicit
sample limitations above. They do not declare Human Product Acceptance.

```text
RESPONSE_CONTRACT = IMPLEMENTED
RESPONSE_CONTRACT_FIRST_CLASS = PASS
INTERACTION_MODE = PASS
EXPECTED_ANSWER_FORM = PASS
MINIMUM_SUFFICIENT_ANSWER = PASS
EXPLORE_VS_EXECUTE_DIFFERENTIATION = PASS
INFORMATION_BUDGET = PASS
QUESTION_BUDGET = PASS
JUDGMENT_CONSISTENCY = PASS
ADVANCEMENT_OBLIGATION = PASS
STATUS_REALITY_FIRST = PASS
EXECUTABLE_INTENT_LOW_OVERHEAD = PASS
REPEATED_FAILURE_STRATEGY_SIGNAL = PASS
SEMANTIC_TRUTH_BOUNDARY_PRESERVED = PASS
GOVERNED_STREAMING_COMPATIBILITY = PASS
NO_CASE_SPECIFIC_TEMPLATE_ARCHITECTURE = PASS
READY_FOR_HUMAN_REVIEW = YES
SOFTWARE_DOMAIN_GROUNDING = NEXT
SOFTWARE_PRODUCTION_SOP = NEXT
FULL_REGRESSION = NOT_RUN_BY_DESIGN
CLOSURE = NOT_PERFORMED
HUMAN_ACCEPTANCE = PENDING_HUMAN
COMMIT = NOT_CREATED
PUSH = NOT_PERFORMED
```
