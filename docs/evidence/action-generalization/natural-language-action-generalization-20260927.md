# Natural-language action generalization qualification

The original Human failure remains unchanged. Implementation now carries a grounded canonical WIC action through existing authority, Repository Asset admission, Git effects and observed Reality. No Chinese branch phrase aliases were added. Qualification was stopped at the Human’s explicit request to shut down and clear the test runtime before architectural refactoring. Unfinished runs remain INTERRUPTED_BY_HUMAN; the completion invariants are not asserted as PASS.

## Preserved failure and first divergence

Original failed Interaction `44c3a727-4102-4dcc-9d15-122a0409fd0a`, Turn `7c19cb46-dd5d-470a-a521-92426a2b0743`, Human record `281e9762-8f54-4cdb-8395-f0582695af30` contains exactly `切个新分支：feat_feedback`. Successful comparator is Interaction `50ae2542-a948-4342-8125-1fb2e7835a7b`, Turn `a8e40682-89d0-45f9-8fe9-ebe7a6d65b37`, and successful Human record is `05786092-5e22-472b-8bc0-5d776ce56526`.

[Complete internal comparison](human-regression/comparison.json) retains raw Human records, assessments, semantic extractions/facts, meanings/confidence, mode, Response Contract, intakes and Git/connector evidence. [Preservation hashes](human-regression/preservation-manifest.json) describe the unchanged captured artifacts.

The earliest model representation difference is that A includes both REFERENCE and STATE_CHANGE extractions; B includes only REFERENCE and uses `repository.branch_create_request` plus `branch.name`. **Both preserve the explicit creation request and its literal target.** The first causal execution divergence is `RepositoryAssetService.execute_interaction_actions`: it independently reparses Human prose using `repository_actions`, producing LOCAL_BRANCH for A and no action for B. B therefore never reaches action admission, connector selection or Git. Its later answer truthfully observes `main`.

Historical typed canonical action/confidence/admission fields were not recorded. Missing historical data is marked NOT_RECORDED or NOT_REACHED; diagnostic replay of the unchanged command witness is not described as an original execution receipt.

## Generic correction

The WIC semantic contract returns `InteractionActionCandidate`: canonical operation, speech act, latest Human record id, exact source substring, literal branch/source arguments and confidence. Production execution consumes that structured meaning. Current actor ownership and resource ownership remain independently checked at admission and again before effect; model confidence, credentials and connector availability do not grant authority.

`CREATE_AND_SWITCH_BRANCH` projects to the existing `CREATE_BRANCH` Asset operation and `git.branch.create` connector. Git observes the resulting branch, revision and tree before response. The same owner handles acquisition, inspection and branch-status queries. An empty interpreted action set cannot fall back to old phrase parsing. Null denotes only an unrecorded legacy/deterministic interpretation. Active Work model ports also use semantic binding; the legacy exact-command shortcut is retained only for older fixture ports without a semantic capability.

Responses to repository operations stream the observed owner result and persist the same result. An omitted explicit ACTION_REQUEST candidate triggers `EXPLICIT_ACTION_LOST_BEFORE_EXECUTION` and one bounded structured repair against the same Human basis. Exhaustion preserves the Human record and truthfully fails without an execution promise. Missing executable conditions produce an explicit blocker, with no background execution claim. Preview/delivery candidates remain subject to their existing candidate, acceptance and delivery owners; semantic recognition never supplies their missing authority.

Qualification found two adjacent faults. Invalid fact/extraction references now enter the same bounded semantic repair before assessment admission. Structured expression repair now retains a complete string already observed by the governed delta gate; the model cannot rewrite it during schema repair. Existing refinement event/observation owners record recovery scope and retain `work_converged=false` for local action/expression recovery.

## Qualification inputs and runtime

[Semantic equivalence corpus](../../../benchmarks/golden/interaction-action-equivalence-v1.json) contains eight branch-positive templates, seven branch-negative near-neighbors and seven neighboring operation classes with two positive/two negative examples each. This is a test corpus, not an implementation alias table. Expanded GC-LC-02 checks canonical action, literal target, actual branch and absence of branch effects in negatives, using different branch names per trial.

The real `/app` browser Interaction is `cd28d7fe-7731-4cb6-a41d-80a79b50ab12`. Exact `切个新分支：feat_feedback` created/switched the real local branch; `分支创建好了吗` answered from its Git observation. Two further expressions created `feat_browser_from_current` and `feat_browser_create_switch`. Discussion and existence-query negatives retained the last branch/intake. No tester Git command, manual branch setup, source modification, push or production Work was used. [Browser DOM evidence](browser-three-positive-two-negative-dom.txt) and [public/internal receipts](runtime-evidence/browser-interaction-index.json) retain the journey.

Neighbor semantic audit: [28 results](neighbor-semantic-audit-20260927.json). These qualify model interpretation and speech-act boundaries; they do not pretend semantic-only calls performed GitHub retrieval, Preview creation, delivery or Web Search. Existing owner boundaries are qualified separately by the real runtime owner audit, backend regression and Release Evaluation. Preview/delivery missing-candidate/acceptance boundaries remain truthful blockers.

## Verification and outstanding external gate

This independent closure task is stopped and superseded by the Intent Realization Kernel refactor. [INTERMEDIATE CHECKPOINT handoff](INTERMEDIATE-CHECKPOINT-HANDOFF.md) records current source identity, completed receipts, interrupted runs and known semantic splits. No completion invariants are asserted as PASS. Failed and incomplete runs remain preserved and are not folded into unique passing counts.

All real Web Search qualifications remain **BLOCKED_EXTERNAL**, including explicit/combined/model-initiated Web retrieval, live provenance/refinement/convergence and GC-EX-12. The [independent rerun entry and evidence requirements](../../operations/web-search-live-qualification.md) remain explicit. Missing Web credentials do not stop code-owned implementation, Golden or regression work. Direct Fetch and deterministic adapters do not qualify real Web Search.

## Human-requested runtime shutdown

On 2026-09-27 the Human explicitly ended the running test batch and requested removal of test containers and images before architectural refactoring. All 13 containers, all tagged/dangling images, four project networks and unused build cache were removed. Test ports 8078, 8079 and 55438 have no listeners. All 294 data volumes and frozen FSI evidence were preserved. No automatic restart or qualification continuation is scheduled by this task.

The final source root unit run completed with 948 passed and one external-contract skip. The integration partitions, Golden trial 5, final neighboring-owner audit and final Release Evaluation were interrupted; their partial results must not be represented as completed qualification. Detailed shutdown inventory and verification are retained locally in `.spg/action-generalization/shutdown/result.json`.
