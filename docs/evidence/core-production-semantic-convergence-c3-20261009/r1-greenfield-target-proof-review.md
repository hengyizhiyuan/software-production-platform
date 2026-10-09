# C3 Supplement R1 — Governed New-Target Scope Proof

Reviewed UTC: 2026-10-09T14:50:28.331299+00:00.

## Authority and historical boundary

This implements the Human-authorized / Architecture Lead-approved bounded R1 scope correction on the existing C3 branch. Source starting point: evidence HEAD `66684461791f287d56c8c6eb86dc3b0af4a941fa`, application baseline `d8ea0642f0c360794e69c366e8f15fa369eeed0b`. The Program invariant remains the [fixed Accepted ADR](https://github.com/hengyizhiyuan/software-production-system/blob/1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1/docs/04-decisions/ADR-0002-STOCHASTIC-NATIVE-ENGINEERING.md); existing project scope responsibilities are defined by [Repository-Aware Code Change Proposal Lite](../../architecture/repository-aware-code-change-proposal-lite.md).

Retained Work408 input: local `C:/Users/yuchunbo/Downloads/watt-work-408e408a-fab8-5a34-b101-b922043cb6fd-diagnostic.zip`, SHA256 `1d62a35bfe0fce16581cbff6058d59e1ba3a5f7d2392c537a8beb2d192310e61`, Work `408e408a-fab8-5a34-b101-b922043cb6fd`. The ZIP evidence manifest records `source_revision=null` and `source_tree=null`; the failing execution's exact code/image identity remains **UNKNOWN**. Repository Source revision `7a43f86903cc4bba1cbbe8ea58e6a9f794fd31d4` and tree `f8dd561e5dbd3dd615b09bd78e7f1ae2b5d388ea` come from the separately retained read-only Repository Source inspection. They identify the inspected repository baseline, not the ZIP's runtime source identity. No hidden reasoning or full raw transcript was copied into this report.

The separately retained export qualification at admin commit `5de657f3cb65780adf50f6557b54171a6c3cfae5` proves bounded read-only diagnostic export for a DESIGN / WAITING_HUMAN Work, not a root-cause review or production PASS. The prior review distinguished incomplete proposed behavior / `INTENT_COMPLETENESS_MISMATCH` from a structural new-target proof mismatch. Their individual historical causal contributions, especially the second `ValueError`, remain **UNKNOWN**. R1 does not diagnose a Provider transport failure, assert Work408 repaired, alter that Work or replay it.

## Confirmed contract gap (E3 exact code)

The prior `RepositoryTargetNecessityProof` required a source path and nonempty exact repository quote for every scope target. The independent scope-validator instruction further required a new file to have an existing implementation witness. The Proposal consumer rejected a necessity proof unless its source path existed in the exact baseline tree. A legal new software surface on a baseline without implementation could therefore not express its necessity through this proof contract, even when its governed user behavior was clear.

This is a confirmed representation limitation. It does not establish that every observed DESIGN failure has this cause, or that new target absence alone establishes necessity.

## Minimal implementation / unchanged authority

Only these existing modules and one new test module are changed:

- `src/spg/domain/refinement.py`: the existing necessity proof gains opt-in `evidence_kind=NEW_TARGET`, exact source revision/tree and an evidence-shape guard. `EXISTING_IMPLEMENTATION` is the compatible default and still requires its actual source path / quote. Shared deterministic proof checks validate exact candidate membership, Human quote provenance, version/tree and original-tree path compatibility.
- `src/spg/providers/deepseek_semantic.py`: only the Scope Validation seam. The existing model judges necessity and complete governed behavior using original outcome/requests/constraints. A new target needs no fabricated existing-source quote. Its exact source revision/tree, actual target absence and path identity are independently checked. Every new target must be used by a `REQUIRED_TARGET` coverage row, and plans with an actually new target cover the original canonical outcome, requests and constraints irrespective of the model-selected proof tag. Missing coverage remains a failure through the existing two-attempt / one-feedback bound.
- `src/spg/providers/repository_change_proposal.py`: the existing read-only consumer independently rechecks the complete Git tree and exact proof basis. It preserves required / conditional scope, forbidden areas, proposal lineage and existing-source witnesses. NUL-delimited Git tree inspection preserves Unicode paths and prevents escaped display text being mistaken for absence. Existing files/directories that conflict with a proposed new file reject `NEW_TARGET`.
- `tests/test_c3_greenfield_target_proof.py`: independent controlled regressions.

The model's necessity judgment is a derived scope candidate, not Engineering Truth, Verification PASS, Human authorization or an executed effect. Deterministic checks establish identity, provenance, path compatibility, contract and bounded coverage; they do not replace semantic necessity reasoning. No filename, subject alias, business keyword, case whitelist or broad Greenfield pass flag is added. Future Human/Delivery and current prohibited effects retain their existing lifecycle owners. `semantic_steps.py`, fulfillment/provider formation, production/main, ECS, original Work and Holdout are outside R1 ownership.

## Controlled qualification plan and limits

Static AST and scoped `git diff --check` passed for R1. The root's [development-1 Linux receipt](continuation-20261010/development-1/result.log) records 73 PASS / 2 FAIL across 75 selected cases; R1 contributed 20 PASS / 2 FAIL across its 22 cases. Both failures were controlled test-layer defects: the positive TaskContract fixture omitted its existing exact ECF source basis, and the malformed-proof test expected only the later consumer error even though the normal request schema correctly rejected it earlier. Only the test inputs/assertions were repaired; the positive fixture now supplies its exact observed SourceBaseline/revision references, and the negative checks both normal wire rejection and independent copied-request rejection. The two targeted retest nodes are **PENDING execution**. This development receipt is neither installed-image qualification nor real Work success; the root owns the final installed-image regression.

The new module contains 22 controlled cases: English/Chinese goals and unrelated new filenames; no prior code quote; unchanged Git HEAD/status/refs; wrong revision/tree; existing or conflicting path; outside candidate; false Human provenance; duplicate proof; forbidden path; missing identity and independent consumer shape revalidation; fabricated quote; unsafe path; strict existing-source quote rejection; complete Scope → original production-plan consumer → Proposal → CodeChangeContract → TaskContract; bounded truthful stop for incomplete behavior or all-downstream coverage; complete-tree check despite sampled-context omission; existing Unicode path protection; existing-source witnesses cannot bypass complete behavior coverage for an actually new target.

The positive chain uses a declared controlled semantic response and actual local Git objects/pure application contracts. It creates no persisted Work, PWU, Runtime, Human decision or Provider call. It is not a real G0/end-to-end production or Runtime Conformance Qualification. Final exact commit/image and actual execution receipts must be reported by the root after its freeze. C3 and N1 remain PARTIAL until their original acceptance boundaries are genuinely met.


## Final exact continuation qualification

Application source `e8e04b296b31d776a13dda728fa19469681cbaab`, tree `a349e40ea0c328ad55574dc668e884a137a19944`, new image `sha256:4d3c64b1e3543a3574cd69b435d6f703fad6edc23b9db7d54d799dc1a652bf6e`: [321 installed-image tests](continuation-20261010/continuation-final-image/watt-continuation-receipt.json) and [5 isolated PostgreSQL tests](continuation-20261010/semantic-owner-pg/receipt.json) PASS. No source/test overlay or live model calls. New fixture DB `spg_c3_continuation_fixture`, migration `20261007_72`, is stopped. These are bounded engineering qualifications, not real G0 or historical Work408 repair.
