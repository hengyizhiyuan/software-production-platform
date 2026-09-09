# Design Intent Framing Focused Validation

Status: **FOCUSED DETERMINISTIC VALIDATION PASS / REAL PROVIDER PROOF PASS**

Real Provider Proof: **PASS — `gpt-5.6-sol`**

Date: **2026-09-09**

## Validation subject

The validation binds the Design Intent Frame domain contract, WIC semantic
wire schema and prompt, frame-driven Guided Design selection, persisted
Interaction Assessment reconstruction, Shared Understanding projection,
Human-correction behavior, and migration `20260909_29`.

## Deterministic evidence

- Design Intent Framing, Conversation Intelligence, Guided Design, WIC wire,
  and persistence-foundation contracts: **34 passed**.
- WIC pre-Work plus governed Work/Guided Design affected integration suites:
  **34 passed, 7 real Provider tests deselected**.
- Explicit correction path: an operational-activity frame selected no
  product/system schema; a later Human correction produced a
  `PRODUCT_SYSTEM` frame, selected the general product/system schema, retained
  append-only assessment history, reconstructed after service restart, and
  created zero Work/production facts.
- Alembic round trip on isolated `spg_design_intent_test`:
  `20260909_29 -> 20260908_28 -> 20260909_29` **PASS**.
- Final migration current/head during focused validation:
  `20260909_29 (head)` / `20260909_29 (head)`.

The broader combined run also exposed one environment-identity assertion in
`test_db_01_connectivity`: it expects the database name `spg_test`, while this
mission intentionally used the isolated `spg_design_intent_test`. The affected
WIC/Guided Design suites and migration path passed; this database-name mismatch
is not represented as a product failure.

## Case evidence

| Case | Expected framing | Result |
| --- | --- | --- |
| “我要做一个电商系统。” | `PRODUCT_SYSTEM`, general product/system schema | PASS |
| “我要优化研发效率。” | `UNKNOWN`, explicit ambiguity, no premature schema | PASS |
| “我要给现有运营后台增加直播排期。” | `FEATURE`, existing-product evolution | PASS |
| “我想策划一次 Watt 发布直播。” | `OPERATIONAL_ACTIVITY`, no forced product schema | PASS |
| Watt-promotion operations platform with audience/channels | platform remains `PRODUCT_SYSTEM`; promotion is context | PASS |
| Human correction from activity to backend system | new frame and schema replace current candidate; history remains | PASS |

## Real Provider evidence

After explicit Human authorization of the exact egress messages, one bounded
proof executed the following three-turn correction sequence:

1. “我想做一个运营管理平台。”
2. “这个平台主要用于推广 Watt，目标用户包括个人开发者、小型开发团队，渠道包括公众号、小红书和直播。”
3. “不对，我不是要设计运营活动，我是要开发一个后台系统。”

The proof completed with **3 Interaction Turns**, **6 Provider Threads**, and
**6 Provider Turns**: one existing WIC semantic Turn and one existing
Conversation Intelligence Turn per Human message. All three persisted frames
classified the design object as `PRODUCT_SYSTEM`; the general product/system
schema remained selected. Business audience and channels remained context.
The correction changed the subject to an explicit Watt-promotion operations
backend and the Human-facing response acknowledged that the object was a
backend system rather than an operations activity.

The success artifact was written only after assertions proved append-only
frame history, correction-aware schema selection, and zero Work/production
facts. The sanitized local artifact was
`.spg/validation-evidence/design-intent-framing-real-provider.json`; it is
validation output and is not admitted as repository source.

## Provider-call and authority guard

The implementation adds no LLM stage. Framing is emitted by the existing WIC
semantic Turn and consumed by the existing Conversation Turn. Deterministic
validation created no Work, PWU, Run, production Attempt, Runtime Commit, or
Trusted Baseline mutation.

The first command submission was rejected before execution because explicit
confirmation of the three Chinese egress messages had not yet been supplied.
That historical pre-execution block created no Provider Thread or Turn. After
the Human supplied exact authorization, one proof ran with no retry and no
resume. It created no Work, PWU, Run, production Attempt, Runtime Commit, or
Trusted Baseline mutation.
