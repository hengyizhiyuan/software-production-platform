# C3 — Capacity & Representation Review

## Summary

**Specialty result: Controlled Qualified. Overall: Outcome B / C3 PARTIAL — actual capacity recovery unproven.** Exact source `e0df8196` and image `sha256:7a4ac00e…732f7b35` have **191 installed-source PASS + 4 isolated PG PASS**, with zero errors/skips in those final groups. Older failures and the first PG setup error remain preserved; repeated groups are not added as unique coverage.

The same 26-component structural sample shrinks from 9,924 to 2,158 output bytes, while the actual request grows from 47,135 to 54,365 bytes. The combined 536-byte reduction is serialized-byte arithmetic, not tokens or compute. Provider `max_output_tokens` causal exclusivity, reasoning/visible usage and live recovery remain UNKNOWN. This round performed **zero real model calls, no new G0 and no Holdout access**.

The [exact live decision package](live-model-decision-package.md) has been submitted to Human: at most one formation plus one conditional independent review, unchanged profile, no Self-Refine or Work writes. It is **awaiting explicit authorization; no call has been made**. The exact image archive is persisted with a hash and `0600` mode; restore qualification and offsite copy were not performed.

Final scoped review recorded: **2026-10-09 16:37:58 UTC / 2026-10-10 00:37:58 Asia/Shanghai**. Source `e0df8196cb51480f542af13b40cfa77fca6b6a6e`, tree `d479d61f5fcac075a5af3a274f60cbe3f6e9f53f`, exact image `sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35` (`watt-c3-capacity:e0df819`). This report does not close C3, authorize another model request or G0, or change a Human/Guardian gate.

## 1. Evidence and exact identities

| Observation | Exact identity / evidence | What it establishes |
|---|---|---|
| Previously authorized Provider diagnostic | Source `d8ea0642f0c360794e69c366e8f15fa369eeed0b`; image `sha256:51c0b8be88969720cb3a3cfc4e047edc7f229aa22348a95a89cbb4bf83a18e39`; [diagnostic](../continuation-20261010/historical-provider-diagnostic-1/provider-diagnostic.json) and [container identity](../continuation-20261010/historical-provider-diagnostic-1/container-identity.json) | E1, PROVEN_SCOPED: one authorized diagnostic's Provider events and terminal failure, not original Work success or historical cause. |
| Current offline capacity baseline | Source `e8e04b296b31d776a13dda728fa19469681cbaab`; evidence baseline `6fbc692de4696ff5a1b9ea3073fe4c42bc405292`; image `sha256:4d3c64b1e3543a3574cd69b435d6f703fad6edc23b9db7d54d799dc1a652bf6e`; container `51322ad97a301392170478a4fd65ce1388fec934217d58ef94125418116c4634` | [Execution receipt](baseline-execution-receipt.json): exit 0, `network_mode=none`, read-only basis/controller, zero model/HTTP requests and credential inputs. |
| Deterministic aggregate measurement | [Measurement](capacity-measurement.json), SHA256 `fbcd899b4b8d7831f5764f75d812d24e74e5afe0aeb308765162f36e4d9dd105`; [controller](measure_capacity.py), SHA256 `c87fe121a10c338ceac3310b7b694988140253642000af7bdffabbe5ff1d918d` | E2, PROVEN_SCOPED: offline exact-source serialization and reversible sizing fixtures. No live model or semantic qualification. |

The fixed safe canonical snapshot has SHA256 `9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c`, Work `048189aa-0613-5307-b6f4-c430e7977f93`, Reality `332a3a38-8719-580c-a1a2-c331ae14a5ae`, inventory `7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf`, and target-source revision `465038ded6cf4ba335a11577de76acb1dea55b76`. The target-source revision is distinct from the Watt application revision. The controller checked exact basis hash, inventory fingerprint, source order and capability hash. It reconstructed the current baseline request with installed modules; no retained original HTTP body is being replaced by an invented historical byte receipt.

Installed Owner/source hashes are in `capacity-measurement.json`. Relevant exact-`e8e04b2` code references are `application/governed_obligations.py:607` (`fulfillment_inventory`), `:1189` (`fulfillment_capability_contracts`), `:1220` (semantic-review pending receipt), `:1285` (Provider entry count), `:1312` (two formation attempts); `providers/fulfillment_candidate.py:90` (`form`) and `:153` (`review`); `infrastructure/model_runtime.py:361` (`_payload`) and `:390` (`_compact_schema`); `domain/governed_obligation.py:47`, `:225`, `:237` (component, route and projection contracts). These are E3 code references, not evidence that a newer implementation passed Runtime qualification.

## 2. Established failure and causal limits

**PROVEN_SCOPED / E1:** the authorized diagnostic began `2026-10-09T15:06:57.030966Z`, queued/sent one logical model entry, accepted HTTP 200 and a first response event, and ended `2026-10-09T15:07:53.359970Z`. The terminal was `INCOMPLETE_RESPONSE`, `provider_status=incomplete`, `termination_reason=max_output_tokens`, with request ID `d504da81-846e-45a1-8411-1f5b6edb2c08`. The observed wall time was 56.328976289 seconds. This diagnostic did not observe an HTTP rejection or a timeout terminal. Its output contract was `NOT_REACHED`; no parsed fulfillment Candidate, semantic review or Work qualification resulted.

**UNKNOWN:** original failed Work's Provider details remain unknown. The diagnostic's numeric input/output/reasoning/total usage and visible-JSON token count are also unknown in the retained receipt. `reasoning_effort=low`, `max_output_tokens=16384` and the terminal reason do not reveal the split between reasoning and visible output, the provider's accounting semantics, or which request/output component exhausted capacity.

**PROVEN_SCOPED / E2:** representation repetition and structural wire cost are measurable below. **HYPOTHESIS:** removing that repetition may improve completion reliability. Sizing alone does not prove repetition was the only cause, that 9,924 bytes is the actual diagnostic output length, or that a 2,829-byte structural fixture will produce a semantically valid plan. No byte-to-token conversion or probability estimate is made.

## 3. Exact baseline request size

The reconstructed request uses 26 sources and 12 existing capability contracts. The actual source-kind distribution is **FACT 6, IR_CLAUSE 4, IR_CONSTRAINT 4, WORK_CONSTRAINT 11, WORK_CONTEXT 1**. This corrects a preparation-message counting error; the saved aggregate is the authority for these counts.

| Part | UTF8 bytes | Unicode characters | Serialization |
|---|---:|---:|---|
| Immutable inventory | 37,488 | 37,488 | Actual input's default JSON spacing |
| Existing capability contracts | 2,608 | 2,608 | Actual input's default JSON spacing |
| Instructions | 2,365 | 2,365 | Exact installed constant |
| Complete `input_text` | 40,196 | 40,196 | Inventory + capabilities + feedback envelope |
| Typed / strict schema | 1,915 | 1,915 | Compact JSON spacing |
| Actual compact strict schema | 1,252 | 1,252 | Adapter removes annotation-only keys |
| Complete HTTP JSON entity body | **47,135** | **47,135** | Installed `httpx2.Request(json=payload)` serialization |

The body SHA256 is `b009bcbdec9e82f6fa24dc7f0c8eb14d2c3ea1c120b2735a3b6e08e67cfb6d82`. The request was constructed in memory and was not sent. The body includes the input string's JSON escaping, instructions, schema and profile fields; the rows overlap and must not be summed. Authentication/header/TLS/framing bytes were not measured. Byte and character counts happen to match for this retained basis and are not assumed equal for future Unicode inputs.

The schema is already compacted: 1,915 → 1,252 bytes removes 663 bytes of annotation overhead while retaining constraints. This does not eliminate the larger immutable input or generated output repetition.

## 4. Repetition and growth

The inventory contains 556 string-value occurrences, 150 distinct string values and 89 repeated values. Raw string-value bytes total 20,832; distinct values total 6,182; repeated raw bytes total 14,650. These exclude JSON keys, delimiters and escaping. Nested subtree measurements overlap and cannot be added to this raw-string total.

| Fixed field subtree | Occurrences / distinct | Repeated serialized value bytes |
|---|---:|---:|
| `item` | 8 / 5 | 4,391 |
| `source_text` | 73 / 12 | 4,322 |
| `provenance` | 17 / 12 | 1,531 |
| `production` | 8 / 2 | 1,125 |
| `content` | 23 / 12 | 704 |
| `clause` | 8 / 7 | 447 |

The source array itself occupies 33,644 default-spacing bytes. Work constraints are also projected at inventory level, and the Item payload is repeated for surviving Clause–Item pairs. These repetitions preserve real identity, provenance and semantic context today; deleting them without a deterministic recovery contract would be unsafe.

The current domain schema caps routes at 1,024, rationale at 1,000 characters and component quote at 65,536 characters. Exact-source/capability uniqueness gives a 26 × 12 = 312 possible pair ceiling for this basis, before stricter semantic guards. This pair ceiling is a deterministic admitted-identity constraint, not an assurance that the provider will emit only that many valid pairs.

There is no established universal inventory byte bound, and no finite overall pre-validation output byte bound from the current schema: some reference strings, arrays and integer lengths lack upper bounds. **Measurement caveat:** `fields_without_schema_upper_bound` mechanically reports missing `maxLength`/`maxItems`/`maximum`; it also lists `inventory_fingerprint`, whose exact 64-character regex does constrain that particular field. That coarse list is not a claim that the fingerprint itself is unbounded. The other missing limits still prevent a finite total schema byte ceiling.

## 5. Structural representation experiments

All output experiments use one all-UNRESOLVED, full-source component per source. They are sizing fixtures, not legal semantic plans, a historical model response, an Assurance result or a qualification PASS. Real mixed obligations may require more than one route per source and additional supporting Fact/target references.

| Representation | Compact UTF8 bytes | Difference from existing fixture | Proven scope |
|---|---:|---:|---|
| Existing full-reference/full-quote fixture | 9,924 | Baseline | Current typed structure only |
| Same fields, quote reconstructed from exact original span | 7,478 | −2,446 / −24.65% | Exact roundtrip asserted for this fixture |
| Inventory-bound source/capability ordinals and spans | 2,829 | −7,095 / −71.49% | Structural cost only; no implemented codec or semantic roundtrip qualification |

Separate input experiment: interning 32 repeated strings produces 31,568 compact bytes versus 35,835 for the original compact inventory, a 4,267-byte reduction. Exact expansion back to the inventory was asserted. This does not show the model can use such a representation, and is not the proposed main repair. Input/context readability and semantic review may have costs that byte savings do not measure.

## 6. Bounded implementation direction and invariant protection

The smallest direction is a **private Provider wire representation** with deterministic recovery into the unchanged formal `FulfillmentProjectionCandidate`. The model continues selecting semantic contribution, existing consumer capability and original-source linkage. The existing Owner can reconstruct exact source references, source quote from validated source span, Work-constraint index from its source, and Owner/phase/evidence/Gate tuple from the selected capability. Inventory and capability fingerprints, ordinal bounds, exact spans, target scope, original Fact references, values/order/qualifiers, continuous permissions and full source coverage remain strict.

This recovers metadata; it does not decide semantic equivalence or create permissions. The same independent semantic review must consume the recovered formal Candidate. Current Fact/content/Git/Source obligations remain current checks; lifecycle obligations remain with their actual gates. Unsupported/missing/ambiguous references remain unresolved or rejected, and a wrong quote/span must not be repaired by changing the source. No Subject alias, business vocabulary table, added Owner, parallel state machine or public formal contract change is required by the measured overhead itself.

Keep the existing **at most two formation attempts, one feedback Self-Refine, one independent review per candidate and at most four logical Provider entries**. Transport replay counts remain separate from logical entries. Same-basis receipt replay must not reset consumption; unknown/pending outcomes must not be rerun. No model profile/output allowance increase, new diagnostic/G0 request or Holdout access is authorized by this review.

The private-wire source has now been frozen as `e0df8196cb51480f542af13b40cfa77fca6b6a6e`, tree `d479d61f5fcac075a5af3a274f60cbe3f6e9f53f`. Exact source diff from `e8e04b2` changes only `src/spg/providers/fulfillment_candidate.py` and `src/spg/application/governed_obligations.py`: Provider-local context/schema/decoder, safe raw-response observation, pending/observed wire-identity continuity, and truthful capacity stop. It does not change the formal domain Candidate or independent semantic-review contract, Guardian, ECF, accepted Facts or model budget. The temporary `f/t/u` reference arrays have no newly introduced 1,024-item limit; the earlier extra limit was removed to avoid restricting the existing formal contract. Existing 1,024 routes, 64 KiB safe output and 128 KiB Owner receipt boundaries remain.

At exact `e0df8196`, `providers/fulfillment_candidate.py:108` builds the private schema; `:113` constructs exact request-local dictionaries/fingerprints; `:158` decodes to the formal Candidate; `:216` handles decoded synthetic-secret privacy before safe raw-response retention; `:268` exposes wire metadata; `:272` forms the candidate; `:352` keeps independent review. `application/governed_obligations.py:1267` and `:1280` consume existing formation receipts and bounded outcomes. These are E3 implementation references. Development results are in section 9; final baked-image, actual offline codec and isolated database evidence are in section 10.

The [actual codec controller](measure_compact_wire.py) captures actual Provider kwargs using a controlled Runtime fixture; real ModelRuntime/HTTP entries remain zero. Its final-image result now compares new instructions, input, compact schema and complete entity body against the old aggregate, including the increased input. The controlled regression proves recovery, reference rejection, original Fact/scope/authority protection, mixed components and receipt/budget behavior within its tested fixtures; it does not prove a live model will generate a valid plan or restore the original production path.

## 7. Actual time, cost and recovery location

- Offline execution: `2026-10-09T16:01:08.414097Z` → `16:01:14.049380Z`, enclosing wall time 5.635283 seconds. In Asia/Shanghai this is **2026-10-10 00:01:08.414097 → 00:01:14.049380**.
- Measurement body: `16:01:09.525076Z` → `16:01:13.174880Z`, 3.649806130 seconds. This is nested in the enclosing time; do not add them.
- This measurement: **0 model requests, 0 HTTP requests sent, 0 credential inputs, 0 Work/Owner writes**. It used an existing image; no new build or production environment was created. Actual CPU time, peak memory, money cost and token counts are UNKNOWN/not measured.
- The earlier authorized diagnostic is separate: 1 logical model entry, 56.328976289 seconds, numeric token/cost/replay count UNKNOWN in its retained receipt. Zero observed transport-recovery stages is not a substitute for a typed actual replay count.

Cross-computer public recovery location: `/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/baseline-measurement-1/evidence/`. This folder contains the local copied measurement and enclosing receipt; their hashes above allow content verification. The inputs remain in the exact public canonical snapshot and prior diagnostic paths recorded in `baseline-execution-receipt.json`. New review/implementation/test receipts must remain separate from these retained baseline observations.

**Current conclusion: representation recovery and receipt handling are PROVEN_SCOPED; causal exclusivity, live model convergence and C3 closure are not established.**

## 8. Independent local receipt-capacity defect

**DEFECT_CONFIRMED / E2, causal status CONFIRMED_EDGE:** a controlled expanded-candidate counterexample ran once against the exact baseline image `sha256:4d3c64b1e3543a3574cd69b435d6f703fad6edc23b9db7d54d799dc1a652bf6e`, with **no source overlay**, a separately mounted test SHA256 `7b9d70d7a57775f78317b64e8fd74be49423677e2ada570fd5e3a6c3a94e7b68`, `network=none`, no model calls or database/Work. Its synthetic individual component texts fit the existing quote bound, while the complete candidate exceeds the existing 131,072-byte Owner receipt limit. It records `MODEL_RESPONSE_OBSERVED` as terminal `OBLIGATION_FORMATION_RECEIPT_LIMIT`, without candidate body. Replay already returns UNRESOLVED without another provider entry. The current invocation nevertheless continues after that durable terminal and escapes as `OBLIGATION_FORMATION_PENDING_OR_TERMINAL` instead of returning the same truthful UNRESOLVED outcome.

The [baseline receipt](baseline-limit-receipt.json), [sanitized failure](baseline-limit-failure.log) and XML preserve **1 FAIL**, `2026-10-09T16:02:48.256457Z` → `16:02:56.073809Z`; pytest reports 3.64 seconds and the enclosing wall time is 7.817352 seconds. The negative test failure is evidence of this local completion-boundary defect; it must not be changed into a baseline PASS.

Root's minimal stop handling was then checked in a **development source overlay**, using the same base image as dependency runtime. [Development receipt](development-limit-fix-1/receipt.json) records manifest SHA256 `a19aca3607bd56f0fa9a4a5d057f2e850ca36692a4e16543292cd43ff76b59a2`; `application/governed_obligations.py` overlay SHA256 `6ca199e28de5845bd992c3d14ea1c90007f2ff4b1847895a415029fee61b0c65`. The exact controlled capacity test and existing projection/provider-failure groups give **31 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, `2026-10-09T16:05:35.296249Z` → `16:05:44.620399Z`, 9.324149949 enclosing seconds; pytest reports 4.94 nested seconds. Network and model calls remain zero. This is scoped development repair evidence, not a new baked-image qualification or a real Work.

The confirmed edge is **Owner observation-size terminal → local return/replay continuity**. It is independent of the Provider's output-token terminal. The prior Provider diagnostic did not return a parsed candidate, so these records do not establish that its failure crossed the receipt limit. No Provider budget, receipt capacity, retry count or admitted Fact was expanded to make the test pass. The repaired source/image and scoped final regression are recorded in section 10.

## 9. Private-wire development ledger and confirmed seams

All three groups below used the baseline `4d3c64b1…` image as dependency runtime with **explicit development source overlays**, `network=none`, zero real model calls, zero errors/skips. They are not qualifications of the unmodified baseline image or the frozen new image. Every failure receipt remains preserved.

| Group | Actual UTC execution | Enclosing wall seconds | Actual result | Classification |
|---|---|---:|---|---|
| [development-wire-1](development-wire-1/receipt.json) | 16:17:15.281735 → 16:17:28.181581, 2026-10-09 | 12.899856507 | 187 tests: **180 PASS / 7 FAIL** | Seven positive fixtures used a qualified `SCOPE` value (`complete:true`) with a checker that already supports only unqualified literal file scope. Its rejection was correct. The fixture's claimed positive qualification was invalid; this is not a Runtime capability regression or evidence that the Provider issue was solved. |
| [development-wire-2](development-wire-2/receipt.json) | 16:23:11.222204 → 16:23:21.457046, 2026-10-09 | 10.234835508 | 44 tests: **42 PASS / 2 FAIL** | Two independent C3 source/observation seams confirmed below. |
| [development-wire-3](development-wire-3/receipt.json) | 16:26:22.834266 → 16:26:33.433238, 2026-10-09 | 10.598965990 | **75 PASS / 0 FAIL** | Scoped development repair: 45 capacity/wire/privacy cases + 21 existing projection + 9 existing Provider-failure cases. New-image and database evidence still pending. |

Development-wire-2 confirmed **DEFECT_CONFIRMED / E2, causal status CONFIRMED_EDGE** at two bounded seams:

1. `test_actual_provider_observation_never_retains_decodable_unicode_escaped_synthetic_secret`: the **FORM** parameter was the actual failed privacy case; escaped fixture secret text could survive raw-string privacy observation even though decoding exposed the sensitive value. The repair protects Provider-local FORM and REVIEW safe observation of decoded JSON before raw retention. REVIEW negative coverage later passed; no REVIEW privacy failure is being claimed. The repair does not change semantic requirements, remove difficult sources or consume another model attempt. The sentinel is synthetic controlled data; this test does not prove a new real credential exposure occurred.
2. `test_complete_pending_wire_metadata_cannot_replay_a_fully_unmarked_observation`: an existing compact pending receipt could be followed by an observation with all compact markers missing and enter a legacy interpretation. The repair keeps actual pending/observed codec selection and exact request/table/schema/version identity continuous; missing observation identity is rejected, not treated as a fresh legacy plan. No same-basis budget reset or added retry is allowed.

Wire-3 manifest SHA256 is `dcfcadef3186d3d2be654e3e9aa04585efdeffc53e0ddd0a4afd64a3f8c8f488`; wire-1 and wire-2 manifests remain `d2b2a04bae7af047765d2f4b3307eccc091355367baa9f7e1d93fdcf440f0911` and `f339e31318a8056f25cbc56eef2e0397cb4a3080554f5439508f3e9b7c43bc4c`. Recorded cases are not unique case totals across groups and must not be added as final revision coverage. Logical fixture entries are not real Provider requests or transport retries. CPU/memory/token/money costs remain unmeasured, and the nested pytest durations must not be added to enclosing times.

None of these seams demonstrates that the earlier `max_output_tokens` cause was unique or removed. Actual Provider completion, reasoning/visible output use and C3 closure remain unproven under this zero-call mission.

## 10. Final exact-image qualification and actual wire costs

The [build](final-image/build.json) completed at source `e0df8196cb51480f542af13b40cfa77fca6b6a6e`, tree `d479d61f5fcac075a5af3a274f60cbe3f6e9f53f`, image `sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35`, with tag `watt-c3-capacity:e0df819`. [Actual installed imports](final-image/actual-imports.json) report PASS and the same caller-observed image; no source overlay is used. The unchanged Owner versions are Guardian `d01bac1ad153e1eadefafe87d2ea4f5d65896ab6` / tree `4f75d9137bebc7bf956fe4466cbae93f88c5c03b`, and supported ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c` / tree `878d39d9c259272bb05f2e02bdf9d60c22fad460`. ECF `c6b568d006022e39b95daebedfecfb55e562ebe5` is a separately baked incompatible-version negative input, not the selected runtime Owner.

**PROVEN_SCOPED / E2:** [final installed-source regression](final-image/watt-continuation-receipt.json) gives **191 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, without source overlays, live model calls, real AI Work creation or original business database access. Its selected capacity/wire cases include both FORM and REVIEW privacy negatives. This qualifies the tested representation, identity, bounded receipt and unchanged Owner/gate mechanisms; it is not a real G0 or a claim of model-generated semantic success.

**PROVEN_SCOPED / E2:** [actual compact-wire measurement](exact-wire-measurement-1/actual-compact-wire-measurement.json) and [image receipt](exact-wire-measurement-1/receipt.json) run the same baked image, `network=none`, `source_overlay=false`. The actual Provider form uses one capture-only fixture entry, zero real ModelRuntime/HTTP entries, and the actual decoder. All **26 sources, 26 components and 26 unique source references** are retained. Formal typed JSON, Candidate fingerprint and component fingerprint roundtrip exactly:

- Candidate fingerprint `0d730618d1c9d2d9978061bfb05f447cc16ebf4951390848adec29cdd5b79cfc`.
- Components fingerprint `76468b237c28fba482b20f67b5729d1e2af30807c308a35340321affd0fd379d`.
- Request fingerprint `4b995573e01820631e063d0108388140be8576c3ac385a38da88d8ee87ea62d4`.
- Table fingerprint `cddd1ffc3429695d19411d42c5d6b741534460496705dbb0a430ff138df9e429`.
- Private schema fingerprint `5668e226eb8d38c0f4bf9004ea8fc7aa363e9d388f64927783252f562d78ad40`.

The sample remains **all-UNRESOLVED structural sizing**, not an admitted legal plan or independent semantic-review PASS. Its actual wire cost, rather than the preliminary ordinal experiment's 2,829 bytes, is:

| Metric | Old baseline bytes | Actual new bytes | Delta |
|---|---:|---:|---:|
| Instructions | 2,365 | 2,929 | +564 |
| `input_text` | 40,196 | 46,720 | +6,524 |
| Compact strict schema | 1,252 | 876 | −376 |
| Complete HTTP JSON entity body | 47,135 | **54,365** | **+7,230** |
| Same 26-component structural output | 9,924 | **2,158** | **−7,766 / −78.254736%** |
| Request body + this sample output | 57,059 | 56,523 | **−536** |

The new request is larger because it includes exact recovery tables and protocol instructions. The 536-byte combined reduction is **serialized byte arithmetic only**, not a token, compute, money, capacity-cause or Provider reliability result. Output compactness is established; actual Provider completion and reasoning/visible output accounting remain UNKNOWN.

**PG qualification:** the first [owner-pg attempt](owner-pg/setup-failure-receipt.json) has **4 SETUP ERROR / 0 PASS**. The controller chose `spg_c3_capacity_fixture`, which the existing destructive-test fixture guard correctly rejected because it requires the known isolated name `c1_contract_continuity`. This is a controller setup error before schema setup, not a Runtime regression; migration was `UNKNOWN_NOT_CREATED`, and the original receipt/log/XML remain preserved.

One controller configuration correction then ran [owner-pg-retry-1](owner-pg-retry-1/receipt.json): **4 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, migration `20261007_72`, same exact baked image, no source/test overlay, fresh isolated `c1_contract_continuity` database on an internal network, and no original database access. It proves the tested persistence/replay/stop behavior through actual PostgreSQL Owner records using controlled fixtures. It creates fixture data only, not a real AI Work; there are no live model calls or production resource changes. Root reports that the isolated PostgreSQL service was stopped after qualification.

| Final operation | Actual UTC window on 2026-10-09 | Observed enclosing wall seconds |
|---|---|---:|
| Image build | 16:27:26.138756 → 16:27:49.351610 | 23.212923204 |
| Installed-source regression | 16:27:52.613162 → 16:28:06.077882 | 13.464729104 |
| Actual codec measurement | 16:28:42.928819 → 16:28:50.293303 | 7.364484 derived from enclosing timestamps; inner measurement 5.047372340 |
| Corrected isolated PG qualification | 16:30:59.646659 → 16:31:23.688535 | 24.041838132 |

In Asia/Shanghai these windows are on **2026-10-10**, eight hours later. Inner codec timing is nested; some surrounding controller windows overlap. These numbers must not be summed as total compute or elapsed mission cost. This bounded capacity mission has **zero real model requests, zero new G0 and no Holdout access**. Token/reasoning/visible-output, CPU, peak-memory and monetary costs remain unmeasured. Every prior failure and setup error remains visible.

## 11. Outcome and exact next decision

**Outcome B — scoped representation and receipt mechanism qualification achieved; actual Provider capacity recovery unproven.** No new engineering blocker is inferred merely because the currently authorized zero-call qualification cannot observe Provider behavior. C3 remains unclosed, and original failures, Facts, Candidates, decisions and standards remain unchanged.

The next proposed action requires **new explicit Human authorization for this round**: run the qualified exact image against the same existing retained inventory for **one formation request and, only if a Candidate survives deterministic plan checks, one independent semantic review**. Maximum **two logical calls**, unchanged `deepseek-flash`, reasoning `low`, `max_output_tokens=16384`, timeout 120 seconds; **no feedback Self-Refine**, no further logical retry, no Work/Owner mutation, no new G0 or Holdout. Existing adapter transport recovery remains separately counted: at most one pre-response replay per logical entry, hence at most **four HTTP requests** if both logical calls and their allowed replays occur. It must not be concealed as a second logical formation or a new repair allowance. Capture request/table/schema identity, terminal state, actual numeric usage when present, safe Provider fields and review outcome. Neither parsed output nor plan semantic validation creates Assurance PASS, Human authority or Work closure.

The [concrete decision package](live-model-decision-package.md) has been submitted and is **awaiting Human response**, with no call executed. The earlier authorization for a single historical diagnostic does not authorize a second call. Until an exact new decision and resulting evidence exist, the report must not claim `max_output_tokens` causality is eliminated or capacity recovery proven.

Public cross-computer evidence is recoverable under `/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/`: `final-image/`, `exact-wire-measurement-1/`, `owner-pg/` and `owner-pg-retry-1/`, alongside the retained baseline/development folders. Selected final artifact SHA256 values:

- `final-image/build.json`: `5dae7d24959583087281b8359a41bc902934b4e8032d3f43ab08975543f39c38`.
- `final-image/watt-continuation-receipt.json`: `08374b127e494f6596d81e526d64c1bc32674c01f5dbb9861c2d63cdf2d0d6ef`.
- `exact-wire-measurement-1/actual-compact-wire-measurement.json`: `0cd9f2fa1e1795ad2e537b7822b897163abbb2f897b5f5df7aa9b594ab303ad7`.
- `owner-pg/setup-failure-receipt.json`: `9dc8dc270af05b61aab5453187bc2e38fdd68c5fcbadfc22120b0e83164f30e8`.
- `owner-pg-retry-1/receipt.json`: `8bbdb98441feb0409102f34cc7e1848b95c5f5f8a1834ccfc5ced6b505627ff9`.

The [image recovery receipt](image-recovery-receipt.json) additionally records the exact qualified image archive at `/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/image-recovery/exact-image.tar.gz`, SHA256 `35576c81785997c4ff1e6d347671bdf283b0f38323875e3218affffbca8f4949`, **293,129,132 bytes**, mode **0600**. Archive persistence ran `2026-10-09T16:33:26.565574Z` → `16:36:23.006326Z`, wall 176.440748584 seconds. This records a stored recovery artifact, not a tested restore or offsite backup: both remain **NOT_PERFORMED**. No production resource was mutated. The archive time is a separate I/O observation, not model/token cost.
