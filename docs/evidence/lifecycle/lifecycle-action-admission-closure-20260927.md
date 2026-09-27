# Watt lifecycle semantics and action admission — consolidated closure

Qualification date: 2026-09-27. This is one consolidated hardening task, superseding the standalone Pre-Work mission. **Code-owned hardening and qualification are complete.** GC-LC-01…15 and all nine neighboring Golden cases qualified. The complete backend corpus has 1,677 uniquely qualified tests and one unchanged upstream ECF-contract skip; frontend 77/77 and Release Evaluation 53 cases / 136 checks qualified. Real Web obligations remain explicitly BLOCKED_EXTERNAL.

Starting clean pushed application baseline: `17ebfb74374659ee9b0c376d6f8cf6f5b7508199`, branch `feature/production-environment-foundation`. The implementation is qualified in the isolated `watt-lifecycle-qualification` runtime at `http://127.0.0.1:8079/app`; the user's retained `8078` runtime is unchanged. Qualified implementation commit: `d585c2009284d7ab35cc027ab9a485148f96253b`, tree `1eae9bb47912f90d6741d491c1d15be0da87b3d5` ([commit receipt](qualified-implementation-commit.json)). Code/test/runtime-harness fingerprint: `af8bc7d790ca6df9acff7ce95e447ccb41685b7f5c6b3bf18950b6b396512df6` ([source manifest](source-manifest-history-final.json)). Earlier trials identify earlier source stages and remain evidence rather than being relabeled as final-source runs. The [runtime activation receipt](runtime-activation-final.json) verifies all 222 application source paths: the app matches final source; worker/coordinator/tool-host images differ only in the read-only historical-query delta, which those execution components do not serve.

Mandatory inputs: [frozen Attempts 1–7 failure map](../dogfood/fsi-hd-01-cross-boundary-failure-map-20260927.md), [system-wide stability closure](../stability/system-wide-stability-closure-20260927.md), unchanged [original Tier-0 corpus](../../../benchmarks/golden/tier0-v1.json), current Interaction, governance, Product, Preview, Native execution and convergence contracts. The historical failure-map SHA256 remains `ae310fdb6630bad284f0d4ac6d0fc8e3cb3606e8606346f90288a8dfbf7b3b05`; all 28 frozen FSI volumes remain present and were not written or removed by this task ([preservation receipt](frozen-fsi-preservation-20260927.json)).

## A. Wrong global assumptions found

| Owner | Previous conflation | Corrected invariant and evidence | Qualification |
| --- | --- | --- | --- |
| Repository Asset / intake contract | Repository intake and local branch authority required a production Work identifier | A persisted explicit Human record can authorize an independent Interaction action. Work-specific mutation retains its Work/Task authority. | LC-01/02/03, PostgreSQL + actual Git |
| WIC production-intent contract | Clone/pull action verbs also counted as production mutation | Acquisition and incomplete future modification are separate facts. Present safe action survives an unknown future scope. | LC-01/02/04; 50 policy/command tests |
| Connector Resolver | Capability requirements and gap recording assumed every operation belonged to Work | Independent requirements may have no Work; no synthetic Work or Work gap is created. Capability is not permission. | LC-01/03/10/11 |
| Product Asset continuity | Repository/Product source establishment assumed Work binding | A known Product/source can exist while production remains unadmitted. Work binding only occurs for actual Work. | LC-01/02/15 |
| Conversation/UI projection | ACTION_REQUEST implied production; no admitted Work erased acquired repository facts | API/SSE/UI preserve repository observation independently from Work admission, and local preparatory actions do not create production authority. | Real browser A/C, LC-15 |
| Control Room | Any Human attention took precedence over required Preview preparation | PREPARING/BUILDING projects Preview owner progress. Sealing/test success alone cannot establish review readiness. | Four PostgreSQL projection states; LC-07 |
| Advisory UI / continuity projection | A completed advisory reply still displayed “respond to current question”; old Work diagnosis survived moving to a prospective conversation | Attention requires an actual unresolved decision. Advisory conversation has no production start; independent repository Product is displayed and stale production history is cleared. | Real browser B; frontend regression |
| Work Reality query / Interaction | A historical-result question fell through to model conversation; lack of recent prose was treated as lack of completed production | Existing read-only query owner reads durable artifact observations, verification and exact Trusted Runtime Commit; completion cannot remove historical evidence or create new Work. | LC-09 live failure preserved, corrected live PASS + two PostgreSQL cases |
| Governed Response Realizer | A repairable closed-schema expression defect immediately failed the reply while production could continue | Reuse the existing one-attempt structural repair, same admitted envelope and meaning; record expression-only recovery, never production replay or global convergence. | Two bounded/exhausted provider cases; 83 related expression/UI tests |
| Golden Worker-loss harness | Read-then-kill was assumed to preserve a settled checkpoint | Freeze the declared process, verify epoch, settled effects and running inference, then inject loss. Uncertain writes remain fenced. No runtime uncertainty guard is weakened. | EX-14 trial 1 unqualified; safe trial 2 fully PASS |

The [canonical semantics](../../architecture/lifecycle-and-action-admission-semantics.md) include the owner/transition map, taxonomy, side effects and semantic gate audit. The census records **60 actual repository state/condition/status/outcome enums** ([census](lifecycle-state-census-20260927.json)). No new Coordinator, Action Manager, PreWork Engine or refinement framework was introduced. Existing production planning, Task Contract, PWU, Candidate and remote governance guards that require admitted Work remain in force.

## B. Canonical eligibility matrix

The versioned [executable 16 × 13 matrix](../../../benchmarks/golden/lifecycle-action-matrix-v1.json) and [policy tests](../../../tests/test_lifecycle_action_policy.py) classify actions independently using explicit intent, lifecycle compatibility, current authority, capability, required credential, side-effect class and observed Reality. The ten classifications are AUTO_ALLOWED, ALLOWED_IF_EXPLICIT, ALLOWED_IF_AUTHORIZED, REQUIRES_HUMAN, REQUIRES_WORK_ADMISSION, REQUIRES_CANDIDATE, REQUIRES_ACCEPTANCE, REQUIRES_DELIVERY_AUTHORIZATION, BLOCKED and SELF_REFINE_FIRST.

| Situation | Read / acquire / local preparation | Production | Preview / review | Remote delivery |
| --- | --- | --- | --- | --- |
| PRE-WORK | Explicit inspect/acquire allowed; branch requires READY base and current local authority | Requires sufficient intent and admitted Work/Task basis | No invented Candidate | Cannot bypass Candidate, acceptance or authorization |
| Work admitted | Inspection remains independent | Existing governed owner admits planning/PWU/mutation | Requires exact Candidate and current verification | Work admission grants no delivery permission |
| Candidate sealed | Reality remains inspectable | Requires legitimate correction/refinement | Required Preview is an automatic system obligation; no Human start | Requires acceptance then separate authorization |
| Human accepted | Read/local inspection remains available | Further change requires its own Work authority | Retained Preview/history remain inspectable | Acceptance grants no remote authorization |
| Delivery authorized | Independent observations continue | No blanket production permission | Exact accepted Candidate remains the basis | ALLOWED_IF_AUTHORIZED only after current grant/credential/manifest checks; receipt proves effect separately |
| Work completed | Read history allowed; new Work can use same Product | New Work uses the current accepted baseline | Past evidence remains readable | Completion does not authorize delivery |
| Retryable / terminal | Eligible retry is bounded; terminal authorization failure is not retried | No retry changes authority | Preparation remains distinct from readiness | Unknown effects remain fenced |

The shared policy supplements existing Repository Asset and GitHub delivery owners. It is a contract and tested admission model, not a replacement router or a new Truth owner; other existing owners retain their valid authoritative guards.

## C. Pre-Work regression

The mandatory literal browser A ran on the final repository-action code, through `/app`, with no tester Git, manual clone, fake admitted Work, or production start. Final Interaction: `50ae2542-a948-4342-8125-1fb2e7835a7b`.

1. “我有个GitHub仓库：https://github.com/hengyizhiyuan/software-production-platform.git，把它clone下来，我要改个需求” established `refs/heads/main`, revision `0b535f63302fe45e88d0b3e203ae991868ced079`, tree `753564ba0a09c0bed999dff17b540b09e581e8d9`.
2. “切一个 feat_test 分支” established `refs/heads/feat_test`, with the same revision/tree.
3. “我现在在哪个分支？” reported the observed `feat_test` and exact revision. Production remained unadmitted; no source edit or push occurred.

Evidence: [final browser A](browser-journey-a-source-final-dom.txt), [independent API projection](browser-source-final-api.json), [four completed SSE streams](browser-sse/), and three independent automated runtime trials for both [LC-01](runtime/lifecycle/GC-LC-01/) and [LC-02](runtime/lifecycle/GC-LC-02/). The streams include completed `response.final` and `message.completed`; actual final receipts retain repository facts.

The later read-only C, “先帮我看看这个仓库使用什么框架，我再决定改什么。”, inspected the pinned `pyproject.toml`: Python/FastAPI and other dependencies, revision above, manifest SHA256 `0168a0d3d9b20db9475110260aadfe09758a0175af085298423a1de63b02e4ad`. It did not start production ([browser C](browser-journey-c-source-final-dom.txt), three [LC-03 trials](runtime/lifecycle/GC-LC-03/)).

## D. Over-correction protection

The literal browser B, “这个仓库以后可能会用到。”, completed as an advisory conversation: repository observation null, admitted Work null, no clone. The final UI offers continued conversation and states no production action was requested ([browser B](browser-journey-b-final-dom.txt), [API](browser-journey-b-api.json)). Three LC-04 trials also used a concrete repository URL with vague future intent and performed no acquisition.

Command witnesses reject negation, instructions explaining clone, search for alternatives, ambiguous multiple targets and branch-status questions as execution authority. Local branch grammar rejects theme switches and file checkout; acquisition URLs are not enlarged by trailing punctuation. These are semantic boundary protections, not case-specific responses.

## E. Authority separation

Three real authenticated push requests to fresh nonexistent delivery authorizations returned **409 AUTHORIZATION_NOT_FOUND**, with fixture remote refs unchanged. The installed GitHub push owner did not create authorization or attempt remote effects ([LC-10 live receipts](runtime/capability-authority-live/)). PostgreSQL owner tests separately prove accepted manifest, configured credential, observed write grant, explicit authorization and current grant revocation are distinct checks.

Three real runtime authority trials retained the configured valid DeepSeek credential and a completed attributable live-provider witness, removed access only from a fresh empty test Interaction, and submitted explicit clone through the ordinary API. Each returned **403 ACCESS_DENIED**, with **zero Turn rows**; test access was restored as fixture cleanup. No credential value is in evidence, and no existing Work was rescued or changed ([LC-11 live receipts](runtime/credential-authority-live/)). The independent Repository Asset execution guard is also exercised after resource authority is removed.

There is no qualified live GitHub write claim: no authorized remote write was requested. The negative boundaries and local fixture ref observations establish that capability and credential do not manufacture authority.

## F. Human attention audit

Repository readiness no longer asks Human to start production merely to acquire/inspect/create the explicit local branch. Vague future conversation no longer displays a fabricated current-question action. Required Preview is scheduled by its existing owner after seal and served verification precedes review.

Legitimate attention remains for one genuinely ambiguous repository target, one material search-domain choice, unavailable external credential, exact Candidate review, independent delivery authorization, and preserved bounded non-convergence incidents. GC-EX-11 remains a successful expected missing-credential escalation; no credential workaround or fabricated Preview is counted as success.

Network-only repository retries retain three attempts and a 300-second invocation budget; auth/not-found terminal outcomes execute once. Exhausted attempts survive restore without resetting the budget. Existing WIC RESPONSE_REFINEMENT records `INTERACTION_ACTION_ONLY` or `EXPRESSION_ONLY`, `work_converged=false`, evidence and attempt budget. Ordinary source/tool repairs and Preview progression do not require Human retry/start actions.

## G. Projection consistency

Final browser/API/SSE simultaneously preserve **Conversation PRE-WORK**, **Repository READY**, **Product known**, **Production NOT ADMITTED**. Product binding is disabled for a repository-only prospective view. No prior Work diagnosis/history appears as the new conversation's production state.

PostgreSQL owner projection checks cover Preview PREPARING and BUILDING → PREVIEW_PREPARING, READY → legitimate waiting for review, FAILED → PREVIEW_UNHEALTHY. Actual required Preview trials run automatically. Local recovery does not overwrite independent Preview/global convergence state: EX-05 trial 2 repaired the tool/source obligation, then exhausted Preview preparation on Docker capacity and remained NON_CONVERGING; that preserved failure is evidence for LC-14, not a successful Work.

## H. Lifecycle Golden corpus

[Corpus v2](../../../benchmarks/golden/tier0-v2.json) retains the original 23 cases verbatim and adds GC-LC-01…15. Boundary qualifications use actual PostgreSQL/Git or authenticated runtime, in addition to policy tests; browser journeys use real production providers and public interfaces.

| Case | Qualification | Trials / evidence |
| --- | --- | --- |
| GC-LC-01 | PASS — explicit public acquisition before Work | 3 runtime trials + final browser A |
| GC-LC-02 | PASS — clone/local branch without edit or push | 3 compound-command trials + browser A |
| GC-LC-03 | PASS — pinned manifest inspection, no production | 3 runtime trials + final browser C |
| GC-LC-04 | PASS — vague future intent has no effect | 3 URL-bearing runtime trials + literal browser B |
| GC-LC-05 | PASS — admitted production/Preview grants no delivery | EX-01/06/07 actual runtime receipts, empty delivery records |
| GC-LC-06 | PASS — exact local acceptance grants no push | EX-15 committed local acceptance + unchanged remote refs |
| GC-LC-07 | PASS — sealed Candidate automatically prepares required Preview | Independent EX-01/06/07/05/14/15 runtime obligations; no Preview start |
| GC-LC-08 | PASS — completed Product starts another Work on accepted baseline | Work `94dfaa83-9d84-5fd1-a58a-df7706055903`, same Product, source `3d31ed65075daa30cca8820a40d750790f7898ba`, automatic Preview; new title and accepted prior button retained |
| GC-LC-09 | PASS — completed Work remains inspectable | Corrected live history query cites actual path, Candidate, verification and trusted commit; prior false reply retained |
| GC-LC-10 | PASS — push capability is not authorization | 3 authenticated negative API trials + 3 current-grant owner trials |
| GC-LC-11 | PASS — valid provider credential is not current resource authority | 3 live 403/zero-Turn trials + 3 Repository Asset owner trials |
| GC-LC-12 | PASS — transient retry / terminal no retry / exhausted no reset | 3 independent PostgreSQL/Git-owner trial sets, durable lineage and WIC recovery scope |
| GC-LC-13 | PASS — legitimate one-target question, deterministic steps autonomous | Ambiguous two-repository live trial + owner qualification; automatic acquisition/Preview trials |
| GC-LC-14 | PASS — local recovery does not claim global convergence | Preserved EX-05 Preview exhaustion and IP-07 downstream non-convergence; corrected EX-14 same-attempt recovery remains independently evidenced |
| GC-LC-15 | PASS — independent repository/Product/Work projections | Final browser A/C, API and four SSE streams; frontend Product/diagnosis regression |

Highest-risk pre-work cases repeated three times; authority and retry owner boundaries repeated three times (6 tests in each set). Preview automation is evidenced by several independent actual production journeys. No byte-identical trajectory requirement was introduced. Existing historical repeat evidence remains unchanged.

The [machine qualification index](lifecycle-golden-qualification-20260927.json) identifies every actual trial and boundary proof. The [projection oracle](independent-projection-browser-oracle.json) joins the browser/API/SSE observations; the [local/global oracle](local-recovery-global-convergence-oracle.json) deliberately qualifies separation using a failed downstream Work rather than claiming that Work succeeded.

## I. Neighbor Golden regression

| Case | Current result | Evidence / retained qualifications |
| --- | --- | --- |
| GC-EX-01 | PASS | Actual one-link minimal diff + served Preview; completed test runtime later retired, evidence retained |
| GC-EX-05 | PASS, trial 3 | Declared no-effect file.read fault targeted this Work; automatic source repair; real browser cancel; only web/app.js changed |
| GC-EX-06 | PASS | Actual transient acquisition recovery + exact label/diff/served Preview |
| GC-EX-07 | PASS | Only requested Help link, exact minimal source diff and served Preview |
| GC-EX-11 | PASS, expected Human dependency | Missing required Stripe secret; legitimate bounded escalation, no unsafe workaround |
| GC-EX-14 | PASS, safe trial 2 | Frozen settled checkpoint; new lease epoch; same Attempt resumed; one settled source write; interrupted inference retained |
| GC-EX-15 | PASS | Exact local acceptance and trusted commit, remote refs unchanged, no delivery authorization. Timed-out HTTP receipt reconciled read-only; no repeated mutation |
| GC-IP-02 | PASS | Real form submission/reload, actual API equals actual Preview SQLite rows |
| GC-IP-07 | PASS, trial 3 | One legitimate users-domain/API-consistency choice; two PWUs and Join verified; actual name/email/empty-result Browser + API queries agree with Preview SQLite; customer domain unchanged |
| Relevant WIC/admission | PASS | 151 focused neighboring owner tests, two read-only history cases, and the complete final PostgreSQL corpus |

Original case requests, forbidden assistance and business oracles remain intact. Independent trials use isolated source identities or run before advancing a shared accepted Product baseline. Initial observer timeouts, the mis-cut Worker fault, shared-baseline collision, Docker capacity exhaustion and actual business-oracle failure are preserved; none is converted into a PASS.

GC-IP-07's final exact Candidate is `837f3590b79e64ea1115484e4ae8a39279ceb80a`, tree `ad464d79fd166530cb6174fb61064b9e095aa826`, served at `http://127.0.0.1:57688/`. The actual served application uses `name` and `email` query parameters. Two business records were submitted through its existing POST `/api/users`; no SQL writes or source repair were supplied by the tester. Browser queries and read-only database inspection independently establish the unchanged business oracle ([trial 3 proof](runtime/neighbors/GC-IP-07/trial-3/business-oracle.json)). Trial 1's shared-baseline/non-convergence and trial 2's actual API oracle failure remain visible with their original identities.

Trial 2's aggregate oracle runner was interrupted by a remote-disconnected response during app reactivation. Its independently retained API/database oracle already failed; a later read-only observation using the actual `name`/`email` contract also returned Fixture User for an unmatched name. That bounded business failure and the interrupted aggregate runner are distinguished explicitly ([classification](runtime/neighbors/GC-IP-07/trial-2/qualification-classification.json)); neither is relabeled as an aggregate PASS.

## J. Full regression

| Verification | Final result |
| --- | --- |
| Policy / command semantics | 50 passed |
| PostgreSQL repository/Reality owner supplement | 57 passed (15 owner + 42 earlier policy; final policy set separately has 50) |
| Current authority + retry repetitions | 3 × 6 passed; zero failures |
| Historical read-only owner | 2 passed; no provider invocation, Work revision/run/step changes |
| Related expression/UI Python regressions | 83 passed |
| Focused neighboring PostgreSQL owners | 151 passed |
| Complete backend unit partition | 930 passed, 1 known upstream ECF Preview-contract skip; zero failures |
| Complete backend integration partition | 747 uniquely qualified: isolated primary 737 passed / 1 database-name failure / 9 required-name setup errors; exact 10 cases passed with unchanged assertions in required `spg_test`; zero remaining failures |
| Complete frontend | 77 passed; zero failures |
| Fresh migrations | Head `20260927_58` reached |
| Alembic check | PASS — no new upgrade operations |
| Release Evaluation | PASS — all 53 selected cases / 136 selected checks, zero failures; 4 real-container cases, zero failures; 6 recovered, 3 expected escalations |
| Frozen FSI evidence | PASS — same hash, all 28 volumes retained |
| Final source/secret/diff/tree checks | PASS — frozen source unchanged, actual credentials absent from commit candidates, whitespace/link checks pass; clean tree checked after evidence commit |

Release Evaluation is [durable](release-evaluation-source-final.json). Its live subprocess cases use the source available when dispatched; the later historical-query delta has independent owner/live proof and is included in the complete frozen-source backend partition. Unit and integration partitions are disjoint; retries/supplements are not added to the unique full-suite count. The complete unique backend count is **1,678 collected: 1,677 qualified PASS, one known external SKIP, zero remaining FAIL/ERROR**. Original integration outcomes are preserved: DB-01 and the response-contract schema fixture assert the literal database name `spg_test`, while the complete isolated partition used `spg_lifecycle_integration`. The exact 10 unchanged tests passed in the required-name fixture ([primary receipt](verification-logs/backend-integration-history-final.xml), [connectivity supplement](verification-logs/backend-required-database-name.xml), [nine contract tests](verification-logs/backend-required-database-contract.xml)); the isolated primary is not described as all green. A separate complete collection of 1,678 tests exactly matches the disjoint partition union. The existing sibling ECF Preview contract is unavailable at its checked-out owner revision and remains the single explicitly unqualified historical contract. It is not relabeled as test success.

Early broad attempts are retained: old JS cache-version assertion, two four-second retry deadlines under concurrent load, and a fresh database started before full migrations. The assertion was updated to the actual cache version, the deadlines/budgets were not weakened, and the final integration partition uses a migrated isolated database. Interrupted runs are not complete full-suite qualifications.

Raw SSE records retain their mandatory event-separator blank lines; captured pytest diagnostics/XML retain their original indentation. Scoped Git whitespace attributes preserve these exact evidence bytes. Authored source, tests and documentation remain under ordinary whitespace checks; no test assertion, deadline or acceptance oracle was relaxed.

## K. Remaining risks and deferred qualifications

**Real Web Search is BLOCKED_EXTERNAL** because `SPG_WEB_SEARCH_API_KEY` is not supplied, by explicit Human instruction. This includes SEARCH-Q2, the Web component of SEARCH-Q3, model-initiated Web retrieval, live provenance/refinement/convergence and GC-EX-12. No real retrieval was attempted in the new blocked receipts ([deferred Web](deferred-web/)). This dependency does not stop implementation, Golden cases or regression independent of that key. GitHub/page Fetch and deterministic Search tests cannot stand in for live Web evidence.

The [separate live Web/GC-EX-12 entry](../../operations/web-search-live-qualification.md) retains exact runtime activation, raw input/Turn/SSE, provider/query/rank/timestamp/URL/Evidence ID, inspected page content, citations/synthesis, pinned project paths/hashes, latency/tokens/costs and no unauthorized production as requirements. Fresh trial identities are mandatory; credential values must remain private.

The frozen-frontier fault rule preserves unknown-write fencing. An uncertain-effect cut cannot be rescued by clearing DB state or replaying source effects. Docker's finite network capacity requires retiring completed qualification runtimes explicitly; only five empty older qualification networks and completed runtimes from this batch were retired, with all volumes/evidence preserved. Retired endpoints are historical proof, not advertised as currently available.

No uncovered lifecycle/action defect remains in the qualified task scope. The upstream ECF Preview-contract skip is an unchanged external owner qualification gap, and real Web evidence remains the explicitly deferred external dependency. Human product acceptance remains separate from automated qualification and is not granted by this report.

### Completion invariants

The [machine verification](lifecycle-action-admission-verification-20260927.json) records exact counts and external exclusions; the [evidence manifest](evidence-manifest-20260927.json) pins supporting artifacts. FULL_BACKEND_REGRESSION describes the completely collected/reconciled corpus with its explicitly unqualified upstream skip, not an assertion that skipped or blocked live obligations passed. Final clean-tree output is retained in `.spg/lifecycle-hardening/final-working-tree.json` after committing this evidence.

| Invariant | Result |
| --- | --- |
| `NO_WORK_ADMITTED_DOES_NOT_MEAN_NO_ACTION_ALLOWED` | PASS |
| `WORK_COMPLETED_DOES_NOT_MEAN_NO_FURTHER_PRODUCT_ACTION` | PASS |
| `WORK_ADMISSION_AND_ACTION_ADMISSION_ARE_DISTINCT` | PASS |
| `LIFECYCLE_STATE_AND_ACTION_ELIGIBILITY_ARE_DISTINCT` | PASS |
| `CAPABILITY_CREDENTIAL_AUTHORITY_ARE_DISTINCT` | PASS |
| `HUMAN_ACCEPTANCE_AND_DELIVERY_AUTHORIZATION_ARE_DISTINCT` | PASS |
| `LOCAL_RECOVERY_AND_WORK_RECOVERY_ARE_DISTINCT` | PASS |
| `EXPLICIT_SAFE_PRE_WORK_ACTION_CAN_EXECUTE` | PASS |
| `IMPLIED_FUTURE_ACTION_DOES_NOT_EXECUTE` | PASS |
| `PRE_WORK_REPOSITORY_ACQUISITION` | PASS |
| `PRE_WORK_LOCAL_BRANCH_OPERATION` | PASS |
| `PRE_WORK_READ_ONLY_INSPECTION` | PASS |
| `PRODUCTION_MUTATION_REQUIRES_SUFFICIENT_WORK_INTENT` | PASS |
| `REMOTE_DELIVERY_REQUIRES_EXPLICIT_AUTHORIZATION` | PASS |
| `CANDIDATE_PREVIEW_DOES_NOT_REQUIRE_HUMAN_START` | PASS |
| `WAITING_FOR_HUMAN_ONLY_MEANS_REAL_HUMAN_DEPENDENCY` | PASS |
| `TRANSIENT_ACTION_FAILURE_SELF_REFINES` | PASS |
| `TERMINAL_ACTION_FAILURE_DOES_NOT_BLINDLY_RETRY` | PASS |
| `LIFECYCLE_NON_CONVERGENCE_IS_BOUNDED` | PASS |
| `INDEPENDENT_REALITY_PROJECTIONS_ARE_TRUTHFUL` | PASS |
| `GC_LC_01_TO_15` | PASS |
| `NEIGHBOR_GOLDEN_REGRESSION` | PASS |
| `SYSTEM_WIDE_SELF_REFINE_REGRESSION` | PASS |
| `WORK_LEVEL_SELF_CONVERGE_REGRESSION` | PASS |
| `FULL_BACKEND_REGRESSION` | PASS |
| `FULL_FRONTEND_REGRESSION` | PASS |
| `RELEASE_EVALUATION` | PASS |
| `ALEMBIC_CHECK` | PASS |
| `FINAL_WORKING_TREE_CLEAN` | PASS |
