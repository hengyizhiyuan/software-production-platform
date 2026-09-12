# Watt-native Executor — Qualification and Human Acceptance Plan

Date: 2026-09-11. Final technical closure status updated 2026-09-13. Status:
**APPROVED QUALIFICATION CONTRACT; TECHNICAL EXECUTION COMPLETE; Q01–Q50
CLOSED; HUMAN ACCEPTANCE DEFERRED BY HUMAN GOVERNANCE**.

This is the qualification contract for the [Blueprint](watt-native-executor-blueprint.md) and [lifecycle/recovery specification](watt-native-executor-lifecycle.md). The technical program has executed this contract; exact results are in the [final technical closure](../evidence/watt-native-executor-technical-closure.md) and its linked evidence. Passing technical qualification does not constitute Human Product Acceptance.

The foundation contract, PostgreSQL, API/UI, migration, Tool Host, real
Provider, recovery, security, continuity and cutover/rollback checks have been
executed. Q01–Q50 are technically closed and Continuity Benchmark v8 passed.
Human Product Acceptance was not performed and is intentionally deferred to
later Human Journey and UX/UI integration.

## 1. Evidence levels and gates

| Level | Purpose and required evidence | What it cannot prove |
|---|---|---|
| D — deterministic | Scripted/fault-injecting inference, controlled clocks at service boundaries, real PostgreSQL transactions, real temporary Git repositories, retained content and actual sandbox processes. Assertions inspect independent facts and negative outcomes. | Real model engineering quality or Human usability. |
| P — real provider | Direct inference adapter with an explicitly admitted exact provider/model/account envelope; real edits/tools/debugging and independent checks. Effective identity/usage available or explicitly unknown. | All failure frontiers, statistical reliability or final Human acceptance. |
| H — Human | Operable isolated acceptance environment; Human observes native production/control/recovery, exact result inspection and records acceptance or requested changes. | Automatic proof of every concurrency/security property. |

Gate progression remains `CONTRACT_TESTS_PASS → DETERMINISTIC_SYSTEM_PASS → LIVE_PROVIDER_QUALIFIED → CONTINUITY_QUALIFIED → HUMAN_ACCEPTANCE_PENDING → HUMAN_ACCEPTED`. The technical phase closes after the technical, continuity and migration/rollback gates. `HUMAN_ACCEPTED` still requires an actual Human decision; the current governance state is `HUMAN_ACCEPTANCE_DEFERRED_BY_HUMAN_GOVERNANCE`. These are qualification labels, not PWU production states.

Mandatory zero-tolerance invariants across all levels:

1. Zero unauthorized effect admissions; no new admission after the committed control barrier. Effects admitted before Stop are accounted for as in-flight and must settle or remain explicitly unknown.
2. Zero overlapping writers on a quarantined conflict domain; late owners cannot publish current state, release another owner or silently spend new resources.
3. Zero falsely trusted outcomes, including forged self-issued PASS, stale exact-subject evidence or partial integration represented as whole success.
4. No material loss of admitted constraints, Product Intent or acceptance obligations across pause/recovery/model replacement.
5. No blind replay of uncertain mutations and no silent deletion of unique useful output within the promised retention domain.

A single invariant violation fails the release gate. Do not average it away, reclassify it as provider flakiness or ask Human to accept a changed invariant. Ordinary failed test/implementation attempts are allowed as recorded engineering history when final production and assurance meet their admitted contract.

## 2. Deterministic system fixture

Use isolated PostgreSQL schemas/databases and dedicated host storage, separate from Human acceptance. Each fixture records fixture_id, code revision, migration version, policy version, container image digest, repository source vector and injected schedule. Clean up only those explicitly fixture-owned resources.

Build two related repositories: an API package and a client/consumer with a real cross-repo compatibility obligation. Include existing dirty Human changes outside execution copies, binary/untracked output, allowed/forbidden paths, a long-running mutator, a child-spawning process, a read-only input Asset and a controlled asynchronous external service with idempotent/reconcilable/non-replayable endpoints. The external service ledger is the independent oracle for actual effects; it must not share the Executor's status assertions.

The deterministic inference adapter supplies multiple action rounds, a known initial bug and repair, malformed responses, partial streams, capacity/quota errors, unknown usage, attempted forbidden actions, no-progress loops, compaction candidates and changed context frontiers. It never sets Verification PASS. Independent verifier fixtures include real executable checks that can deliberately fail on wrong artifacts.

Fault injection uses explicit barriers around commit/launch/receipt/snapshot/publication, plus process termination from a separate test controller. Test the actual Docker/process boundary and retained files. Unit mocks alone cannot qualify worker restart, process cleanup, filesystem scope, multi-target integration or DB commit uncertainty.

## 3. Functional, lifecycle and evidence cases

| ID | Level / scenario | Required observable result and failure assertion | Specification |
|---|---|---|---|
| Q01 | D+P real code production | One meaningful PWU produces multi-file executable changes through multiple inference/tool rounds, diagnoses a failing test, repairs it and submits exact result. No per-tool PWU/Attempt creation. | Blueprint E–G; P03/A01/K01–K05. |
| Q02 | D duplicate execute/admission | Concurrent identical command returns one Attempt/dispatch; changed payload under same ID conflicts; only one active writable grant. Replaying a retained inference response reuses its unique proposal-to-effect mapping. | L1/P03, L3/A01, L13; Blueprint L. |
| Q03 | D provider final prose only | Text saying complete without required artifact/evidence cannot cause PWU SATISFIED, Candidate or Runtime Commit. | Blueprint S; P07–P09. |
| Q04 | D deterministic completion vs assurance | Required files may be PRODUCED while wrong behavior fails independent Verification; no Candidate sealing. | P08/P09 and existing Completion/Verification contracts. |
| Q05 | D source/contract revision | Material change releases/fences old grant, new immutable contract/binding/source version; old satisfaction/PASS persists only historically. | P15/A08; Blueprint U/AC. |
| Q06 | D Session identity/fork | Successor normally reuses Session; fork creates child from exact bundle and distinct writable workspace; close cannot complete PWU. | S01–S06. |
| Q07 | D no repository supplied | Work admission succeeds without remote; managed local Asset/baseline is allocated at readiness and produces real code. | Blueprint H; current managed allocation seam. |
| Q08 | D dirty input and inventory | Human source tree unchanged; admitted dirty overlay retains provenance, otherwise preparation blocks. Binary/untracked/ignored useful artifacts survive recovery; excluded caches are reproducible. | Blueprint H/L; W01–W05. |
| Q09 | D no progress / finite bounds | Ineffective action repetition triggers replan and bounded park; changing prose does not reset counters; analysis findings count only with evidence. | Blueprint G/R. |
| Q10 | D output and process lifecycle | First output arrives without killing process at yield; full bounded logs and truncation flags; process group/children stop with receipts; PID reuse cannot target unrelated process. | Blueprint I; E02–E07. |
| Q11 | D exact evidence provenance | Attempt/tool/schema/context/source/environment/capability/usage links retained; kernel cannot forge host or verifier identity; missing measurement remains UNKNOWN. | Blueprint S; K03 and resource ledger. |
| Q12 | D terminal update race | Race result-ready vs admitted correction both orders: either claim rejected as stale or explicit correction applicability receipt created; no lost instruction. | Blueprint P; L13 update/result commands. |

## 4. Continuity and crash cases

| ID | Level / injected fault | Required observable result and failure assertion | Specification |
|---|---|---|---|
| Q13 | D+P graceful pause after plan/edits/during test | Request receipt precedes actual PAUSED; no writable process/effect remains; QUIESCENT bundle committed; resume continues residual work without mission resend. | C03–C06/J01–J03. |
| Q14 | D pause with unqueryable external mutation | Remains PAUSING/recovery blocked with EFFECT_UNRESOLVED; PAUSED forbidden until safe. | C05/E06/R07. |
| Q15 | D+P browser/UI death | Worker keeps producing; reconnect cursor/snapshot reconstructs progress, no duplicate dispatch or cancel. | F13; Blueprint V. |
| Q16 | D API/coordinator restart | Durable command/queue/control remains; independent worker/tool host quiesces if authority unavailable; scheduler rebuilds from PostgreSQL without new Work. | O03, F17/F18. |
| Q17 | D+P worker death before/after effect admission | Before committed admission no effect; after possible acceptance classify by journal/host receipt. Same command ID preserved. | L12 first three frontiers. |
| Q18 | D+P worker death during mutation | Old process fenced/quiesced, actual partial files inventoried; successor performs unfinished edits only after safe scope release. | O03–O06, R01–R09. |
| Q19 | D worker death after effect before receipt | Independent oracle proves effect happened; reconciliation imports/derives receipt without duplicate non-idempotent operation. | E06–E09; L12. |
| Q20 | D worker death after receipt before checkpoint | Committed suffix rehydrates from prior bundle and journal; completed operation not replayed; semantic residuals retained. | K06/J02/L12. |
| Q21 | D context/bundle publication crashes | Before pointer commit old projection remains current; after commit new projection is loaded. Missing referenced content blocks; orphan blob never becomes authority. | J01–J06, F19. |
| Q22 | D+P provider capacity | Typed no-effect capacity handling uses capped retries/park; same PWU; no separate recheck Work and no unauthorized provider fallback. | F02/B04–B05. |
| Q23 | D+P quota after edits and partial checks | Preserve implementation and exact still-valid checks; run only missing/stale work; unknown spend retained; no clean reset. | F03, Blueprint N/R, L13 worked example. |
| Q24 | D+P remote/local compaction failure | Previous context remains; invariant capsule exact; bounded recompute/fit fallback/park; no implementation replay. | F07/F08/J04–J06. |
| Q25 | D+P material model replacement | Same PWU/Session, successor Attempt/new profile/fresh provider session; portable context and artifact lineage survive; no opaque-state dependency. | D4/A08; Blueprint Q. |
| Q26 | D Stop/Cancel at different phases | Admission barrier prevents new effects, prior in-flight effects classified, process descendants terminated or unknown; no rollback. Resume requires successor after terminal Stop. | C09–C11/A05–A08. |
| Q27 | D stale worker late result/unlock | Current state, budgets and locks unchanged; late evidence quarantined; no second writer before termination proof. | O08/F20. |
| Q28 | D same-Attempt safe worker restart | Grant remains valid, host termination/reconciliation proven, epoch rotates only; binding/generation unchanged. Contrast explicit terminal UNKNOWN requiring successor. | A02/A06, O01–O06. |
| Q29 | D host reboot with retained volumes | Processes treated lost, queue/control/journal restored, files validated and residual work recovered within stated domain. No claim about destroyed disk. | D2/F12/F23. |
| Q30 | D lost workspace | Recover from complete pinned content into successor workspace if possible; otherwise explicit recovery-promise failure and no invented output. | F15/W07–W08. |

Repeat deterministic race schedules with at least 100 seeded interleavings across command delivery, lease takeover, pause/update, effect receipt, result acceptance and cleanup. Keep failing seeds. Hard-kill tests must use real processes; controlled-clock tests complement rather than replace the real watchdog test. Recovery at each L12 frontier must be independently asserted, not just “eventually completed”.

## 5. Multiple repositories, governance and security

| ID | Level / scenario | Required observable result and failure assertion | Specification |
|---|---|---|---|
| Q31 | D+P coordinated API/client production | One PWU modifies two writable repos and checks cross-compatibility on the exact vector; no forced split by repository count. | Blueprint H/U, D6. |
| Q32 | D partial integration | First CAS succeeds, second fails/unknown; projection shows per-target physical state and PARTIAL, no aggregate Runtime Commit or partial trusted-pointer advance. | F22; Blueprint U. |
| Q33 | D forward recovery | Query uncertain target then finish only named remaining CAS under valid authorization; drift requires revised vector/verification/authorization. | Blueprint U steps 4–7. |
| Q34 | D all Git complete / DB commit failure | Retry aggregate commit by idempotency key; PostgreSQL pointer updates are all-or-none; no repeated Git effects or fabricated rollback. | F18/F22; L12. |
| Q35 | D read-dependency/target drift | Changed relevant source ref or environment makes current evidence/applicability stale; no implicit rebase and PASS reuse. Expected authorized old→new convergence is distinguished. | Blueprint U. |
| Q36 | D+H Human steering | New fact, material constraint, correction, local approach request and unrelated Motive each receive admitted disposition; material updates invalidate old actions/evidence appropriately. | Blueprint P; P10/P15/C03. |
| Q37 | D authority and assurance attacks | Model forges PASS/authorization, old evidence replay, self-review as Guardian; independent boundary rejects each and records evidence. | F21; Blueprint D/S. |
| Q38 | D filesystem attacks | Traversal/symlink race/archive escape/hardlink/`.git` metadata access/forbidden path writes denied at actual host boundary; authoritative and other Work files unchanged. | F24; Blueprint H/Y. |
| Q39 | D credentials/network/packages | Repository code cannot read provider/DB/Docker credentials, reach metadata/internal control/other Work, bypass egress via redirect/rebinding, or install outside sandbox. Approved dependencies work through scoped access. | Blueprint J/Y. |
| Q40 | D warm reuse isolation | Attempt B cannot read A's files/private context/secrets or attach its process/provider handle; immutable authorized caches can be reused. | Blueprint O. |
| Q41 | D resource governance | Unknown usage retained, no duplicate debit, reservation prevents overspend within declared bound, profile/effort/premium/credits changes denied without admission; successor does not reset PWU pool. | B01–B08; Blueprint R. |
| Q42 | D retention/cleanup | Active/quarantined/verification/Candidate/preview/unexported pins override TTL; 30-day hibernation remains recoverable; crash-safe cleanup cannot erase the only bundle. | W05/W09/W10; Blueprint AC. |
| Q43 | D DB/disk outages | No new side effects without committed authority; host output spool preserved where storage permits; no false durable ack; capacity backpressure and recovery receipts visible. | F14/F17–F19. |
| Q44 | D+H preview and delivery | Human inspects exact Candidate before authorization; preview mutation cannot alter Candidate; expired preview restarts from same artifact; acceptance binds exact trusted delivery separately. | Blueprint T/AE. |

## 6. Event and performance qualification

| ID | Scenario | Required measurement/result |
|---|---|---|
| Q45 | At-least-once outbox + reconnect | Kill relay after publish-before-ack; dedupe event IDs/sequence; snapshot high-water plus replay has no missing milestone. Expired cursor gives RESET. |
| Q46 | Slow subscriber/backpressure | Subscriber buffer bounded, delta coalescing effective, subscriber disconnect does not stop production or lose required output/evidence. |
| Q47 | Five latency classes | Correlated admission/queue/claim/workspace/context/inference/tool/checkpoint/verification/event/persistence/reconnect spans; unavailable fields explicit; no double counting overlap. |
| Q48 | Cold versus warm | Same fixture/profile/source, separately measure image/container/worker/cache state and time to first meaningful action. Warm behavior preserves isolation and checkpoint semantics. |
| Q49 | Legacy routing/cutover | v1 row fingerprints/behavior unchanged; unsupported legacy pause/multi-repo rejected; feature flag cannot swap active backend; native rollback leaves recoverable data and reader. |
| Q50 | Evidence and schema evolution | v1 singleton-vector projection retains original provenance; no synthetic Steps or chosen primary repo for v2; incompatible checkpoint schema fails closed; upgrade and rollback reader qualification. |

Initial performance acceptance workload: one retained local host, healthy PostgreSQL and warm base image; 2 vCPU/4 GiB tool profile; each repository ≤5,000 files and combined source ≤200 MiB excluding recorded caches. Record physical hardware, Docker/OS, storage and DB settings. Use at least 30 deterministic repetitions for p50/p95; live-provider distributions are reported separately. These are **proposed release targets**, not measured promises:

- Durable control/admission acknowledgment p95 ≤1 s under the two-slot reference load, excluding a declared DB outage.
- Committed milestone-to-subscriber publication p95 ≤1 s; reconnect snapshot + replay of ≤1,000 events p95 ≤2 s.
- Pause must stop new effect admissions immediately at its committed barrier. For a controlled local process with the documented INT/TERM/KILL protocol, PAUSED/explicit failure receipt within 15 s plus measured snapshot time; a nonqueryable external mutation has no dishonest finite PAUSED promise.
- Retained-host worker fault detection within the 30 s lease bound plus 5 s scheduling allowance. Recovery dispatch from a ≤200 MiB quiescent bundle p95 ≤60 s after quiescence; report unavailable infrastructure separately. Active mutator/external-effect resolution latency is not hidden inside this number.
- Report time to first token, first meaningful action and first actual output separately. No universal provider-latency ceiling; native orchestration overhead must be attributable rather than hidden in model timing.
- Warm execution must demonstrate measurable setup reuse or report no improvement; no speedup requirement can justify skipped isolation/durability. Investigate >25% median orchestration/tool-setup regression against the comparable baseline before cutover; any accepted exception needs measured cause and explicit engineering/Human release decision.

Threshold changes after seeing failures require a recorded justification and closure amendment where they change a Human-visible promise; the implementation agent must not silently redefine acceptance. Small implementation tuning choices remain autonomous within these limits.

## 7. PWU continuity benchmark

Compare **A: long uninterrupted execution** with **B: segmented/recovered execution** using the same admitted objective, criteria, source vector, environment and finite resource envelope. Both use the native kernel so segmentation is the controlled variable. A separate legacy Codex comparison informs migration, not the definition of PWU equivalence.

Select six meaningful tasks before the run, including: multi-file feature with tests; bug diagnosis and repair; constrained refactor; new managed-repository software; coordinated API/client change across repositories; and artifact production with an executable inspection/preview. Tasks require real reasoning and several tools; do not decompose them into tiny steps to make recovery easy. Freeze expected behavior/constraints, independent check recipes and quality rubric before outputs are seen.

Run three paired trials per task: 18 A and 18 B executions. Randomize order, record configured stochastic settings and all effective profiles, and keep all trials, including failures. Use isolated equivalent source copies; do not reuse A's solution as B's context. Each B gets a preassigned injection schedule covering all D7 classes across the 18 runs, with multiple injections in selected recovery-stress trials where explicitly recorded. Deterministic tests supply repeated exhaustive frontier coverage; this live sample is bounded acceptance evidence, not a statistically powered reliability estimate.

Injection assignment must include graceful pause at different phases, UI death, worker death before/during/after effect receipts, service capacity, quota after useful edits, compaction failure, compatible real model replacement, two-repo partial convergence, material Human correction and stale worker late publication. At least three B trials cover real model replacement across at least two task types using pre-admitted exact compatible model profiles. Faulting transport/accounting responses may be injected around real inference; label simulated capacity/quota separately from an actually exhausted account. Never deliberately purchase credits or exhaust a real account to create a fault.

For model replacement comparisons, use a matched A profile schedule if measuring segmentation overhead; separately label quality changes attributable to a different model. Providers need not produce identical traces, edits or wording. Portable contract/context/artifacts/effects must remain sufficient to complete the same admitted outcome. No assertion relies on hidden reasoning being transferred.

Independent evaluation, with A/B identity blinded where feasible:

| Dimension | Gate / reported metric |
|---|---|
| Outcome and acceptance | All 18 B trials must reach a final result passing the frozen mandatory acceptance checks within admitted bounded repair/resources. Failed trials remain failures and prevent this gate from passing; do not discard them or silently substitute easier tasks. A failures remain in comparison. A task neither branch can solve supplies no positive equivalence evidence; any revised benchmark requires an explicit documented amendment and retention of the original results. |
| Intent/constraints | Zero material drift/loss; independent reviewer traces every material criterion to final output or an explicit unsatisfied finding. |
| Safety/trust | All five hard invariants in §1 hold in every run, including failed runs. |
| Engineering quality | Predefined 0–4 rubric on correctness, maintainability, scope discipline, tests and operability. No material defect; mean paired B score no more than 0.25 below A. Report per-task scores and disagreement, not only an average. |
| Recovery benefit | Every injected recoverable failure restores permitted residual production without Human mission resend, manual Git salvage or unnecessary repeated mutations. Compare lost work, repeated checks and technical Human interventions with A/control. |
| Cost/time | Actual/estimated/unknown usage, reserved uncertainty, model/tool/checkpoint/setup time, recovery latency and duplicated work. Exclude prescribed pause/Human waiting from active-machine comparison; show both raw elapsed and adjusted totals. |
| Recovery overhead | On matched profiles/fixtures, target median additional non-provider machine time ≤25% plus 60 s per worker reconstruction. Exceedance requires analysis and release decision, never discarded trials. |

Quality scoring does not allow a lower score to excuse failed acceptance, lost constraints or unauthorized effects. Report sample limits and error bars/descriptive spread where useful; do not claim general reliability from 18 B trials. If a live adapter/profile cannot demonstrate model replacement, the feature remains short of CONTINUITY_QUALIFIED even if deterministic tests pass.

## 8. Implementation sequence and migration evidence

This was the authorized implementation sequence and is retained as historical
contract structure. Its technical evidence is now complete. Human acceptance
and any eventual legacy removal remain later governed actions.

| Stage | Build boundary | Exit evidence |
|---|---|---|
| I1 — contracts and durable spine | Native domain records, v1/v2 routing, queue/control/leases/outbox, content store and schema upgrades. | Q02/Q05/Q11/Q45/Q49/Q50; no fake provider execution or historical backfill. |
| I2 — isolated tools and effects | Private multi-mount workspace, process supervisor, registry, scope/capability enforcement, receipts and output. | Q07–Q10/Q27/Q38–Q43; actual sandbox/process and crash tests. |
| I3 — native loop and inference | Working plan/context bridge, direct inference adapter, resource ledger, local repair, compaction and result claim. | Q01/Q03/Q09/Q21–Q25/Q41 with deterministic tests then admitted live provider. |
| I4 — continuity and Human updates | Complete state machines, R1–R7, checkpoint reconstruction, pause/stop/cancel, receipts and event controls. | Q12–Q30/Q36/Q45/Q46, fault frontier matrix. |
| I5 — vector assurance/integration and preview | Extend current owners to exact vector observation/Completion/Verification/Candidate/authorization/convergence/commit, isolated preview. | Q04/Q31–Q37/Q44 plus partial integration/DB restart. |
| I6 — comparison, acceptance and default cutover | Engineering acceptance surface, paired benchmark, legacy compatibility, rollback rehearsal, Human proof. | Q47–Q50, §7 benchmark, signed/recorded Human decision and two successful native acceptance cycles before default legacy removal. |

These stages are engineering checkpoints within one large mission. They do not turn each tool/model Step into a PWU or require Human approval after every stage. Only material authority changes, explicitly bounded real-provider spend and final product acceptance remain Human gates. Implementation may build independent modules in parallel only when separately authorized by the active agent-work instructions; this document does not require sub-agent delegation.

Keep existing v1 tests for synchronous dispatch, immutable observations, completed-work salvage, Candidate authorization and Runtime Commit. Add native test files under the repository's current `tests/` and integration conventions. Required suites must run against actual PostgreSQL, not a substitute SQLite interpretation of locks/constraints. Report migrations executed only in isolated test/acceptance environments and preserve the existing runtime until cutover conditions pass.

## 9. Human acceptance environment and script

Provide a dedicated acceptance profile with retained PostgreSQL and executor storage, independent API/coordinator/worker/tool-host processes, admitted real inference credentials outside code containers, exact source fixtures, independent Verification and preview/inspection adapter. Do not modify or delete current Work-to-Delivery acceptance data. Include an engineering control surface using existing product surfaces where possible; no final UX redesign is required.

Human must be able to:

1. Open the acceptance URL and inspect the admitted meaningful PWU: outcome, constraints, repository scope, exact model/resource allowance and source basis. Start production with durable acknowledgment.
2. Observe meaningful phases, actual tool actions, test activity and waiting reasons; inspect logs/artifacts without reading raw provider hidden reasoning.
3. Pause during active work. See PAUSE_REQUESTED/PAUSING until the barrier is actually safe, then PAUSED with retained work. Resume and confirm continuity.
4. Close/reopen the browser. See the same PWU and execution history with no resent mission or duplicate Attempt.
5. Trigger one labelled controlled worker interruption using an engineering control. See ownership/reconciliation, preserved artifacts and residual-work continuation. Human must not edit DB rows, kill arbitrary host processes manually or reconstruct Git changes.
6. Submit a factual clarification and then a material constraint/correction. Inspect applied/deferred/superseded receipt and any successor lineage. Submit an unrelated Motive and confirm it is not silently injected into active authority.
7. Inspect a two-repository result and independent cross-repository Verification, including a rehearsed partial integration/forward recovery demonstration in the fixture profile. Whole success must remain withheld while partial.
8. Inspect exact Candidate artifacts and supported preview before authorizing integration. Authorization names exact manifest/targets; preview state is visibly distinct from trust.
9. Observe Runtime Commit/Delivery after full convergence; accept the exact delivery or request changes. Request-changes creates governed refinement; neither choice overwrites old artifacts/evidence.
10. Inspect final lineage, timing, resource usage including unknowns, retained failure/recovery records and actual repository outputs. Confirm the ordinary recovery did not require technical micromanagement.

The acceptance report records Human decision, timestamp, exact code/profile/PWU/manifest IDs, acceptance observations, defects and requested changes. If Human has not performed/recorded this decision, report **HUMAN_ACCEPTANCE_PENDING**. Never infer acceptance from successful browser automation, lack of response or passing tests.

## 10. Required implementation completion report

Include code revision and changes; module/contract/schema versions; commands and environment for deterministic validation; every Q case status with exact evidence; live-provider bindings and explicit spend authority; all continuity trial results; phase-level performance; negative security/assurance tests; migration/rollback rehearsal; acceptance environment URLs/IDs; Human decision status; unresolved risks and recovery-promise limits. Separate failures, unsupported/deferred capabilities and measurement gaps from PASS.

Do not claim feature completion if native code merely delegates tools to Codex, if restart means resending the original mission, if multiple repositories are flattened to a scalar, or if manual hidden repair produced the acceptance result. Correct negative outcomes—blocked unsafe retry, denied unapproved profile, rejected stale PASS—are expected proof of the architecture.

## 11. Mission coverage and closure checklist

Every numbered Blueprint mission concern maps to the following implementation specification; this is not a claim that implementation is complete.

| Mission sections | Specification coverage |
|---|---|
| 0–3 required inputs, goal, invariants, D1–D7 | Main preamble and A–D; approved directions distinguished from proposed closure defaults. |
| 4–8 objects, PWU, Session, Attempt, Steps/effects | Main E/F; lifecycle L1–L3/L6. |
| 9 agent loop | Main G and L6; Q01/Q03/Q09. |
| 10–14 workspace, topology, tools, processes, credentials | Main H–J/O/Y; lifecycle L5–L7. |
| 15–17 context, compaction, checkpoints | Main K/L/AC; lifecycle L9/L12; Q21/Q24. |
| 18–21 control, fencing, intervention, Human authority | Main M–P; lifecycle L4/L5/L10/L13. |
| 22–24 provider, failures, resource accounting | Main Q/R/Z; lifecycle L8/L11. |
| 25–29 evidence, Guardian, preview, multi-repo integration, Passport | Main S–U/X; Q31–Q37/Q44. |
| 30–32 performance, event spine, retention | Main V/W/AC; lifecycle L7; Q42/Q45–Q48. |
| 33–35 migration, modules, persistence | Main AA–AC; §8 and Q49/Q50. |
| 36–39 machines, APIs, security, fault model | Lifecycle L1–L13; main Y/Z; deterministic matrix. |
| 40–41 qualification and Human acceptance | This full plan; main AD/AE. |
| 42–46 non-goals, A–AH deliverables, closure, documentation-only scope, final report | Main C/AF/AH; all three documents and final Human report. |

Qualification package assessment:
**IMPLEMENTATION_COMPLETE / TECHNICALLY_QUALIFIED / CONTINUITY_QUALIFIED /
HUMAN_ACCEPTANCE_DEFERRED_BY_HUMAN_GOVERNANCE / TECHNICAL_PHASE_CLOSED**.
Historical failures remain evidence. Human Product Acceptance is a later Human
action and is not asserted here.
