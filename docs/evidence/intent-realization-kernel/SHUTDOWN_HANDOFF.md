# Watt IRK campaign shutdown and reality handoff

## A. Shutdown decision

The Human terminated the roughly 80-hour IRK / Behavioral Convergence campaign on 2026-09-30. No Watt behavior repair, new source generation, Golden/Lifecycle/Holdout submission, or follow-up campaign began after that instruction. The already running GC-IP-02/trial-22 was allowed to finish its fifth native step and reached an automatic Preview. Its browser business oracle was deliberately not run. The already performed GC-IP-04 browser edit was reconciled read-only. Human Acceptance is **PENDING** throughout.

## B. Exact current source identity

| Field | Observed identity |
|---|---|
| Branch | `codex/irk-behavioral-convergence` |
| Shutdown source checkpoint | `b119c29e1068e6e2c1ab1ba8ca3a73b7d7993c4d` |
| Source checkpoint tree | `1a9e82de0c7e3517d1d05921a44d7c84c0bfb7a5` |
| Production fingerprint | `cc44098163e2676ec0c6b04b9d3126fb0719ac635ef5335e1f2b7ba8f4ba8c01` |
| Migration head | `20260928_62` |
| QA image | `watt-irk-convergence-runtime:qa` / `:source39`, both `sha256:723dfb3aa62c649e6adca764324ecfc58a9cf4b1a1df3f2ef6b5f6e16bc7fe47` |
| Runtime/source match | All 293 normative `src`, `migrations`, and `docker` files matched the current worktree fingerprint before shutdown. |
| QA database | `watt-irk-convergence-qa_native-postgres-data` Docker volume, preserved; service stopped. |
| Push state | Local only. `origin/main` was 0 commits ahead and 111 behind the source checkpoint; no branch of this name was present on origin at last check. |

The checkpoint commit preserves the six edits already present when shutdown was requested: two production files (`assets.py`, `intent_realization.py`), three tests, and one Golden oracle script. The earlier dirty diff and each normative file hash are preserved in `shutdown/pre-shutdown-inventory.json` inside the private evidence archive. The oracle script correction changed the benchmark, not the production fingerprint. The checkpoint is **PARTIALLY QUALIFIED**, not a final behavioral-convergence freeze. See [shutdown-source-identity.json](shutdown-source-identity.json).

## C. Implemented architecture reality

The current source contains the governed semantic path: Human Turn and provenance → clause-level semantic candidate → IRK validation and typed Action / Production Intent → durable obligation ledger → existing WIC, repository Action, Work, Connector and production owners → observed effect reconciliation → grounded response. It includes per-effect authorization, parameter binding, Turn/Action/Work refinement and convergence mechanisms, and a failed-Turn semantic envelope. The architecture is described in `docs/architecture/intent-realization-kernel` and the prior [implementation report](REPORT.md). Existence of a mechanism is not universal correctness or completed qualification.

## D. Current-source formal verification

The exact production fingerprint above was tested before shutdown. Backend unit suite exited 0 (the log includes skips). Fresh PostgreSQL/Linux integration completed **788/788**, zero failure/error/skip. Frontend Node tests passed **78/78**; prototype tests **21/21** and Vite build passed. Migration upgrade to `20260928_62`, downgrade/reupgrade, and `alembic check` passed. Release Evaluation passed **56/56** selected cases. Visible semantic corpus passed **41/41**, with six bounded in-run compiler recoveries; that corpus is compiler-level evidence. Logs and JSON receipts are in the evidence archive. Four earlier integration attempts were stopped or failed because of harness mounts/user/socket/database-name setup; their original logs remain and are not counted as PASS.

## E. Current-source real-runtime qualification matrix

[shutdown-current-source-matrix.json](shutdown-current-source-matrix.json) lists each of 47 finite requirement groups with exactly one status. Its unit is a requirement group, not an individual attempt:

| Status | Count |
|---|---:|
| `PASS_CURRENT_SOURCE` | 18 |
| `FAIL_CURRENT_SOURCE` | 0 |
| `PARTIAL_CURRENT_SOURCE` | 9 |
| `NOT_RUN_CURRENT_SOURCE` | 1 |
| `BLOCKED_EXTERNAL` | 2 |
| `HISTORICAL_PASS_ONLY` | 17 |
| `HISTORICAL_FAIL_ONLY` | 0 |

Tier0 current-source business PASS exists for EX-02, IP-01, IP-03, and IP-04. FSI-HD-01 has one independent current-source browser/Preview PASS but EX-01's three-trial Tier0 minimum is incomplete. IP-02 reached Preview but no browser/API/SQLite oracle after shutdown, so it is PARTIAL. EX-11's actual missing-secret boundary was observed without execution or Preview; EX-12's available GitHub research passed while real Web Search remained blocked by a withheld credential. Current physical Lifecycle PASS exists for LC-01/02/03/04 (three trials each), LC-09 and LC-13. Seven other Lifecycle cases have current formal neighbor coverage but no current physical Golden replay; LC-08 and LC-15 have historical physical evidence only. No fresh post-freeze unseen Holdout was generated.

The matrix also preserves **seven diagnostic attempt findings** separately: EX-02/trial-21 shared-Product fixture contamination (PARTIAL), EX-11/trial-20's original exact-word oracle FAIL, LC-09/trial-21's volatile queue-timestamp oracle FAIL, and integration attempts 1–4 (one stopped, three harness FAIL). Later semantic or final-suite PASS receipts do not rewrite those originals. No current-source unauthorized side effect is established by these retained attempts; universal zero false effects is unproven because the finite matrix and unseen Holdout were stopped.

## F. Historical evidence that remains relevant

The original fourth-freeze [report](REPORT.md), [Tier0 matrix](golden-matrix-final-r290.json), [Lifecycle matrix](lifecycle-final-matrix-r247.json), and [root-cause map](convergence-root-cause-map.md) remain historical. They contain actual failures: create-only branch requests caused an unrequested switch; Work history/status answers could contradict Reality; worker-loss refinement could remain FAILED after physical resume; and prior generated Candidates lacked About discoverability or a coherent persistence/API/form mapping. These are not promoted to current-source PASS or current-source FAIL without current evidence. Source38/39 physical regressions specifically exercised Work-history grounding and source-bound read-only branch inspection; all old failed receipts remain immutable.

## G. Watt Platform defects remaining

**No reproducible current-source Watt Platform defect is established by the executed shutdown matrix.** This is an evidence statement, not a platform clearance. Fresh Holdout, worker-loss fault injection, invalid native-result injection, complete Tier0 and Lifecycle physical slots, and a full 38-invariant re-audit remain unqualified on this source. Historical confirmed platform defects and their repairs are recorded in the root-cause map. The source39 changes specifically normalized read-only Work-history questions to persisted Reality and prevented same-source inspection from reacquiring a repository and resetting the observed branch; current LC-09 and LC-02 physical receipts passed. The incomplete matrix cannot prove that related failure classes are absent elsewhere.

The [failure-attribution table](shutdown-failure-attribution.json) assigns each retained finding to Platform, Artifact, Harness, External or qualification debt without promoting earlier-source evidence.

## H. Artifact defects and normal production-refinement findings

Historical Candidate defects include an About page without a discoverable navigation link and customer notes whose migration, API and form field names disagreed. A source39 FSI Candidate placed the requested `/about` link, while a direct GET of `/about` returned 404; the narrow FSI link oracle passed, but the served target is a known Artifact quality finding. IP-02's Preview has no post-shutdown business oracle, so its generated form quality is unknown. These findings belong first to Candidate → Verification → Guardian → Watt Self-Refine, with Human Acceptance still pending. **Artifact failure does not imply Platform failure.** Escalate to Watt Platform only when an invariant is violated, required detection/feedback/recovery fails, a recurring systemic pattern is demonstrated, or authority, Reality, lifecycle or completion semantics break.

## I. Qualification Harness defects

Known harness defects are the shared Product identity in EX-02/trial-21, EX-11's exact wording placement check, LC-09's comparison of volatile `capacity_observed_at`, four source39 integration setup attempts, earlier Docker network exhaustion, and this shutdown's Preview UUID transcription error. The original receipts remain, with separate corrections. The current QA image and worktree had matching normative source; source39 final integration used a fresh database, correct user/mount/socket/sibling repositories, and 788 tests passed. Future qualification needs one versioned, canonical preflight/test entry that verifies image, source, DB migration, mounts, UID, Docker socket, fixture namespace and bounded runtime cleanup before running a matrix.

## J. External blockers

Real Web Search requires `SPG_WEB_SEARCH_API_KEY`; it was withheld. EX-11 identified the real externally issued `STRIPE_SECRET_KEY` startup prerequisite, stopped at Human decision, and did not fabricate a secret or Preview. These are independently scoped external dependencies. Human Acceptance is PENDING, not an automated blocker or a PASS.

## K. NOT_RUN and deferred qualification debt

No post-shutdown trial was started. The current-source Tier0 minimum trial counts, seven physical Lifecycle neighbor cases plus historical-only LC-08/15, the eight-journey complete business suite, fresh unseen compiler/live-owner Holdout, worker-loss and invalid-result injections, and the 38-invariant final audit were not completed as a finite all-PASS campaign. The matrix gives each group's exact state; historical PASS cannot fill a current-source slot. This debt no longer blocks shutdown.

## L. Watt Self-Refine evidence

Codex source repair means code changed between trials. The source37→38 Work-history change and source38→39 repository-inspection change are **CODEX_PLATFORM_REPAIR**. By contrast, source39 FSI trial5 recorded same-source `SEMANTIC_BINDING_FAILURE` and `CANDIDATE_INCONSISTENT` recoveries within its governed Work, and source39 IP-03 trial23 recorded recovered verification/runtime-tool attempts and a scope recovery while completing one Candidate. IP-03 also has one failed runtime-process refinement event; do not count every event as recovered. These are **WATT_SELF_REFINE** receipts at the same source/request/authority, not Codex reruns. Visible corpus compiler recoveries are compiler-level evidence only.

## M. Resource and cost observations

`source39` was the last named source generation; an exact count of distinct candidate builds was not audited. A deduplicated scan of 238 retained `latest.json` records found 106 Works with 28,117,745 observed model tokens (23,994,418 input; 4,123,327 output) and 1,346 recorded inference submissions. This is a **lower bound on retained observations**, not a full campaign bill or an exact DeepSeek request count. Provider currency spend was UNREPORTED in those Work receipts. Docker later reported 20.79 GB images, 20.42 GB volumes, and 33.9 GB shared build cache, 22.56 GB marked reclaimable. Shared cache and all 307 volumes were retained to avoid broad deletion.

## N. Infrastructure cleanup

[shutdown-cleanup.json](shutdown-cleanup.json) names the exact dedicated QA, idle test, fixture, native runtime, Preview and image resources retired. Final Docker state had zero running containers, 48 exited containers, 10 networks, and 307 preserved volumes. The current `qa/source39` image remained. The source27 runtime tag remained because an exited failed-attempt container references it; removal was not forced. C: free space measured 6,759,751,680 bytes before and 6,478,495,744 bytes after bounded cleanup. Host free space **decreased**, so no disk-space recovery is claimed; Docker Desktop's shared storage was not compacted and broad builder/volume prune was not run. Current QA and Preview endpoints are unavailable after shutdown.

## O. Repository and runtime final state

The pre-existing six-file diff was committed as the labelled partial-qualification shutdown checkpoint. This report, source identity, cleanup and matrix are the handoff artifacts. Raw `.spg` receipts are ignored by Git and preserved in one private, hashed shutdown archive at `D:\hy\software-production-platform\.spg\irk-shutdown\irk-source39-shutdown-2026-09-30.zip`; its SHA-256 is in the adjacent `.sha256` sidecar. No credential or private environment file is included. The branch was not pushed. Working-tree cleanliness must be checked after the handoff commit; the source fingerprint is unchanged by evidence/doc commits.

## P. Backlog by responsibility owner

| Owner | Deferred work |
|---|---|
| Watt Platform | Investigate only a newly demonstrated current-source invariant failure; complete worker-loss/result-fencing and remaining effect/response audits in a future campaign. |
| Watt + Guardian production loop | Detect and refine Artifact quality findings such as the served `/about` target, joined field mappings and missing UI operations through Candidate → Verification → Guardian feedback → Watt Self-Refine. |
| Qualification Infrastructure | Canonical versioned preflight and test entry; isolated readonly fixture namespace; semantic/volatile-field-aware oracles; bounded Preview/test cleanup; exact image/source/DB identity receipt. |
| External | Supply real Web Search and Stripe credentials through governed mechanisms only if a later task authorizes those integrations. |
| Continuous Qualification | Explicitly schedule new current-source Tier0/Lifecycle/Holdout/business/fault matrices in a later campaign; retain this campaign's NOT_RUN states. |

## Q. Safe starting baseline for the next campaign

Use the local `b119c29` source checkpoint, exact fingerprint and retained `qa/source39` image digest, migration head `20260928_62`, current-source matrix, failure attribution and private archive together. Restore the preserved DB/workspace volumes only with a new, explicit test profile and preflight. The stopped QA service and historical Previews are not live dependencies. The evidence/docs handoff commit does not alter the 293-file production identity.

## R. Claims excluded

Do not claim all-PASS IRK closure, universal language understanding, zero false effects across unrun cases, production readiness, completed Human Acceptance, successful Web/Stripe integration, a fresh unseen Holdout, a clean historical record without failures, or recovered C: disk space. This campaign is stopped by Human decision.
