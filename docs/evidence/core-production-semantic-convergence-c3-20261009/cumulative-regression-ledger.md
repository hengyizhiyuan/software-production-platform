# C3 cumulative regression and consumption ledger

Captured 2026-10-09T13:50:38.784388+00:00 — **READY_FOR_REPORT**

Independent engineering ledger. This status means accounting is ready for reporting; C3/N1 remains PARTIAL. No Human Acceptance or complete Work qualification is granted.

## Execution and measured cost

- **39** distinct retained receipt/XML execution groups counted once: **1781 PASS / 42 FAIL / 55 ERROR / 52 SKIP** (1930 raw report entries).
- The 15 PASS development terminal group was already counted in the prior 38 groups. Only the image3 related deterministic 216 PASS group is added.
- ERROR includes one remote collection placeholder, not an executed body. Setup errors likewise do not prove test bodies executed.
- Measured group wall sum **1630.883485663s**; local Windows collection **6.3609231s**; combined measured sum **1637.244408763s**. These are sums of receipt walls, not CPU, campaign elapsed time or invoice cost.
- The original 3 final-image groups have no local XML; their node coverage remains UNKNOWN.
- The explicit current Owner/classname/name algorithm counts **456 distinct available XML nodes**, with **0 new node identities** in image3 and 1156 repeated observations. The prior 452-node mapping is preserved unchanged in JSON. The 4-node method discrepancy is UNKNOWN, not credited as new coverage. Repeated execution and node identities do not establish unique requirements, nonpreset semantics or generalization.

| Receipt group | PASS | FAIL | ERROR | SKIP | Exit | Wall s |
|---|---:|---:|---:|---:|---:|---:|
| dev-regression-1/c1-chain-receipt.json | 0 | 0 | 0 | 50 | 0 | 11.103 |
| dev-regression-1/c3-carrier-receipt.json | 0 | 0 | 0 | 2 | 0 | 11.112 |
| dev-regression-1/guardian-unit-receipt.json | 75 | 18 | 0 | 0 | 1 | 19.094 |
| dev-regression-1/watt-unit-receipt.json | 103 | 4 | 0 | 0 | 1 | 13.996 |
| dev-regression-2/c1-chain-receipt.json | 0 | 0 | 50 | 0 | 1 | 96.878 |
| dev-regression-2/c3-carrier-receipt.json | 0 | 0 | 2 | 0 | 1 | 18.689 |
| dev-regression-2/guardian-scoped-receipt.json | 88 | 0 | 0 | 0 | 0 | 12.649 |
| dev-regression-2/watt-scoped-receipt.json | 18 | 2 | 0 | 0 | 1 | 9.966 |
| dev-regression-2-static-fixture/static-model-fixtures-receipt.json | 2 | 0 | 0 | 0 | 0 | 8.939 |
| dev-regression-3/c1-positive-receipt.json | 0 | 0 | 2 | 0 | 1 | 18.785 |
| dev-regression-3/guardian-scoped-receipt.json | 99 | 0 | 0 | 0 | 0 | 17.121 |
| dev-regression-3/watt-scoped-receipt.json | 79 | 10 | 0 | 0 | 1 | 15.011 |
| dev-regression-3-coverage-integration/c1-positive-receipt.json | 2 | 0 | 0 | 0 | 0 | 30.924 |
| dev-regression-3-coverage-integration/watt-coverage-receipt.json | 31 | 0 | 0 | 0 | 0 | 8.801 |
| dev-regression-3-fixtures/c1-positive-receipt.json | 0 | 2 | 0 | 0 | 1 | 20.735 |
| dev-regression-3-fixtures/watt-fixture-failures-receipt.json | 10 | 0 | 0 | 0 | 0 | 8.998 |
| dev-regression-3-guardian-contract/c1-positive-receipt.json | 0 | 2 | 0 | 0 | 1 | 20.579 |
| dev-regression-3-guardian-contract/c3-carrier-receipt.json | 2 | 0 | 0 | 0 | 0 | 15.594 |
| dev-regression-3-guardian-contract/guardian-components-receipt.json | 35 | 0 | 0 | 0 | 0 | 7.298 |
| dev-source-facets-1/watt-scoped-receipt.json | 0 | 0 | 1 | 0 | 2 | 11.178 |
| dev-source-facets-1-test-parameter-retry/watt-scoped-receipt.json | 107 | 2 | 0 | 0 | 1 | 11.613 |
| dev-source-facets-2/c1-positive-receipt.json | 2 | 0 | 0 | 0 | 0 | 42.936 |
| dev-source-facets-2/c3-carrier-receipt.json | 2 | 0 | 0 | 0 | 0 | 17.933 |
| dev-source-facets-2/guardian-scoped-receipt.json | 135 | 0 | 0 | 0 | 0 | 23.039 |
| dev-source-facets-2/watt-scoped-receipt.json | 30 | 0 | 0 | 0 | 0 | 11.995 |
| dev-terminal-fix-1/watt-receipt.json | 15 | 0 | 0 | 0 | 0 | 17.620 |
| final-image-regression/c1-chain-receipt.json | 48 | 2 | 0 | 0 | 1 | 394.568 |
| final-image-regression/guardian-unit-receipt.json | 108 | 0 | 0 | 0 | 0 | 16.740 |
| final-image-regression/watt-unit-receipt.json | 159 | 0 | 0 | 0 | 0 | 18.003 |
| final-image-regression-c1-fixture-retry/c1-constraint-identity-receipt.json | 2 | 0 | 0 | 0 | 0 | 17.949 |
| final-image-regression-c1-fixture-retry/c2-pg-preflight-receipt.json | 2 | 0 | 0 | 0 | 0 | 14.723 |
| final-image-regression-c1-fixture-retry/c3-carrier-receipt.json | 2 | 0 | 0 | 0 | 0 | 14.105 |
| pe-development/receipt.json | 12 | 0 | 0 | 0 | 0 | 7.619 |
| retry-1/final-image-regression/c1-chain-receipt.json | 50 | 0 | 0 | 0 | 0 | 540.623 |
| retry-1/final-image-regression/c2-pg-preflight-receipt.json | 2 | 0 | 0 | 0 | 0 | 17.795 |
| retry-1/final-image-regression/c3-carrier-receipt.json | 2 | 0 | 0 | 0 | 0 | 17.592 |
| retry-1/final-image-regression/guardian-unit-receipt.json | 140 | 0 | 0 | 0 | 0 | 22.645 |
| retry-1/final-image-regression/watt-unit-receipt.json | 203 | 0 | 0 | 0 | 0 | 21.098 |
| terminal-fix-qualification/watt-terminal-receipt.json | 216 | 0 | 0 | 0 | 0 | 24.839 |

Original image543 retains Watt159/Guardian108 PASS and original C1 **48 PASS/2 FAIL**, followed by same-image test-only supplemental identity2/carrier2/C2 PG2 PASS. Retry1 exact91f5/image6f8 has **397 PASS**, no FAIL/ERROR/SKIP (Watt203, Guardian140, C1 chain50, carrier2, C2 PG2). Final exactd8ea/image51c0 has **216 PASS**, no FAIL/ERROR/SKIP, from related installed deterministic fixtures only. The development terminal 15 PASS used an explicit source overlay. Earlier failures remain preserved.

## Collection, build and controller boundaries

- Actual Docker builds: **3**, measured wall total **87.88310848299s**. All actual build receipts are retained. The Windows-path preparation failure happened before Docker and counts as zero builds.
- Windows collection failed on fcntl (exit1, zero test bodies). First remote source-facet collection failed on reserved parameter (exit2, zero bodies). Initial C1/carrier52 SKIP remain SKIP.
- Dev2 pre-test harness failure is retained separately. Receipt/XML hashes, source identities, versions and times are in JSON.
- Retry controller1 SyntaxError exited1 before HTTP. The pre-control2 read-only observation shows product_rows0/work_rows0/no Work/model. Controller2 is a distinct control attempt, not a duplicated Work. Original controller130 and control2 exit0 are not Work PASS.

| Actual build | Image prefix | Exit | Wall s |
|---|---|---:|---:|
| build.json | sha256:54355780b7fdd683… | 0 | 24.347853138 |
| retry-1/build.json | sha256:6f8d9b3a27e7e245… | 0 | 27.539667058 |
| terminal-fix-qualification/build.json | sha256:51c0b8be88969720… | 0 | 35.995588287 |

Final image: `sha256:51c0b8be88969720cb3a3cfc4e047edc7f229aa22348a95a89cbb4bf83a18e39`, Watt `d8ea0642f0c360794e69c366e8f15fa369eeed0b`, Guardian `d01bac1ad153e1eadefafe87d2ea4f5d65896ab6`, ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`. Its imports and all 1,091 actual build-input hashes passed; no application source overlay, business database, model or new Work was used for this final related regression.

## Model usage

- Original SelfRefine event `b2cce513-53da-4962-b161-1491e4730bc2`: **22,382** tokens. Retry event `8259d87d-7d0a-4fd4-b074-ea7bdbc55fc3`: **15,766** tokens. Only these 2 persisted Owner event counters are confirmed; sum **38,148**, not whole C3/Work usage. Reasoning/cache fields are not added again to total tokens.
- Both LOCAL_OBLIGATION_RECOVERED events prove local scope recovery. Neither proves complete Work or Provider transport recovery. Whole Work/C3 usage, model cost and HTTP retries remain UNKNOWN.
- One logical formation transport failure was reported by the root scoped observation; safe public canonical/trace fields do not independently identify a Model Runtime request. HTTP attempts/retries UNKNOWN. Final diagnostic/fail-stop fixtures do not demonstrate transport restored.

## Latest actual G0 blocker

The latest real G0 is **91f5dbc/image6f8**, not final d8ea/image51c0. Work `048189aa-0613-5307-b6f4-c430e7977f93`; Work Reality `332a3a38-8719-580c-a1a2-c331ae14a5ae`; ADMITTED binding `cc9ac6de-ac1c-4885-838b-2bb4234d5a9b`; run `f9f06c0a-b5fd-41c4-8e09-594cb91ea029`; PWU `395f75c3-6bbb-4028-8565-7a227f4adf04` PROPOSED; Attempt `f5026ead-1f51-4795-935a-85d4045547d4` CREATED; dispatch `106b2585-8205-4244-a736-89f10906e486` at 12:58:13.762658Z.

Preserved trace: orchestration → Work.advance_work → submit_queued_dispatch → Native ensure_submitted/_admission → validate_continuous_gates → validate_fulfillment_projection → **OBLIGATION_PROJECTION_UNRESOLVED**. SelfRefine `bc2921b0-bbe6-4f01-a99e-7d563ad972e4` at 12:58:14.384675Z is ESCALATED/NOT_RESUMED, automatic replay budget0 and qualified_safe_replayfalse; convergence `72f2b152-2c4b-4f69-be0c-505beca8ae8c` is NON_CONVERGING. This stop boundary is CONFIRMED_EDGE; exact unretained semantic/Provider cause is UNKNOWN.

At the 13:00:20 scoped read-only capture, queue/Native binding/Verification/Candidate queries returned 0 rows; the Work DB row was READY and driver showed Human attention. This is not ordinary Candidate approval pending, full Work PASS or proof of complete effect absence. Original Work24d9/image543 also remains unclosed. Final d8ea repairs diagnostic/upstream truthful-stop seams in deterministic fixtures; it did not execute a new real G0.

## Pending independent boundary

**Holdout SEALED, specific Human unseal authorization PENDING, 24 cases, zero executions.** No sealed specification was opened. This audit changed no source/tests/Runtime/history and performed no model/Work/ECS action.

The safe [freeze review](frozen-terminal-fix-review.md) independently binds final source/archive/controller/import/regression identity. Accounting readiness does not close C3, N1 or future Human Gates.
