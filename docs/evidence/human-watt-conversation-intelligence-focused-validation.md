# Human–Watt Conversation Intelligence Focused Validation

Status: **IMPLEMENTED / FOCUSED VALIDATION PASS / REAL PROVIDER PROOF PASS**

Human Product Acceptance: **PENDING**

## Repository reality and implementation

At starting HEAD `bf0858c0d835b263737077ae2e27111f31b0e01e`, WIC semantic
interpretation and `natural_response` shared one Codex Provider payload and
instruction. Domain assessment, Guided Design semantics, and final Human wording
were coupled at the Provider boundary even though persistence and streaming
were already separate and truthful.

The implementation introduces provider-neutral conversation contracts, a
bounded native context assembler, a response composer, an independently
configurable Conversation Provider, and a compatibility facade over the existing
`WorkInteractionService`. No migration or persisted Truth-owner change was
required.

## Benchmark

- corpus: **30 cases**;
- languages: Chinese and English;
- behavioral intents: **13 / 13 covered**;
- categories: vague goal, factual question, context addition/reuse, correction,
  disagreement, recommendation, decision support, detail request, side question,
  material branch, frustration, Guided Design progression, Human decision,
  limitation, Verification, Attention, and feedback;
- dimensions: directness, naturalness, concision, context fidelity,
  non-repetition, proactivity, relevance, decision utility, appropriate detail,
  metadata leakage, and continuity.

The corpus is reusable and does not send all 30 cases to a real Provider.

## Real Provider evidence

The bounded proof used `gpt-5.6-sol`, independent ephemeral read-only/deny-all
semantic and conversation Threads, an empty disposable working directory, and
exact test-supplied context. It created no Work or production facts.

The first vague-goal sample exposed two questions in one response. Policy was
tightened to one highest-impact question. A later combined run passed the vague
goal and context-reuse assertions before a transient semantic typed-payload
failure at the direct question. That failed combined run is not represented as
an end-to-end pass. The direct-question, detail, correction, and recommendation
cases were replayed individually through the same product service boundary and
passed.

| Scenario | Intent | Observed result |
| --- | --- | --- |
| Vague new goal | `NEW_GOAL` | Proactive opening guidance; one highest-impact question; no methodology/schema dump. |
| Known context reuse | `CONTINUE_CURRENT_WORK` | Reused purpose, audience, and channels; did not ask for audience again. |
| Direct question | `DIRECT_QUESTION` | First paragraph states that pre-Work Guided Design does not generate/write a document and has no exact path; brief governed-proposal explanation follows. |
| Explicit detail | `REQUEST_DETAIL` | Expands across users/problem, outcomes/scenarios, boundaries, capabilities, architecture/risks, verification, and staged production. |
| Correction | `CORRECTION` | Accepts “personal developers, not large enterprises” and continues without defensiveness or repeated questioning. |
| Recommendation | `REQUEST_RECOMMENDATION` | Recommends outcomes/key observable scenarios first, using the known audience/problem, without returning a questionnaire. |

Representative safe responses:

- Direct question: “目前不会自动生成或写入设计方案文档，因此暂时没有确定的输出路径。” A reviewable production proposal would later decide whether and where to create it.
- Correction: “收到，首批目标用户修正为个人开发者，不是大型企业。” The corrected fact becomes the basis for later design.
- Recommendation: prioritize “成果与关键场景,” starting with the state visibility individual developers need across running, success, failure, blocking, and intervention.

| Scenario | Semantic Thread | Conversation Thread |
| --- | --- | --- |
| Direct question | `01a08319-cec9-7232-b593-4342705d45cc` | `01a08369-8752-78d0-b254-8142a1c8271a` |
| Detail request | `01a0836c-1cb7-7861-b791-9aa772687236` | `01a0836e-a8ae-79f0-9393-076bf21b01c8` |
| Correction | `01a08371-d8db-72e0-8857-528593a682cc` | `01a08374-2f63-7b42-b451-c96e7999b9e5` |
| Recommendation | `01a0837c-ccf7-79c1-9844-600caadf1a62` | `01a0837f-5bd8-7500-ae90-047d8aa97576` |

This is Provider behavior evidence, not Human Product Acceptance.

## Boundary evidence

- semantic wire schema contains no `natural_response`;
- conversation wire schema contains only `natural_response`;
- Conversation Provider input is bounded Context plus structured result;
- it uses no tools, hidden memory, or repository inspection;
- Work/Plan/Design/Authority/Verification/SPG ownership is unchanged;
- machine-facing production contracts never pass through rewriting;
- streamed deltas still converge on one persisted Watt message;
- proof activity created zero Work and production facts.

## Validation results

- Conversation, Provider, WIC, Guided Design, configuration, and composition
  contracts: **23 passed**;
- frontend state and one-message streaming lifecycle: **24 passed**;
- affected PostgreSQL WIC, governed Work admission, API/application,
  long-lived Work, and Steering reconstruction: **111 passed, 6 protected real
  Provider tests deselected**;
- six mandatory real Provider conversation modes: **PASS** through staged
  combined/targeted evidence described above;
- Alembic current/head: **`20260908_28 (head)` / `20260908_28 (head)`**;
- compile/import: **PASS**;
- `uv lock --check`: **PASS**;
- `git diff --check`: **PASS**.

No full regression ran. The disposable proof and regression databases created
no Work or production facts.

## Findings

`PRODUCT_EXPERIENCE_FINDINGS`:

- two-stage Provider separation improves architectural clarity and
  conversational control but currently increases response latency;
- bounded native context is sufficient for admitted cases; full semantic
  retrieval remains a future ECF concern;
- Human Product Acceptance is still required.

No Conversation Architecture STOP, Truth-ownership change, lifecycle change,
or Human Authority change was required.
