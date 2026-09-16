# WIC Human Experience Recovery Evidence

Date: 2026-09-17

Branch: `feature/spg-first-vertical-slice`

Mission starting revision: `0f7a90fa5d6f54b9233b8523e385ff0ca85c6168`

Current repository revision: `281212163cf8efe6efbb0eb897c19400ab96266a`

The revision advanced during the mission through the non-overlapping
documentation commit `docs: add Watt dogfood production coverage memo`. The
Human-experience recovery was validated as a working-tree change on that
revision. No reset, revert, history rewrite or product-acceptance declaration
was performed.

## Preserved truth

```text
GOVERNED_STREAMING = QUALIFIED
HUMAN_PRODUCT_ACCEPTANCE = FAIL
RECOVERY_RETEST = PENDING_HUMAN
```

The prior technical qualification and failed Human result describe different
gates. This iteration does not overwrite either fact.

## Architecture change

The controlled WIC response path now has an explicit, provider-neutral
`InteractionStrategy` between governed semantics and the Safe Response
Envelope:

```text
Human Turn
  -> Deep WIC / structured semantics
  -> policy / Repository Reality / Human Authority
  -> Interaction Strategy
  -> Governed Response Envelope
  -> Conversation Realizer
  -> governed streaming
```

The strategy records Human abstraction level, cognitive maturity, conversation
mode, one primary conversational move, the next useful granularity, and whether
one question is allowed. Supported moves are `ORIENT`, `EXPLAIN`, `PROPOSE`,
`COMPARE`, `ANSWER`, `ASK`, `CONFIRM`, `CORRECT`, and
`ESCALATE_HUMAN_DECISION`.

The seam owns expression strategy only. WIC still owns interpretation; Work
owns Work Reality; Repository Reality and Human Authority remain unchanged.
Raw Provider prose still cannot bypass the governed envelope or delta gate.

Policy and prompts now require the response to demonstrate understanding by
the quality of its next move. Restatement is reserved for correction, material
ambiguity, Human Authority, or costly constraints. A broad motive stays at the
domain level, a concrete question is answered directly, and Human uncertainty
receives expertise or options before another question.

An independent general-information question is classified as
`CONVERSATION_ONLY`. Provider-invented motive/outcome text can no longer make
that turn ready for Work formation. This was found in the real UI and fixed
without weakening Work admission.

## Bounded latency optimization

The first instrumented broad-motive trace used two serial model stages:

- coalesced semantic/conversation Provider: about 27.6 seconds;
- external wording Realizer: about 8.9 seconds;
- browser final paint: about 36.8 seconds.

The coalesced Provider had already supplied the natural response. Rephrasing it
with a second model added latency and created a second opportunity for wording
drift after governance. The controlled path now keeps the Realizer seam but
uses deterministic governed streaming when pipeline evidence proves that one
Conversation Provider call has already completed. Custom or separately staged
pipelines retain the replaceable Provider Realizer. Human-owned authority cases
continue to use deterministic realization.

This removes one serial Provider request. It does not reduce the reasoning
effort or switch the configured model.

## End-to-end observability

Server telemetry now retains reception, durable acknowledgement, Reality load,
Fast eligibility and suppression reason, Provider start/first token/completion,
admission, realization, first final delta, persistence and terminal stream
timings. Final response evidence includes exact Provider pipeline provenance and
the selected Interaction Strategy.

The browser records send, durable acknowledgement, first SSE event,
provisional/refinement/final receipt, first actual DOM paint, first meaningful
paint and final paint. Paint timing is marked inside the animation-frame render
callback, so received-but-not-yet-visible text is not reported as visible.

## Real Provider and real UI observations

Runtime:

```text
compose project: watt-wic-governed-streaming
URL:             http://127.0.0.1:8046/app
WIC mode:        WIC_VNEXT_CONTROLLED
Provider model:  gpt-5.6-sol
reasoning effort: low
```

All measurements below start at browser send and end at actual DOM paint. They
are individual observations from the mainland-China/VPN environment, not an
SLA or p95.

| Human journey | Fast visible | first meaningful paint | final paint | observed result |
|---|---:|---:|---:|---|
| Broad motive: `我想做一个企业官网。` | yes | 421 ms | 27,569 ms | Oriented around business role and trust before asking what the organization provides. |
| Domain context: manufacturing energy retrofit | yes | 219 ms | 27,518 ms | Narrowed positioning to energy savings, risk reduction, credible proof and lead generation. |
| Human uncertainty: `我其实也不知道该做成什么样。` | yes | 259 ms | 24,775 ms | Supplied a way to frame the problem; no questionnaire. |
| Direct information: enterprise-site pages | deliberately suppressed | 21,506 ms | 21,622 ms | Answered directly and kept Work admission `NOT_READY`. |
| Specific design question: 3:7 customer gender ratio | deliberately suppressed | 37,109 ms | 37,401 ms | Recommended a professional, restrained industrial-tech direction and explained why customer role matters more than gender. |

Representative final responses included:

> 企业官网通常包括：首页、关于我们、产品或服务、案例或客户、新闻动态、联系我们，以及隐私政策等合规页面。招聘、投资者关系、帮助中心、合作伙伴等页面可按业务需要增加。规划时建议先确保访客能快速回答三个问题：这家公司是谁、能提供什么、下一步如何联系或行动。

> 官网的核心表达可以先围绕“帮助制造企业降低能耗与改造风险”展开，用专业能力、改造方法和可信依据建立信任。下一步建议确定官网是优先获取销售线索，还是优先建立专业形象；这会直接影响内容重心和访问路径。以当前业务特点，我建议优先支持潜在客户理解服务并发起咨询，同时兼顾专业形象。

> 我建议采用“专业、克制、可信”的工业科技风格，不要根据3:7的男女比例直接做性别化设计。可以用深蓝绿或石墨色建立技术与节能感，搭配大面积浅色背景、清晰的数据图表和真实的工厂及改造项目图片；版式强调易读性、改造收益和可信依据，动效保持节制。过于硬朗会显得疏离，过于柔和又可能削弱工程专业感，因此可用圆润细节和真实人物场景增加亲和力。下一步建议先按这个方向制作首页视觉基调和关键首屏样稿，再结合客户在制造企业中的具体角色进行验证；职业角色和决策任务通常比性别比例更能决定有效的官网体验。

The post-change representative sample had meaningful Fast coverage of `3/5`
turns and `3/3` eligible turns. The direct information question was correctly
suppressed rather than showing a generic acknowledgement; the concrete design
question was also suppressed because the deterministic Fast path had no safe,
useful answer for it.

For the direct-question sample, server telemetry measured:

| milestone | elapsed |
|---|---:|
| durable acknowledgement | 73 ms |
| Reality loaded | 187 ms |
| Fast suppressed | 213 ms |
| Provider turn started | 3,829 ms |
| Provider first token | 14,769 ms |
| natural response complete | 16,462 ms |
| semantic envelope complete | 21,036 ms |
| first governed final delta | 21,334 ms |
| persistence complete | 21,472 ms |
| browser final paint | 21,622 ms |

The single coalesced Provider request occupied about 20.84 seconds. Local
strategy, governed deterministic realization, persistence, SSE delivery and
browser painting occupied hundreds of milliseconds after Provider completion.
Browser delivery was not the dominant delay.

The concrete design sample showed the same shape at a slower Provider rate:
the one coalesced request occupied 36.13 seconds, Provider first token arrived
at 23.89 seconds from Human send, and deterministic realization began at 36.99
seconds. Its Interaction Strategy was `PROPOSE / SOLUTION / EVALUATING` with
questions disabled.

The test environment uses a US-node VPN from mainland China. The trace proves
that the external Provider/SDK path dominates current non-Fast completion time,
but it does not separate Provider queue/generation time from VPN transport.
`VPN_NETWORK_IMPACT` therefore remains `NOT_ESTABLISHED` until a matched
VPN/non-VPN A/B run is available.

## Benchmark coverage

The conversation-quality corpus now contains 42 cases. Six recovery cases cover
broad motive, domain context, a concrete design question, a direct information
question, Human uncertainty and a long contextual turn. Their review contracts
include cognitive alignment, orientation before detail, direct answer first,
meaningful alternatives, no questionnaire, no recap dump and advancement of
the Human's thinking.

Existing OPEN_WIC scenarios continue to cover correction supersession,
constraint preservation, Human Authority, Repository Reality and New Motive
isolation. Deterministic contracts cover all A-K journey classes; representative
A-E cases were additionally inspected through the real Provider and browser.
Subjective quality remains a Human judgment.

## Verification

Focused results:

```text
Python WIC/conversation suite: 63 passed, 23 skipped integration cases locally
Web state suite:               39 passed
compile/import:                PASS
uv lock --check:               PASS
git diff --check:              PASS
```

Full Linux target-environment result is recorded after the final run below.

## Remaining findings

- Fast Reception provides sub-second useful text only for eligible turns; it is
  intentionally absent for unsupported or direct-information inputs.
- Current non-Fast samples waited roughly 21–37 seconds for the one external
  Provider call. Further architecture changes are not justified by the
  available trace.
- A matched VPN/non-VPN/provider-path experiment is still needed before
  attributing that wait to the network.
- Human Product Acceptance remains `PENDING_HUMAN` for this recovery iteration.

## Interaction Intelligence follow-up (2026-09-17)

Human Retest exposed cross-domain template reuse: the consumer decision-assistant
mini program received the enterprise-site broad-request frame and enterprise
question. Code inspection established three deterministic causes rather than a
Provider-only quality fluctuation:

- `wic_reception.py` emitted one business/audience and page/function sentence for
  every broad `我想做...` input, and a website-positioning sentence for generic
  context additions.
- `interaction_strategy.py` prescribed an organization/business and
  product/service question for every exploring turn.
- `wic_response.py` removed the model-selected trailing question and appended the
  prescribed enterprise question. Focused tests asserted those exact strings,
  while the recovery corpus contained only one broad object class.

The repair removes broad, context and uncertainty prose from deterministic Fast
Reception; those turns now wait for context-sensitive model content. Interaction
Strategy retains only the primary move, abstraction level, maximum question
count and domain-neutral question bounds. It can suppress a disallowed question
but can no longer author a replacement. Conversation policy requires examples,
choices and questions to belong to the actual object, forbids adjacent-domain
details and known/unknown-field narration, and rejects noun-substitution
templates. Domain keyword maps were removed from Interaction Strategy.

The focused corpus now has 49 total cases and 13 recovery cases spanning an
enterprise site, consumer mini program, mobile app, internal approval system,
developer CLI, engineering infrastructure, content site, vague business idea,
direct questions and specific design questions. Contracts evaluate object
relevance, unsupported premises, cognitive contribution and cross-domain reuse;
they do not provide expected response prose.

Sequential `deepseek-flash` real-Provider probes produced distinct conceptual
focuses:

| Human prompt | admitted move | response focus |
|---|---|---|
| `我想做一个企业官网。` | `ORIENT` | distinguish trust/lead-generation role, then ask about acquisition source |
| `我想做一个面向C端用户的决策助手类小程序。` | `ORIENT` | distinguish decision-assistance modes and identify the first decision domain |
| `我想做一个员工请假审批系统。` | `ORIENT` | define the minimal leave loop and fixed versus conditional approval chain |
| `我想做一个日志分析 CLI。` | `ORIENT` | choose the first diagnostic question and log source for the initial command |
| `我想设计一个工程上下文基础设施。` | `ORIENT` | bound durable context responsibilities and anchor one engineering scenario |

The first approval probe mentioned an adjacent approval-domain field (`金额`). A
domain-neutral policy correction was applied, and the successor probe used only
leave-relevant dimensions (`假种`, `时长`, `部门`). The successor mini-program
probe also removed the earlier inventory of unrelated unknown fields. One
enterprise-site control remained context-specific after the correction.

Focused verification after the final repair:

```text
WIC / Conversation / Provider focused unit tests: 129 passed
Affected controlled-streaming PostgreSQL tests:    3 passed
Real DeepSeek diverse-object probes:               PASS
git diff --check:                                  PASS
FULL_REGRESSION:                                   NOT_RUN_BY_DESIGN
```

Human Product Acceptance remains `PENDING_HUMAN`.
