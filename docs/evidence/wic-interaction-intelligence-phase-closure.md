# WIC Optimization Milestone Closure

Initial phase closure: 2026-09-17

Final milestone closure: 2026-09-22

Starting revision: `33daa29c356eafefd28d8bbfae72571d0b585e2a`

Final implementation baseline: `624c06cdddfc9b6dbd05b4de2f0645b197ae023c`

Branch: `feature/spg-first-vertical-slice`

```text
MILESTONE
    WIC_OPTIMIZATION

WIC_INTERACTION_INTELLIGENCE_PHASE
    CLOSED / PASS

HUMAN_ACCEPTANCE
    PASS

FULL_REGRESSION
    PASS

CLOSURE
    PASS
```

This is a milestone closure, not a claim that WIC is finished or that Human
experience is perfect. Human acceptance has been granted for the current entry
interaction quality. No further WIC optimization is required in this milestone.
The 2026-09-17 Retest and its verbatim record remain below as historical
evidence; the final acceptance in this section supersedes its then-open
product-quality disposition without erasing the observations.

The implementation baseline is the exact repository revision inspected before
this closure-only documentation and test-entry repair. The final closure commit
is reported by Git after commit and push because a commit cannot contain its own
SHA.

## Final implemented Repository Reality

| Capability | Implemented reality and preserved boundary |
|---|---|
| Response Contract | Provider-neutral immutable `wic-response-contract-v4` selects the turn-scoped obligation, opening, response moves, reasoning sequence, information/question budgets, judgment basis, and advancement posture. It remains `ADVISORY_ONLY`. |
| Interaction modes and strategies | `EXPLORE`, `ANALYZE`, `DESIGN`, `DECIDE`, `ANSWER`, `DIAGNOSE`, `EXECUTE`, `CORRECT`, and `STATUS` are implemented. EXPLORE composes `OPEN_EXPLORATION` or `INTENT_REFINEMENT`; design collaboration composes explore/review/decide postures without adding a lifecycle. |
| Intent Refinement | The bounded EXPLORE strategy spends at most one question on an admitted high-impact unresolved decision and does not reopen settled execution intent. |
| System Capability Reality | A versioned, fingerprinted `SystemCapabilityReality` describes Watt's evidenced software-production role and boundaries. It is capability truth, not marketing or execution authority. |
| Capability Alignment | `KNOWLEDGE`, `PRODUCTION_ADVISORY`, and `PRODUCTION` distinguish ordinary answers, bounded software-production guidance, and explicit governed build/change intent. Alignment cannot admit Work or claim effects. |
| Response recovery and trust | Human-visible response maturity is explicit as `PROVISIONAL`, `GOVERNED`, and `FINAL`. Incomplete transport and strict structured-output failures retain safe evidence, use bounded recovery where admitted, and never promote invalid output. Exact-turn retry preserves history rather than requiring message re-entry. |
| Engineering Semantic Truth | Governed semantic facts preserve source, authority, epistemic status, supersession, and exact identity. Current facts flow into Response realization, Task Contracts, Completion Contracts, and Executor instructions without being rewritten by conversational form. |
| Domain Grounding | Immutable Engineering Pattern contracts, structured applicability metadata, dimensions/options, evidence direction, and a bounded catalog are implemented as advisory foundations. There is no Pattern Studio, evolution engine, or complete library. |
| Context Orchestration | A bounded `ContextOrchestrator` selects source-owned candidates under item, character, and per-source budgets while keeping Semantic/Work Reality authoritative and Pattern/SOP guidance optional. It is not the complete ECF or a general retrieval platform. |
| SOP foundation | Engineering Activity, SOP guidance, evidence expectations, and non-authorizing checkpoints are implemented. Full adaptive SOP runtime and administration remain future work. |
| Task Contract | Immutable Task Contracts project objective, scope, constraints, acceptance meaning, evidence requirements, out-of-scope limits, authority, semantic facts, SOP, decision, and evidence lineage into PWU Completion Contracts and Executor instructions. The proposed full lifecycle is not implemented. |
| Decision and Evidence | Bounded Reasoning Summary, Decision Trace, and Human/Engineering/Assurance Evidence Reference contracts preserve lineage without raw chain-of-thought or a new authority owner. There is no general Decision/Evidence store. |
| Work Plan / Steering projection | The API projects completed/current/known-next steps plus persisted Plan revision history, change reason, affected steps, and Reality references. Steering still owns formal `WHAT NEXT`; the projection is Human visibility, not a workflow engine. |

## Architecture and documentation reconciliation

The implementation preserves Work Admission, Human Authority, Engineering
Semantic Truth, Steering, PWU, Executor, Verification, Guardian, Preview, and
Delivery ownership. The current documentation was reconciled as follows:

- [WIC Response Contract](../architecture/wic-response-contract.md) now records
  bounded Human Acceptance and implemented Domain/SOP foundations;
- [WIC Software Production SOP × LLM](../architecture/wic-software-production-sop-and-llm-direction.md)
  no longer contradicts the implemented Context, Task, and Decision/Evidence
  foundations;
- [WIC Intelligence Architecture Closure](../architecture/watt-wic-intelligence-architecture-closure.md)
  explicitly marks its original `NOT_STARTED` values as the historical
  2026-09-15 state; and
- [Watt AI-Native Software Production Architecture](../architecture/watt-ai-native-software-production-architecture.md)
  remains the consolidated current status map.

No product capability, architecture subsystem, authority transfer, or WIC
redesign was introduced by closure reconciliation.

## Final Human acceptance evidence

The Human Governor accepts the current WIC usability level and requires no
further WIC optimization in this milestone. The accepted observations are:

- product exploration is materially more focused and pragmatic;
- Watt asks fewer, higher-value clarification questions;
- responses better match current Human intent and interaction stage;
- tested exploration avoids premature over-expansion;
- Capability Alignment preserves Watt's software-production identity while
  keeping ordinary knowledge answers non-promotional; and
- entry interaction quality is usable and sufficiently mature for closure.

```text
HUMAN_ACCEPTANCE = PASS
```

## Known non-blocking findings

- Long-horizon multi-turn stability still needs continued real-world
  validation across varied projects and failure histories.
- The AI Software Production Evaluation Framework is an architecture baseline;
  its evaluation platform, corpus, automation, and leaderboard are not
  implemented.
- ECF is not the complete Engineering Reality infrastructure; current Context
  Orchestration uses bounded source-owned projections.
- Guardian is not the complete Assurance System; existing verification and
  integration seams do not imply complete Guardian capability.
- Domain Pattern, SOP, Task Contract lifecycle, and Decision/Evidence storage
  remain bounded foundations rather than complete management platforms.
- Future WIC evolution should remain evidence- and scenario-driven rather than
  restarting broad optimization from preference alone.

These findings do not block the accepted WIC optimization milestone.

## Final verification

The final repository tree was verified once after resolving the real
closure-blocking test-entry and frozen-evidence portability defects found by the
initial run.

| Surface | Final result |
|---|---|
| Full Python regression with isolated PostgreSQL `spg_test` | 1,401 passed; 10 protected real-Provider cases skipped; 0 failed; 4 existing Pydantic deprecation warnings |
| WIC / Response Contract / recovery / trust | PASS as part of Full Regression |
| Engineering Semantic Truth | PASS as part of Full Regression |
| Work Reality / Steering / Plan projection | PASS as part of Full Regression |
| Production flow and Verification | PASS as part of Full Regression |
| Watt-native Executor, continuity, recovery, and evidence | PASS as part of Full Regression |
| Web/UI Node suite | 69 passed; 0 failed |
| Alembic schema | head/current both `20260919_44` |
| Python compile/import | PASS |
| `uv lock --check` | PASS |
| `git diff --check` and frozen-artifact EOL policy | PASS |

The ten skips are explicitly authorization/environment-gated real-Provider
probes. They do not conceal a deterministic failure; provider boundaries also
retain their prior bounded real-provider evidence.

The first command invocation stopped during collection because the documented
`uv run pytest` entry did not add the repository root to Python's import path,
so repository-owned `benchmarks` and `docker` modules could not be collected.
The minimal closure fix adds `pythonpath = ["."]` to the pytest configuration.

The first complete run then produced `1,400 passed, 10 skipped, 1 failed`. The
only failure was the frozen Open WIC byte-integrity test: its expected hashes
had been changed on a Windows checkout to CRLF-transformed bytes even though the
Git blobs had never changed. The closure fix restores the SHA-256 values of the
canonical LF Git blobs and pins both frozen artifacts to `eol=lf` in
`.gitattributes`. The focused integrity test passed, and the permitted final
Full Regression on the repaired tree passed with 1,401 tests.

## Explicit closure decision

```text
MILESTONE = WIC_OPTIMIZATION
HUMAN_ACCEPTANCE = PASS
FULL_REGRESSION = PASS
CLOSURE = PASS
READY_FOR_NEXT_MAJOR_INITIATIVE = YES
```

## Historical 2026-09-17 Human Retest evidence

The Human Governor observed that interaction was materially more focused than
earlier WIC behavior, response speed felt materially improved, and the current
direction was better than the prior questionnaire/generic-`ORIENT` experience.
The same Retest also exposed the reliability blocker and the non-blocking
experience findings recorded below.

### Verbatim Human Acceptance record

```text
“偶尔会报错。
整体感觉有改善，开始聚焦了，比之前强些了。
但引导性还是不够，没有那种很专业很有推动力，让用户安心的觉得只要跟着AI的思路走，就能把这个事情很好的推进并完成的感受。
回复速度的提升感受还是很明显的，这点提出表扬，相信未来结合一些产品层的优化，比如加载动效，和文字输出控制，这部分体验提升问题不大了。
然后内容上，还需要形式更丰富些，不要总是大段大段的文字表述，尽可能图文并茂，加上一些列表、表格对比项，架构图、流程图等等之类的。
表述这块也是需要优化，要体现出专业性，无论是处理用户的咨询，还是执行用户确定性的任务，都要做到让用户觉得‘放着我来，这事交给我就是终点，相信我，肯定靠谱的帮你完成’，尽量朝着这些心智来靠拢才好。
最后在表意上，要让用户觉得那些意见是由AI角色‘说’出来的，比如加上一些‘我会帮你XXX’，‘按我的想法，XXX’，‘我觉得如果这样XXXX’，要生动一些，现在感觉就像用户自己百度查资料看到冷冰冰的一段段百科介绍一样。”
```

## Reliability Finding and repair

The isolated `watt-wic-interaction-intelligence` Runtime preserved one failed
Turn among twelve Retest Turns:

```text
Turn
    d23eed01-0a3e-4715-ae5c-77d0b2146b6d

Human input
    部署呢？你建议如何做？

status
    FAILED

failure_code
    InteractionInvariantViolation

failure_message
    Coalesced collaboration Provider returned an invalid structured result
    (root:json_invalid)
```

The Provider transport reached a terminal `completed` response, after which the
coalesced payload failed root-level JSON syntax validation. No Assessment,
Watt Conversation message, Work, or governed truth was created from the invalid
output. Events ended truthfully at `TURN_FAILED`. The same Human input was then
manually submitted again and completed, which is consistent with an occasional
Provider structured-realization failure rather than a deterministic semantic or
schema mismatch.

The exact malformed bytes were intentionally not persisted, so the historical
evidence cannot truthfully distinguish a missing delimiter from another JSON
syntax defect. It does distinguish this failure from a schema/output-field
mismatch and from a transport `incomplete` status.

The repair is deliberately narrow:

- only controlled WIC is eligible;
- only a coalesced payload rejected at root as `json_invalid` is retried;
- exactly one structured repair attempt is allowed;
- schema, semantic, authority, and other validation failures are never retried;
- semantic-provider text from either attempt is not Human-visible;
- no Assessment, Conversation Truth, Work, or governed fact is admitted before
  the complete repaired payload passes existing validation;
- successful evidence records two Provider calls and one retry;
- a second syntax failure remains a truthful terminal failure marked
  `bounded_repair_exhausted`.

This preserves the invariant that malformed output never becomes structured
truth while preventing one occasional syntax-only Provider failure from ending
an otherwise recoverable controlled Turn.

## Deferred Human-experience findings

These findings remain explicit and open. They are not closure blockers and are
not claimed as fixed.

### Professional guided-development confidence

Watt should increasingly create the Human mental model: “Follow Watt's
reasoning and this work will be professionally driven to completion.” The
experience should be capable, proactive, trustworthy, outcome-oriented, and
persistent—not merely friendly conversation.

### Professional/proactive tone and AI role voice

Human-facing expression should sound like an active collaborator speaking from
bounded judgment. Natural forms such as “我建议……”, “我会先帮你……”, “按我的判断……”,
“这里我倾向于……” and “这一步交给我……” are useful directions when truthful. This
must not become theatrical language or a false claim of Authority. The current
encyclopedia/reference-text tone remains insufficient.

### Rich response forms

Formal UX/UI and Conversation Rendering should support the representation best
suited to the content: concise prose, lists, comparison tables, option cards,
checklists, architecture/flow diagrams, and progress/status structures. This
closure does not implement a rich-response system.

### Perceived latency and product presentation

Loading/progress treatment, controlled realization/pacing, and richer streaming
presentation remain product-level opportunities. The Retest's positive speed
observation is retained without claiming a latency SLA or starting another
latency optimization round.

### Legacy naming

The current prototype still contains TNGA presentation. Formal UX/UI should use
Watt / 工律 consistently under the admitted naming rules while preserving
historical evidence where TNGA is part of the original fact.

## Automated Conversation Probe

The repository-native detector is retained at:

- [`interaction_intelligence_cases.json`](../../benchmarks/conversation_quality/interaction_intelligence_cases.json)
- [`interaction_intelligence_probe.py`](../../benchmarks/conversation_quality/interaction_intelligence_probe.py)

It is an internal reusable evaluation tool for finding obvious conversational
regressions before Human testing. It is not exposed as a Human-facing UI and
this closure does not create a Conversation Lab.

## Historical 2026-09-17 verification

Final closure evidence is recorded after the bounded repair in this same
checkpoint:

```text
FOCUSED_VERIFICATION
    165 PASSED
    6 PROTECTED REAL-PROVIDER CASES SKIPPED
    0 FAILED / 0 ERRORS

FULL_TARGET_ENVIRONMENT_REGRESSION
    1166 PASSED
    10 SKIPPED
    0 FAILED / 0 ERRORS
    Linux / Python 3.13 / isolated PostgreSQL spg_test

OPEN_WIC
    5 PASSED

NODE_UI
    39 PASSED

COMPILE_IMPORT
    PASS

UV_LOCK_CHECK
    PASS

GIT_DIFF_CHECK
    PASS
```

The first full-regression setup attempt used the repository's
`native-verification` image and stopped during collection because that image
does not include the locked `openai_codex` test dependency. The complete run
used the existing `codex-executor` test target. An initial isolated database
name also proved the `DB-01` guard by failing because it was not exactly
`spg_test`; the admitted full run used a disposable PostgreSQL container with
the required database name. Neither setup finding is represented as a product
failure or hidden as a successful first attempt.

## Historical 2026-09-17 phase conclusion

Turn Intent, Cognitive State, candidate-first `BUILD`, answer-first `HOW_TO`,
Interaction Strategy, DeepSeek selection, and Fast Reception are not reopened.
Rich rendering and Formal UX/UI are not implemented here.

```text
WIC_PHASE_CLOSURE
    CLOSED / PASS WITH PRESERVED HUMAN FINDINGS

NEXT_MAJOR_PHASE
    FORMAL_UX_UI_IMPLEMENTATION
    REQUIRES_SEPARATE_AUTHORIZATION
```
