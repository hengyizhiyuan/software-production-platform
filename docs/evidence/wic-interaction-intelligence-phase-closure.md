# WIC Interaction Intelligence Phase Closure

Date: 2026-09-17

Starting revision: `33daa29c356eafefd28d8bbfae72571d0b585e2a`

```text
WIC_INTERACTION_INTELLIGENCE_PHASE
    CLOSED / PASS WITH PRESERVED HUMAN FINDINGS

HUMAN_RETEST
    COMPLETED
    MATERIALLY_IMPROVED
    SUFFICIENT_TO_MOVE_PROGRAM_FORWARD

JSON_INVALID_RELIABILITY_BLOCKER
    RESOLVED

HUMAN_EXPERIENCE_FINDINGS
    OPEN / EXPLICITLY_DEFERRED
```

This is a phase closure, not a claim that WIC is finished or that Human
experience is perfect. The current interaction architecture and experience are
useful enough to stop this optimization loop and return to the main Watt
engineering roadmap. The remaining findings below are retained as future
product/UX obligations.

## Human Retest evidence

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

## Verification

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

## Closure and next phase

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
