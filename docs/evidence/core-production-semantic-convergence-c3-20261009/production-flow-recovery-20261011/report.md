# C3 production-flow recovery — 2026-10-11

**C3 PARTIAL — real Formation did not converge within the existing budget.**

This report records new engineering and qualification evidence. It does not change historical failures, Human decisions or the C3 completion definition.

## 1. Exact delivery identities

| Identity | Frozen value |
| --- | --- |
| Watt application commit | `881c2c303083be149594f9d79659a037853e302e` |
| Watt Tree | `d5ad35dc881717d3dab99cfeefc857d0bc78d704` |
| Guardian | `88f5ac35a6d48fb1aace24f94a2100708864e0be` |
| Guardian Tree | `e9e1d88889dff69979a79e4c2638d036a1dfcc6b` |
| ECF, unchanged | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| Application image | `sha256:5b396a0edbdf230cbe1a9b0099fa2b13b8dee2cae504b96f53af1c55e6f5d7f9` |
| Isolated database | `spg_c3_bindingg0g57_qualification_20261010` |
| Migration | `20261007_72` |

Exact Git archives were built into a new image. Actual imported package identities and running roles were observed, rather than inferred from requested configuration. [Frozen build](generation59/image/frozen-inputs.json), [build result](generation59/image/build.json), [actual imports](generation59/image/actual-imports.json), [runtime preparation](real-g0-g57/runtime-role-preparation.json).

Application revision is distinct from the generated Product baseline: `37c2ff226ea0381e34f06537ee5adfdce600016b`.

## 2. Proven system defects repaired

The existing consumer seams now distinguish method eligibility from actual fulfillment:

- Original `BOUND` file facts can propose the existing Git Diff method without being rewritten as `SCOPE`.
- Current content contributions and future Candidate Seal contributions can coexist; seal alone cannot discharge current content or authorize Human promotion.
- Source expressions remain immutable while frozen Task operands can enter independent Review. The former literal-expression/filename comparison no longer rejects legitimate method proposals before Review.
- Linked Clause evidence uses an exact observed Candidate witness when original Fact Scope is absent, with target, revision, tree and lineage checks reproduced independently by Guardian.
- Original Review Wire omitted optional defaults were mistaken for receipt drift. A shared, lossless default-restoration helper now covers rejected-review feedback and positive admission, preserving explicit verdict types and original raw identity.

Watt source commits: `ec4fc607`, `2189ea69`, `ae965a34`, `51e41c11`, `f07eef63`, `3cd4b6d5`, `881c2c30`. Guardian matched consumer changes end at `88f5ac35`. [Detailed consumer delta](engineering-delta.md), [Review identity root cause](review-defaults-root-cause.md).

Changes stay in existing Formation admission, semantic-fact/static consumers, Review feedback, Guardian evidence checks and their tests. No Alias, new Owner, Wire Schema, authority, model-call allowance or budget was added.

## 3. Qualification receipts and limits

| Qualification | Actual result | Applicable version |
| --- | --- | --- |
| Installed Watt focused regression | 39 PASS | Final Watt/image above |
| PostgreSQL / Owner joint regression | 3 PASS | Final Watt/image; actual Git, Verification, seal and independent Guardian with controlled fixtures |
| Historical G55 receipt replay | PASS, zero model calls; original failure preserved | Final Watt/image |
| Guardian installed regression | 178 PASS | Exact Guardian `88f5ac35` in generation57 image |
| Earlier grouped Watt regression | 906 PASS | Earlier `51e41c11`, not counted as final-image qualification |

[Final focused receipt](generation59/image/watt-continuation-receipt.json), [PostgreSQL receipt](generation59/owner-pg/receipt.json), [historical replay](generation59/historical55/replay.json).

The 178 Guardian tests were not rerun on generation59: [Owner reuse proof](generation59/image/guardian-qualified-owner-reuse.json) binds identical Guardian archive/source identities and the original result. Final-image PostgreSQL tests also exercise the matched independent Guardian chain. Fixture success is not a live Worker qualification.

Earlier setup/test failures remain available: generation57 PostgreSQL 1 PASS / 2 FAIL, development5416 Guardian setup failure, superseded builds and controller recovery. They are not included in successful final counts.

## 4. Latest real normal-entry G0

- Product: `de573669-c083-4c3c-bf38-97669d28bc73`.
- Work: `c1c0a944-4626-5ebb-9507-9dbd8aab4974`.
- Work Reality: `a2a5f56d-0add-5bd8-aa7b-f0b83d6dd4a2`.
- Inventory: `6908ea702c03019f2a47adb3c90e54b124cb16358d7a609e8b19ed34724fed9b`, 18 sources.
- Original normal-entry input SHA256: `c587f020c43275019b32c49a94ab8559587a01d339e1fe97b2c8e048a386258e`.
- Snapshot at `2026-10-11T06:13:35.716141Z`: SHA256 `fa51683da2110c206cca363fd25acc52e956461f2f3bdfb6fd644e80dd71f18f`.

Normal entry admitted a Work and invoked the real Provider twice. Candidate1 failed complete source coverage. The single existing feedback was bound to original Wire, Attempt, inventory and durable request/response receipts. Candidate2 restored source coverage but remained invalid. There was no independent Review, PWU, Native Worker, Git implementation artifact, Verification, sealed Candidate or Guardian result for this Work.

Terminal validation receipt: `2e569ed4-c71f-42a1-97dc-9f9f60106cff`, `OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN`.

Two remaining predicates were reproduced in the exact installed image:

| Original candidate | Failure | Existing-contract evidence |
| --- | --- | --- |
| Route15 / source11 / `CANDIDATE_SEAL` | Supporting references still empty | First feedback already supplied necessary alternative source sets `[0]` through `[5]`; second candidate did not supply one |
| Route21 / source17 / `ARTIFACT_CONTENT` | `OBLIGATION_CONTEXT_CANNOT_AUTHORIZE_EFFECT` | Source is `WORK_CONTEXT`; first feedback already identified the refusal. Existing context-retention route is structurally expressible |

Read-only counterfactual probes establish necessary binding eligibility with appropriate operands, not semantic equivalence, fulfillment or Candidate admission. Original candidate and history remain unchanged. No new model calls were made by these probes. [Exact classification and expressibility proof](real-g0-g57-classification/classification.json), [actual bounded feedback](real-g0-g57/bounded-recovery-observation.json).

Classification: **A — generated operands did not converge**, enforced by legitimate source/authority predicates. No new B-class inability to express these bindings was established. Independent semantic validity is **NOT_REVIEWED**, not PASS. Provider completed normally; this is not a capacity/transport failure.

The automatic stop and Work Admission `READY` refer to different lifecycle facts. `work_complete=false` and `human_attention_required=false`; no Human product-rewrite request was manufactured. Only the completed trial's passive GET observer was stopped after durable stop. Observer exit137 is not Provider failure or Work PASS. [Observer receipt](real-g0-g57/terminal-observer-stop.json).

## 5. Closure and next boundary

The proven consumer defects are repaired and protected by focused and joint regression. Existing Self-Refine executed one identity-bound feedback and a second candidate; it repaired coverage but did not repair all necessary operands.

**C3 is not CLOSED.** Real G0 still has no admitted Formation plan and has not qualified Worker → Verification → Candidate → applicable Guardian. Holdout remains sealed because its prerequisite is unmet. Human Integration, Acceptance and Delivery are not authorized by this report.

There is no evidenced additional platform bug justifying another patch or unchanged new Work. Further progress requires an explicit bounded change to the Formation convergence strategy, justified by these retained failures; increasing attempts/budgets, forcing candidate operands or weakening proof is not performed. This is the current production-progress decision boundary, not a request to change product intent. C4/N1/N3 are not started.

## 6. Observed resource consumption

| Scope | Actual tokens | Provider elapsed seconds |
| --- | ---: | ---: |
| G54 Formation1–2 | 122917 | 27.949593171 |
| G55 Formation1–2 + Review | 184380 | 43.003955171 |
| Latest G57 Formation1–2 | 88744 | 19.322629276 |
| Observed subtotal | 396041 | 90.276177618 |

Latest call1: 35479 input + 2506 output = 37985; call2: 48154 input + 2605 output = 50759. Reasoning tokens0, transport retries0, both completed. Final build226.277895296 seconds; final PostgreSQL200.824183295 seconds. These are measured scopes, not whole-task cost. WIC/design usage, full compute/CPU, money, whole-Work elapsed cost: **UNKNOWN**.

## 7. Recovery locations and protected reality

Public safe receipts/manifests are in this C3 Git folder, to be pushed separately from the frozen application commit. Private originals are retained on ECS, outside Git:

- Final build/test inputs: `/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation59-qualified-20261010`.
- Latest runtime/database/volume identities, safe evidence and private original Owner export: `/data/watt/c3-semantic-convergence-20261009/binding-g0-generation57-qualification-20261010`.
- Exact controller sources/logs: `/data/watt/c3-semantic-convergence-20261009/binding-g0-generation57-final-source-controls-20261010`.
- Earlier failed G54/G55 directories remain retained under the same C3 root. Manifests give full snapshot locations and SHA256.

Canonical main, production service/configuration, historical Works/Candidates/decisions and Quality Ledger were not modified. [Final read-only boundary check](real-g0-g57/final-boundary-observation.json) records unchanged canonical main and production checkout identities, running isolated roles and retained original snapshot hashes. Full Human conversations, private Provider payloads and credentials are not published. Moving computers can recover public evidence from Git and private originals from these persistent ECS paths.
