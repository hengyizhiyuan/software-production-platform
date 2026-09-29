# IRK behavioral convergence: failure map and later discoveries

The starting map is based on the preserved `388662d` checkpoint, `REPORT.md`, the
frozen fourth receipts archive, Tier0 matrix r290, lifecycle matrix r247,
language metrics r259, and scope-owner receipt r282. Later diagnostic findings
are called out in their rows. This is a diagnosis, not a final qualification
result. Historical receipts remain unchanged.

## Shared owners and first divergence

| Owner / invariant | Preserved failing observations | First divergence from the oracle |
| --- | --- | --- |
| WIC semantic compiler and IRK binder: clause preservation, contextual references, current intent, target integrity | Visible 12/41 failures (11 compile, one semantic mismatch); unseen compiler 6/40 failures; unseen live HO-001/005/008/035; Tier0 GC-EX-02, GC-EX-03/3, GC-EX-05/2-3, GC-IP-03, GC-IP-07/1-2; lifecycle GC-LC-01/2-3, GC-LC-02/1-2, GC-LC-13 | A current requested clause is omitted, malformed, contextually unbound, or wrongly classified before owner admission. The ledger cannot execute an absent item. The retained groups include contextual 0/3 visible and 0/4 unseen, production-positive 3/8 visible, and status 0/1 visible. Individual Tier0 `result.json` receipts report missing Work or attention; their `journey.json` inputs identify the requested effect. Exact provider failures are in the frozen archive. |
| Branch effect authority: composite action and pre-write gate | GC-LC-02/3; historical source2 HO-002; branch-distinction mismatch; current-source unrequested switch receipt r246 | A create-only Human request compiled as `CREATE_AND_SWITCH_BRANCH`; physical HEAD moved from feat_semantic_3_4 to feat_semantic_3_5. A post-write expected-effect check cannot prevent this. Source2's `refs/heads/refs/heads/main` write is separate historical evidence. |
| Owner realization ledger: Work question and correction | GC-IP-07/3, scope-owner-gap r282; `TURN_OBLIGATION_LEDGER`, `OBSERVED_EFFECT_CLOSES_OBLIGATION`, Work Self-Converge PARTIAL | Three correctly typed scope constraints created zero obligations. The exact pending Steering question remained, the same Work stayed NEEDS_ATTENTION, and no queue or Preview followed. Typed IR existence was mistaken for owner consumption. |
| Answer coverage and response basis | Branch status Turn e5cf4d13… / r207; stale production-status reply; `RESPONSE_REALIZER_IS_REALITY_GROUNDED` PARTIAL | A grounded paraphrase failed `QUESTION_ANSWERED` because prose was compared literally; another reply used an older owner snapshot after Work/Preview advanced. |
| Turn semantic lifecycle | Ordinary branch trial 1; `ONE_GOVERNED_SEMANTIC_REALIZATION_PER_TURN` PARTIAL | Exhausted technical compilation can leave the Turn without a persisted governed semantic lifecycle record. This must be represented as failed compilation, without invented meaning. |
| Steering semantic provider and bounded refinement | GC-EX-08/1 (missing genuine scope clarification despite two login buttons), GC-EX-11/1 (goal not admitted, missing-secret boundary not reached), GC-EX-13/3 (`.git/**` proposal blocked DESIGN), GC-IP-03/1 | Provider candidates or owner semantic decisions failed before the intended business/credential oracle. The `.git/**` path is a model candidate defect; the source scope validator correctly rejects it but did not recover. |
| Native Worker recovery projection and result fencing | GC-EX-14/1; action/Work Self-Refine PARTIAL; invalid native result claims | Trial physically resumed the same Attempt under a new lease with no duplicate source effect, yet `WORKER_LEASE_LOST` refinement stayed FAILED. Malformed evidence IDs must be fenced while preserving settled effects and Worker service. |
| Research retrieval | GC-EX-12 partial trial 2 | GitHub available-surface retrieval exceeded the bounded 250,000-byte fetch and yielded zero source/citation evidence. Web separately requires the withheld credential. The available failure cannot be classified as external. |
| Steering basis persistence | Observed duplicate basis insert in `REPORT.md` | Concurrent or retried basis insertion did not establish idempotent identity before the uniqueness boundary. The database error alone is not a semantic resolution. |
| Frontend Work projection | Preserved PRE_WORK DOM observation | Previous Work source/Preview details remained visible briefly while current focus changed. Projection identity and data invalidation were not atomic. |
| Qualification infrastructure | Preserved Docker address-pool exhaustion | Disposable runtime network lifecycle exceeded host capacity. Cleanup must target only owned disposable resources, retaining historical volumes and frozen evidence. |
| Production exclusion projection | Candidate-17 GC-EX-13/4 reached a Steering question that treated “不在列表显示” and “列表显示客户备注字段” as contradictory | `project_interaction_candidate` flattened `ProductionIntent.exclusions` into Work constraints without negative polarity. Commit `6abc247` marks each exclusion explicitly; Candidate-18 GC-EX-13/5, /7 and /8 each reached an independent Preview and passed the live browser/API/SQLite oracle. |
| Qualification Preview retention | Candidate-18 GC-EX-13/6 completed four PWUs but all Preview retries hit Docker address-pool exhaustion at 32 networks | Old completed synthetic holdout Works had started 10 retained Preview runtimes (20 networks) and the qualification harness never retired those asynchronous runtimes. The bounded holdout-retirement helper now checks a PASS result, exact Work/session identity, minimum age and Docker ownership labels before retiring containers/networks while preserving volumes and receipts. Five old PASS Previews were retired with retained evidence, reducing the network count from 32 to 22. Trial 6 remains a failed diagnostic receipt. |
| Release connector provenance assertion | Candidate-18 clean-database Release GJ-SR-01 and SR-Q1 failed on the same branch test | The first test variant executed with `builtin:git` before registering `learned:native-git` from its verified checkpoint. Its fixture cleared product/runtime tables but left connector overlays behind, so later variants saw the learned connector. The fixture now clears the four mutable connector tables as well while preserving migration-seeded authority actors; the first-execution assertion checks `builtin:git`, and post-registration retention remains separately checked. |
| Integration database identity assertion | Candidate-18 integration shard C stopped at `test_db_01_connectivity` on an independently named test database | The assertion hard-coded `spg_test` despite the fixture using the configured database URL. It now verifies the health-reported database name against that URL; the targeted test passes and the full shard is rerunning on a fresh migrated database. |

## Finite failed slots to close

Tier0: GC-EX-02/1; GC-EX-03/3; GC-EX-05/2-3; GC-EX-08/1;
GC-EX-11/1; GC-EX-13/3; GC-EX-14/1; GC-IP-03/1; GC-IP-07/1-3.
GC-EX-12/1 is Web `BLOCKED_EXTERNAL`; its separate GitHub partial trial is an
internal research failure. Tier0 baseline is 30 PASS / 12 FAIL / 1 external.

Lifecycle: GC-LC-01/2-3, GC-LC-02/1-3, GC-LC-13/1. Baseline is 25/31 PASS.
GC-LC-02/3 is a confirmed physical false effect, not merely a failed response.

The 38-invariant baseline is 21 PASS / 8 PARTIAL / 9 FAIL. The exact invariant
names and preserved evidence are in `REPORT.md`; the final audit must update
every row from new source-qualified receipts, including Human Acceptance PENDING.

## Repair order

1. Prevent unauthorized physical effects before writes; preserve atomic effect
   authority and parameter provenance through the intake/Native boundary.
2. Improve compiler clause completeness and bounded candidate refinement, then
   semantic lifecycle persistence.
3. Realize typed semantic items in their target owners and reconcile actual
   receipts; fix answer coverage and response freshness.
4. Repair remaining Steering, Worker, research, persistence, UI, and harness
   failures by owner, then run the full frozen-source qualification protocol.
