# INTERMEDIATE CHECKPOINT — NOT A CLOSURE CLAIM

**STOPPED / SUPERSEDED BY INTENT REALIZATION KERNEL REFACTOR.** No further product fixes, phrase expansion or generalization trials are authorized by this checkpoint. All test services, containers and images were removed at the Human’s preceding request; no regression command remains running.

## Commit / tree

- Code commit: `d56a5cefff51d00241169b61513d558c3629bc35`.
- Code tree: `e0da39acddf774f4cf44b131a237dc724dd1a450`.
- Branch: `feature/production-environment-foundation`.
- Intermediate checkpoint: the commit adding this handoff and evidence archive, labeled `INTERMEDIATE CHECKPOINT`; it includes the five existing implementation commits starting at `26c8d8f`. It is an evidence/implementation snapshot, not release approval or closure. Its exact commit/tree is reported with the handoff.

## Established findings

The model understood the original `切个新分支：feat_feedback` request and literal branch target. The first causal loss occurred when downstream `repository_actions` independently reparsed the prose through fixed phrases. Both original failed Interaction `44c3a727-4102-4dcc-9d15-122a0409fd0a` and successful comparator `50ae2542-a948-4342-8125-1fb2e7835a7b` remain unchanged; original-field preservation was rechecked.

An independent Search witness shows the same split: the model understood `不要搜索 GitHub，我只是聊聊任务队列的概念`, recorded the withdrawal, and emitted an empty action set, but the legacy search-keyword route still retrieved GitHub evidence. The original violation and subsequent successful local suppression retest are both preserved. These findings justify the architecture refactor; they do not establish that all semantic splits are resolved.

## Useful generic changes retained

- Grounded canonical WIC actions carry operation, speech act, current Human provenance, literal arguments and confidence through assessment, persistence and API. Empty interpreted action sets are distinct from unrecorded legacy interpretations.
- Repository owners consume those bindings, retain authority/resource checks, execute existing Git operations, and answer from observed branch/revision/tree.
- Missing explicit action bindings and invalid semantic references enter bounded same-basis repair; local recovery retains `EXPLICIT_ACTION_LOST_BEFORE_EXECUTION` and does not claim Work convergence.
- Repository responses stream the observed owner result; structural expression repair preserves already observed wording. Missing Preview/delivery conditions produce truthful blockers.
- Model-backed active Work bypasses the old exact-branch shortcut. Recorded semantic non-actions stop reentry into legacy Search routing. These are useful local corrections, not an Intent Realization Kernel.
- Expanded semantic corpus/GC-LC-02, persistence migrations 59/60 and three Release Evaluation cases remain available. No new phrase aliases were added to production action recognition.

## Changed production files (relative to pre-task `8ca6ded`)

- `migrations/versions/20260927_59_interaction_actions.py`
- `migrations/versions/20260927_60_action_interpretation_presence.py`
- `src/spg/api/dto.py`
- `src/spg/application/assets.py`
- `src/spg/application/external_research.py`
- `src/spg/application/interaction.py`
- `src/spg/application/response_contract_expression.py`
- `src/spg/domain/interaction.py`
- `src/spg/domain/interaction_actions.py`
- `src/spg/evaluation/release_gate.py`
- `src/spg/infrastructure/persistence/interaction_store.py`
- `src/spg/infrastructure/persistence/product_schema.py`
- `src/spg/providers/deepseek_interaction.py`
- `src/spg/providers/interaction_contract.py`

Benchmark/corpus and regression changes are preserved in the same implementation history; the complete source fingerprint is in [source-manifest.json](source-manifest.json).

## Passed receipts

- Final code root unit regression: **948 passed, 1 skipped**, 949 cases; the skip requires an unavailable sibling ECF Preview contract. [Final XML](verification/backend-units-search-final.xml).
- Frontend: **77 official tests passed**; prototype journey **21 tests and build passed**. [Official log](verification/frontend-owner.log), [prototype log](verification/frontend.log).
- Schema: head `20260927_60`; Alembic check reports no new upgrade operations. [Schema receipt](verification/schema-check.log).
- Earlier full Release Evaluation: **56 cases / 148 selected checks, PASS**, persisted revision `3640b1b`. Its invocation crossed intermediate source revisions; it is **not** a completed final-`d56a5ce` evaluation. [Receipt](verification/release-evaluation.json).
- GC-LC-02 trials **3 and 4 passed all 17 Turns** each. Real browser Interaction `cd28d7fe-7731-4cb6-a41d-80a79b50ab12` passed the exact original branch request, completion query, two further positives and two negatives, without tester Git commands. [Browser evidence](browser-three-positive-two-negative-dom.txt), [trial receipts](golden/GC-LC-02).
- Neighbor semantic-only audit: **28/28 passed**. It does not qualify external effects. The final owner audit completed acquisition, two inspections, GitHub Search and its withdrawal negative before interruption. [Semantic audit](semantic-audit.json), [final owner results](owner-neighbors-final/results.json).

## Failures / unfinished qualification

- GC-LC-02 trial 1 failed on an invalid semantic extraction reference; trial 2 failed on streamed-versus-repaired wording. Subsequent bounded-repair/prefix-preservation corrections are retained. Failed evidence is not overwritten or counted as a successful trial.
- Golden trial 5, final owner audit, final Release Evaluation and full integration regression were **INTERRUPTED_BY_HUMAN**. The three disjoint integration partitions recorded **145 + 23 + 91 = 259 passed cases** before stopping; their source was `767dcff`, with later deltas explicitly recorded. These partial XML files do not establish full integration PASS. Shutdown-related database errors/KeyboardInterrupt remain in raw logs.
- Earlier failing and interrupted test receipts remain archived, including old migration-head assertions and the corrected failure-classifier NameError. The later complete unit run passes; no further case fixing is planned here.
- The second browser journey on final source was incomplete when services were stopped; no complete final-source browser journey is claimed. Uncaptured durable runtime rows remain in retained data volumes.
- `journey.json` in expanded Golden trials retains the runner’s older declared input metadata. Actual submitted Human inputs are authoritative in `semantic-equivalence-inputs.json`, `submission-*.json` and raw projections; historical receipts were not rewritten.
- All real Web Search live qualification, model-initiated Web retrieval and GC-EX-12 remain **BLOCKED_EXTERNAL**. No credential was provided. [Separate rerun entry/evidence requirements](../../operations/web-search-live-qualification.md), [blocked receipts](deferred-web). Do not restart services or run these trials as part of this stopped task.

## Phrase / keyword paths discovered

- `src/spg/domain/repository_actions.py::repository_actions`: regex/phrase admission, branch extraction and query/negation heuristics; still present for unrecorded legacy interpretations. `RepositoryAssetService._bound_interaction_actions` retains that legacy fallback.
- `src/spg/application/interaction.py`: `exact_branch_creation_command` fallback for non-semantic fixture/legacy ports; `_work_reality_status_question` fast path and other prose-derived lifecycle decisions remain.
- `src/spg/application/external_research.py`: `explicit_search_intents`, `potential_external_research`, URL/Fetch regexes and `_fallback_query`; the new typed gate stops the observed override, but legacy routes remain.
- `src/spg/domain/response_contract.py::production_intent_evidence`: phrase-based production/source extraction is consumed by interaction, research, repository and response decisions.

This is an inventory of inspected paths, not a claim that every caller or implicit-information-gap behavior has been audited. Semantic interpretation, authority, realization and effect must be addressed together by the successor Kernel task.

## Evidence / retained runtime data

All archived evidence is under `docs/evidence/action-generalization/`; original working receipts remain under `.spg/action-generalization/`. [SHA256 evidence manifest](checkpoint-evidence-manifest.json) covers preserved raw artifacts. [Original comparison](human-regression/comparison.json), [preservation recheck](original-preservation-recheck.json), [source boundaries](verification/integration-source-boundaries.json), and [shutdown verification](shutdown/result.json) retain their distinct provenance.

The shutdown removed 13 containers, tagged/dangling images, project networks and build cache. All **294 data volumes**, code and frozen FSI evidence were retained; ports 8078, 8079 and 55438 have no listeners. The runtime image identity is historical ([identity receipt](runtime-final-identity.json)); that image was deliberately removed, not left running.
