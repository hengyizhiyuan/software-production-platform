# Phase B — Assurance, Human Authority, Delivery and Source Continuity Audit

Date: 2026-10-09 (Asia/Shanghai). This is a read-only code/contract/retained-evidence audit and a support note for the parent Core Production Convergence report. No tests, qualification scripts, model calls, runtime operations, database queries, new Works or deployments were executed by this sub-audit. No existing implementation, decision or evidence was changed. This note does not close N1 or qualify current main.

## 1. Exact identities and evidence vocabulary

| Tag | Exact audited revision | Local read source |
| --- | --- | --- |
| M | Watt authoritative main `3c367be19d7663b5b9764347b45e6ae355c28e7d` | `D:\hy\core-production-audit\watt` |
| N | Watt N1 HEAD `5fd2579f8ab67db12f6ea122048613184276175f`; latest recovery application commit `9b3ca2f0b3e298a64ba345229c5856e22be931e5` | `C:\Users\yuchunbo\.codex\worktrees\governed-context-convergence\software-production-platform` |
| GM | Guardian authoritative main `cda2e744ee9027a223a4173faeb9c28829b99a71` | Git object at `D:\hy\architecture-invariant-worktrees\guardian`; local doc HEAD `13a6612b75b3fa5c1767d837d31177e6c48cdb5b` is ancestor main and has identical src/tests |
| GN | Guardian N1 owner code `7cdd58540b59767d9a68a5d16038c06f89059a5d` | `D:\hy\guardian-governed-obligations` |

GM src/tests also match former main `27bf5691e30104bf9a460df29a6f7dd4fb884a30`. GN is not Guardian main. N's GOF receipt identifies GN as its isolated owner overlay. Parent's separate read-only ECS archive comparison confirmed all five overlay Guardian Python files exactly match GN, and all 256 isolated Watt Python files match `84d16b1f98ee124a4a7fb11761c821e25223ad24`. A previous aggregate hash-order discrepancy is not a source mismatch. Production Guardian's five-file source matches GM/27bf569. Older N1 `0d483535...` records mounted owner source hashes, not a recoverable Guardian Git revision; it cannot be relabeled GN.

Code references below use tag + repository-relative file + one-based line. The table resolves exact revision and absolute root. Historical evidence is read from retained N1 files; its original A/B grades remain unchanged.

- E1: retained actual runtime/Owner-record facts or read-only identity, restricted to recorded time and IDs. This audit reads snapshots/receipts; it does not reconfirm the remote database. A report-only uncorroborated narrative remains E4.
- E2: historical exact-source tests/fixture integration. Model-stub and live-model evidence remain distinct.
- E3: exact-revision code/contract/callpath.
- E4: architecture statement or uncorroborated narrative.
- UNKNOWN: necessary historical fact/qualification missing.

Qualification names: PROVEN_SCOPED, IMPLEMENTED_UNQUALIFIED, DEFECT_CONFIRMED, CAPABILITY_GAP, UNKNOWN, DEFERRED. Causality separately: PROVEN, CONFIRMED_EDGE, HYPOTHESIS, UNKNOWN. A code edge does not prove historical causality. No item is marked DEFERRED without formal deferral.

## 2. Findings

1. Existing Candidate sealing, Human authorization, Integration CAS, trusted Runtime Commit, exact Manifest acceptance, durable Product source promotion and successor source materialization should be retained. Their existence does not qualify current N1 as a full loop or require a second coordinator.
2. Original G1 false PASS has a retained cause: mandatory identifiers became an empty required_markers tuple, making `all(...)` vacuously true. New G1 has scoped old-image content PASS and remains at real Human gates.
3. Main lacks N's static post-admission HTML materialization and governed_obligations module. GN's strict owner evidence profile is not in Guardian main. New GOF is branch-only and unqualified end-to-end.
4. New IR Constraint results have no Fact ID, but ECF still reads `check["fact_id"]`. GN continuous evidence only understands semantic-fact references. This is a confirmed mixed-evidence contract mismatch.
5. N Native evidence source_revision is the input baseline; GN compares it to the output Candidate revision. A normal changed Candidate can be incorrectly blocked. Tests align these fields synthetically.
6. Main Guardian independently observes HTTP/API/link effects, but accepts protected COVERED projection without resolving the referenced owner record. GN adds exact record validation; a working live full-chain strict contract remains unqualified.
7. Several natural-text Owner routes still depend on English words. Protocol enums, exact identity checks and typed capability gates are legitimate determinism; static expression recognition that substitutes for semantic obligation judgment is a separate risk, not proof against every finite contract.

## 3. Boundary audit

### 3.1 Accepted Work/Task → Verification

Upstream authority is accepted Work Reality, Source baseline, Task/PWU and CompletionContract, distinct from model candidate checks. M `application/verification.py:157` (`verify_obligation`) obtains exact produced basis, requires obligation membership (`171`), derives idempotent record ID (`175`), and sends Fact refs, Task/ECF fingerprint, proposed commit/tree and contract (`193`). It checks authoritative Git ref before/after provider (`221`), exact returned obligation/commit/tree (`237`), and current basis again during persistence (`248`). `evaluate_admissibility:314`/`368` requires all admitted obligations and no unresolved join. These are lawful deterministic identity/evidence protections.

M `providers/repository_code_verifier.py:80` checks admitted code contract and exact scope/diff. Semantic Fact IDs are recorded but do not obtain N's generic static materialization. Protected-context checks at `98` require a present supporting consumer; missing/unsupported consumer may be skipped there. M `verification.py:763` then projects missing protected checks UNVERIFIED, rather than automatically COVERED. This is a partial consumption CAPABILITY_GAP (E3), not proof of automatic unsafe whole-lifecycle PASS.

N `repository_code_verifier.py:109` consumes CompletionContract fulfillment bindings and `148` revalidates them against admitted Work/IR. Fact checks are materialized at `178`; Constraint results append at `215`; all results must pass (`222`); absent protected consumer fails closed (`226`); current ECF freshness (`234`) and exact protected coverage (`252`) are required; exceptions return UNKNOWN (`257`). Overall IMPLEMENTED_UNQUALIFIED, with §4.1 DEFECT_CONFIRMED. No real GOF G0/G4 verified Candidate proves the seam.

### 3.2 Human identifiers → Contract → exact content

Retained original G1: Work `ae8530f0-1f28-55f7-aea6-e79b13c7fabd`, PWU `12e183d1-581a-4d70-bd01-e0edbc1aac4b`, Candidate `7d410081-4319-5529-a12e-ce844f9d9ac2`, Verification `b10a6b32-faad-5982-8b29-cdd89940c116`. Required markers were [] while three mandatory IDs were absent. M `repository_markdown_verifier.py:201` checks `all(marker.casefold() in normalized for marker in required_markers)`. Cause is upstream missing obligations plus supplied-obligation-only verification; it did not consume and disregard the three obligations. E1/E3, PROVEN for that case.

N `application/semantic_steps.py:68` extracts literal UUID/SHA40 from qualifying exact Human input into admitted objective/verification. N `application/steering_production.py:504`/`520` builds document Contract and calls `_exact_document_lineage_markers:557` from admitted wording, without invented IDs. N `repository_markdown_verifier.py:89` matches semantic refs and Human explicit section scope/order; `234` checks exact UUID/SHA boundaries. The mechanical token check is lawful.

Semantic coverage is narrower: `semantic_steps.py:72` needs English identifier plus literal/exact; `steering_production.py:567` needs English exact/lineage/identifier and appear/include/contain/visible. An equivalent Chinese requirement is a prospective helper-trigger counterexample, not an executed failed Work. Broader semantic classification is IMPLEMENTED_UNQUALIFIED / HYPOTHESIS.
### 3.3 Protected Context → current evidence / future Gate / continuous prohibition

ECF protected items identify source/ref/revision, authority/content digest, package fingerprint and semantic identity. A derived binding must preserve accepted authority. N `domain/governed_obligation.py:39` is frozen and references Fact or original IR Constraint, Work revision, provenance, source, Owner/phase/evidence/Gate. `bind_admitted_fact:91` checks original ref/provenance; `bind_admitted_constraint:122` checks exact admitted IR clause, Human statement/provenance and Work constraints. A Constraint route intentionally has no fabricated Fact ID.

N `application/governed_obligations.py:35` routes typed permission/constraint effects to existing execution/delivery/Git scope gates. `materialize_continuous_gates:65` uses accepted IR, not a global Subject Alias table; `validate_continuous_gates:108` reconstructs exact identities. N `work.py:1790`/`1989`/`2031` carries derived routes in existing CompletionContract construction. Current content/scope stays with Verification, future seal with Candidate, and Human Integration/Acceptance with existing Human lifecycle. `assert_delivery_effect_permitted:137` re-reads current Work/IR before effect; N `cloud_delivery.py:378`/`562` and `github_delivery.py:263`/`344` call it at authorization and execution. This reuses Owners instead of creating parallel lifecycle orchestration.

`evaluate_constraint_routes:169` checks Native Attempt exact Work revision, Source Vector, original IR Constraint reference, source revision, write scope/forbidden paths and actual grants (`180–201`). Emitted evidence meaning (`216`) is **current attempt and scoped verification only**. It cannot establish absence of historical illegal effects; missing ordinary logs cannot prove complete audit coverage.

`evaluate_candidate_handoffs:275` can represent a legitimately recognized seal requirement as CURRENT_VERIFIED_FUTURE_GATE_PENDING only with accepted Human/IR acceptance requirement, exact target and passed prerequisites. Managed ECF PENDING_CANDIDATE_GATE must later pass actual Candidate seal verification in GN. This creates no Human authorization; a retained constraint string alone is not a gate proof.

N `providers/managed_context_fulfillment.py:91–151` still uses English effect/prohibition/candidate/reviewable/change/verification wording to select evidence/phase; `governed_obligations.py:296`/`324` recognizes candidate text. These are semantic routes rather than only protocol enums. An equivalent unlisted expression may fail closed or be misclassified. No new variant was executed and this risk is not asserted as historical preflight root.

Status: retain typed Fact/Constraint identity and present permission protection (E3/E2 scoped). Full mixed Constraint→ECF→Guardian is DEFECT_CONFIRMED at the edges in §4 and IMPLEMENTED_UNQUALIFIED end-to-end. Broader semantic route correctness remains unqualified/UNKNOWN.

### 3.4 Candidate check plan → validation / bounded Self-Refine

N `providers/static_html_semantic_verifier.py:460` (`StaticHTMLPlanRepair`) takes exact original Fact/Work revision/relation/value/scope/qualifiers/authority/provenance and source target. Existing model runtime generates a candidate plan (`491`), at most two attempts with feedback; runtime closes (`512`); exact target, observed quote, method and original expected values are checked (`519–539`). Repair affects derived verification representation, not admitted Fact or Human authority; arbitrary unlimited test-program generation is not used.

`_materialize_fact_check:543` and `verify_static_html_semantic_facts:682` preserve original ref/Work/value/scope/qualifier/provenance trace and execute exact Candidate/Git HTML checking. Unsupported mapping has explicit UNVERIFIABLE_CURRENT (`631`). Legal plan plus wrong content remains FAIL. N `protected_context_verifier.py:119` requires each protected identity and exact Candidate witness; feedback is bounded (`140`), and prior non-SATISFIED judgments cannot turn SATISFIED during representation repair (`148`).

Method enums and exact value/order/target checks are lawful deterministic contracts. Source-witness guard (`526`) relies on finite h1/paragraph/ordered-list words and listed Chinese equivalents; page assertion regex (`600`) handles a narrow mixed sentence form, with fallback only for specific relation/value forms (`613`). These are identified generalization limits, not evidence for more aliases or a proven historical cause.

N `tests/test_n1_static_html_semantics.py` defines unlisted file (`771`), paragraph qualifier (`799`), ordered assertion (`819`), explicit unsupported failure (`858`), expression variation (`929`), plan repair (`957`) and exhaustion (`1014`). Plan repair uses predefined responses, first wrong target then correct target. Historical E2 shows fixture candidate-validation mechanics, not live semantic generalization. GOF records 67 exact-source Watt directed tests and 8 GN tests, but no real GOF G0/G3/G4 verified Candidate. Overall IMPLEMENTED_UNQUALIFIED for this live full boundary.

### 3.5 Sealed Candidate → independent Guardian

Actual normal order is produced artifact → technical Verification/admissibility → seal → review/preview → Guardian → Human integration authorization. M `application/work.py:2751` runs checks, `2785` seals, `2799` prepares review, `2802` waits for authorization. Guardian is not incorrectly claimed to precede seal.

M `application/guardian_assurance.py:102` requires exact READY preview/fingerprint/revision/tree (`111`) and PWU/Task/verification/current-plan identity (`138`). Requests are separate per ECF package (`203`), with acceptance PENDING/delivery NOT_AUTHORIZED (`233`). If no admitted effects, it derives HTTP routes from admitted HTML paths (`173`), which proves observed route properties rather than all intent; unsupported effects block (`193`). `passed:294` rechecks exact READY preview and stored Guardian result (`308`): cached Watt PASS alone is insufficient.

GM `runtime.py:100` preserves immutable request/result identity, independently observes required HTTP/API/link effects (`116`, `_observe:219`) and checks served Candidate source (`_fetch:188`). Protected-context path at `138` accepts caller COVERED directly or an independently satisfied mapped effect. It cannot resolve arbitrary cited Verification/Native/Candidate records. This is CAPABILITY_GAP for strict protected-governance evidence, while independent HTTP assurance remains useful. It does not prove all GM PASS invalid or all M UNVERIFIED automatically pass.

GN `contracts/software_assurance.py:88` adds opt-in governed-obligation-v1, exact authority/digest (`135`), still PENDING/NOT_AUTHORIZED (`141`). GN `runtime.py:180` resolves persisted Verification; requires PASS/exact Candidate commit/tree (`199`), exact package/identity/unique projection (`205–218`), and actual sealed Candidate for pending seal (`223`). `256` checks Native continuous permission evidence. Legacy compatibility stays explicit; finite version/method contracts are not expression aliases.

N `guardian_assurance.py:83` connects GN's resolver; `_resolve_owner_evidence:86` reads exact RuntimeStore Verification/Candidate and NativeExecutionStore records. GN evaluates their identity/phase/evidence rather than only Watt COVERED. The callback does not create missing historical authority or audit coverage. Strict profile is selected only for MANAGED_PRODUCT_WEB_UI (`259`); other paths remain legacy-v1. §4's shape/version faults prevent a complete working-contract claim.

GN `tests/test_governed_obligation_evidence.py:58` rejects missing/stale coverage, `74` checks exact seal, `93` rejects forbidden grant. These are fixtures. N/GN actual production→Guardian strict PASS remains IMPLEMENTED_UNQUALIFIED; GN is not authoritative main.
### 3.6 Candidate/Guardian → exact Human Integration Authorization

M `application/governance.py:79` seals stable exact content/basis. `_require_current_eligible_basis:372` requires SATISFIED PWU, produced completion, ADMISSIBLE/current pointer and exact plan/source/attempt generation, observed produced Git facts, required-obligation fingerprint and all exact PASS records (`461`). `authorize_candidate:159` requires SEALED (`174`), exact fingerprint (`175`) and repository/ref/source/proposed-revision scope (`179`), then immutable Human actor/authorization/scope (`213`). Upstream omitted obligations are not repaired or invented by sealing.

M `work.py:3538` handles exact Candidate authorization attention, checks readiness (`3549`) and authorization guard (`3553`). M `bootstrap.py:394` creates Guardian client, requires exact READY functional preview/Guardian PASS (`400`) and configures authorization/review guards (`412`). M `api/authority.py:59`/`143` derives authenticated actor; resource OWNER membership is checked (`149`) and body identity replaced (`175`). This is existing single-owner authority, not general enterprise IAM. Existing authenticated-authority test definitions (`tests/integration/test_authenticated_authority.py:17`, `47`, `67`) were not run.

G1/G3 zero Human authorizations are truthful waiting boundaries. Architecture approval does not authorize exact Candidate Integration/Manifest Acceptance. Present N1 downstream result remains unqualified/pending, not a permission to invent authority.

### 3.7 Human Authorization → Integration → Runtime Commit

M `application/integration.py:67` persists PREPARED exact intent before effect (`71`), idempotently returns CONVERGED (`80`), represents Git-success/SQL-uncertainty (`88`), blocks changed baseline (`102`), and uses actual Git CAS/readback (`114`). `_require_current_authorized_basis:273` checks SEALED exact fingerprint (`279`/`283`), immutable Human authorization/source/ref/scope (`288`), current pointer/PWU/plan/proposed/admissible basis (`312`).

M `application/runtime_commit.py:296` revalidates Candidate, authorization, pointer, completion and exact PASS records. Human authority (`458`), actual converged integration (`488`) and all exact Verification (`586`) are required; trusted commit/pointer admission is atomic (`159`). Normal Work uses this sequence (`work.py:2805`/`2817`). These services own integration/runtime identity, not a duplicate Guardian implementation. Configured normal Work supplies the preceding Guardian guard; no independently exposed bypass route is established by this audit.

The present N1 G1/G3 cases have no such effects. Existing structural identity/CAS mechanisms should be retained. Their code is E3; fixture definitions without retained execution receipt do not prove current end-to-end. Scoped actual older success is preserved in §5.1.

### 3.8 Runtime Commit → exact Manifest → separate Human Acceptance

M `application/delivery.py:470` (`publish`) requires trusted/authorized basis (`474`), exact optional Candidate fingerprint/revision (`476`), immutable artifact bytes/SHA (`502`), Work revision/runtime/source/Verification IDs (`505`), and stable Manifest fingerprint (`516`). A Candidate is not an uncreated future Manifest.

`decide:620` requires exact displayed fingerprint (`624`) and immutable prior decision (`629`). `_record_acceptance:642` locks Manifest and current Work/runtime cycle (`646–656`), requires current Guardian PASS for software when configured (`658`) and exact served Candidate/runtime probe (`662–674`), then records explicit Human Acceptance (`675`) before source promotion intent (`684`). Integration Authorization and Delivery Acceptance remain distinct; neither is model-generated.

The retained G1 exact review permits only its future Human-selected action sequence; no Human records were created here. Its eventual exact Manifest outcome is UNKNOWN, not preaccepted. M GitHub `_push_locked:321` blocks unsupported attributed release; N adds current publish prohibition (`344`). N cloud authorization/execution add current deploy prohibition (`378`/`562`). These are code protections, not newly qualified production releases.

### 3.9 Accepted Delivery → Product accepted Source → subsequent Work

M `application/product_managed_source.py:239` prepares promotion only on exact current Product accepted version/revision/tree (`247`), explicit Human ACCEPT (`251`) and matching Work source (`253`); conflicting promotion blocks (`256`); durable intent precedes external ref mutation (`262`). `reconcile_promotion:274` checks immutable Acceptance and Runtime Commit identities/revision/tree (`286–294`), exact expected source CAS (`295`), applicable Assurance (`298`), and actual provider target/tree (`300`). Source version records bind Candidate/Work/Acceptance/Human authority (`305`); accepted source + COMPLETED intent advance atomically (`311`). Failures preserve categorized BLOCKED intent (`320`). M delivery `_require_promotion_assurance:692` checks actual Guardian PASS and unchanged exact result refs when required.

`prepare_work:150` reuses an exact existing Work basis, blocks pending promotion (`159`), materializes persisted accepted revision and exact tree (`173–175`), isolates Work branch/source version (`201`) and rechecks Product version before insert (`214`). It does not substitute remote latest HEAD or G1 document Candidate for corresponding Product V1.

N1 G2 receipt records no version>0 in its isolated qualification DB. That is scoped to the required Product/test population and does **not** erase earlier accepted-source qualifications in other Products/databases. §5.1 preserves the actual Oct6 Acceptance→V1→real subsequent Work→Acceptance→V2/Git-SQL continuity. M `tests/integration/test_product_managed_source_gitea.py:320`, `407`, `462` additionally define restart/head isolation, brownfield successor and durable promotion replay; `_run_and_accept:277` supplies scripted Human decisions, so tests alone are not actual Human decisions. None was run here.

M `docs/evidence/first-human-validated-end-to-end-production-loop.md:54–58` says its 2026-09-17 disposable retest retained READY Work but no Delivery Acceptance row. Preserve that specific narrative boundary; do not use it to erase the separate Oct6 durable acceptance evidence or to qualify N1 G2.

## 4. Exact defects and semantic risks

### 4.1 IR Constraint result → ECF/GN Fact-shaped consumer

N `repository_code_verifier.py:215–221` appends Constraint route results into static_html_semantic_checks. N `application/governed_obligations.py:202–218` emits constraint_item_id/clause_id, source_kind IR_CONSTRAINT, and passed continuous disposition GATED_CONTINUOUS, with no fact_id. N `providers/managed_context_fulfillment.py:79–85` consumes those checks and indexes check["fact_id"]. KeyError is caught by verifier `257–263` and becomes UNKNOWN; other managed comprehensions (`150`/`165`) also assume Fact-shaped checks. GN `runtime.py:262–268` requires semantic-fact refs and fact_id matching and therefore cannot consume the new Constraint identity as-is.

E3 / DEFECT_CONFIRMED / CONFIRMED_EDGE. This is not the proven cause of historical G0 preflight failure, which preceded Verification. `tests/test_governed_obligation_fulfillment.py:253–312` manually supplies old Fact-shaped dictionaries; latest 7 tests/actual IR route probe validate route construction and negative permission checks, not actual Constraint→ECF→GN. A fabricated Fact ID would not be a lawful correction; this is an existing Owner evidence-contract seam.

### 4.2 Input baseline role → Candidate output role comparison

N `guardian_assurance.py:117` resolves Native source_revision from Source Vector source_commit_oid (input baseline). N `:281` request source_revision is preview session.repository_revision (output Candidate). GN `runtime.py:284` requires them equal. A lawful changed Candidate normally has different identities. Both roles require exact binding; replacing them with one identical field incorrectly rejects the valid output.

E3 / DEFECT_CONFIRMED / CONFIRMED_EDGE. GN `tests/test_governed_obligation_evidence.py:113–115` sets Native source_revision to req.source_revision, masking the real adapter distinction. No live GOF verified Candidate exercised it; it is not historical workspace root.

### 4.3 Open routes versus lawful deterministic contracts

| Edge | Legitimate determinism | Unqualified semantic selection |
| --- | --- | --- |
| N semantic_steps:72 / steering_production:567 | Exact UUID/SHA syntax/content | English prerequisite decides whether literal Human identifiers create obligations |
| N managed_context_fulfillment:91–151 | Exact grants/diff/source identity | English effect/prohibition/candidate/change/verification wording selects Owner/evidence/phase |
| N governed_obligations:296/324 | Exact IR acceptance_required / seal identity | candidate word predicate decides future-seal handling |
| N static_html_semantic_verifier:526/600 | Existing method contract/value/order/scope | Fixed witness vocabulary/narrow mixed assertion pattern may exclude equivalent expression |
| N intent_realization:85–149 | Unique Product Source authority/revision/tree/provenance | Listed accepted-Product-source phrases at92/115 do not prove arbitrary natural-reference coverage |

Last helper accepts unique actual Product Source record (`100–128`), emits REPOSITORY_OBSERVED (`133`), and fails/clarifies missing or ambiguous source (`140`). G3 scoped positive is retained. An unlisted Chinese phrase is a prospective helper-trigger risk; existing model may still supply a valid observed reference. No new failed Work is claimed. Code E3; broader ability IMPLEMENTED_UNQUALIFIED and variant causality HYPOTHESIS/UNKNOWN. Finite protocol/permission/checker enums are not violations merely because finite; the concern is replacing necessary open semantic judgment with static expression branches.
## 5. Retained actual qualifications and limits

### 5.1 Oct6 accepted-source continuity is PROVEN_SCOPED

M retained `docs/evidence/p0-p1-system-closure-20261006.json` records qualification at `2026-10-06T01:48:09.363623+08:00`, exact application source `52880f1eb0075a6ed3218abae672de08a2d0434e`, tree `24d2e506fbf9bca7573a5338be8d7dff5b864894`, migration `20261005_68`, Guardian `27bf5691e30104bf9a460df29a6f7dd4fb884a30`, ECF `8b2c7b68d6e1752c32050c2042e168b654d8139f`. Its scope is the current single-ECS default static path, not blanket full-system, HA or new-host recovery qualification. Present audit reads this retained receipt; it creates no Human decision or DB requery.

Dedicated Product `a9b9634f-f46a-4452-82d1-d2d4363bebc3` has actual source chain:

- Single-PWU Work `b11e4aac-001b-5c1f-9744-f27fcc93d1d1` → Candidate `c68fc33e-154e-50f9-be15-17b96396c574` → Acceptance `ec23a52d-a6a3-46fd-a63f-7dbe0feabc56` → Product Source V1 `d4ad65db95fa1bb3ad7ec951ea844fd4939c2a3d`, tree `ab4a85cf36ffd2f902c1e85dbc89f8970c5e21e8`, version record `558b5570-dee8-5326-8a38-1c6ba3ebcf32`.
- Real Multi-PWU Work `3ee622b5-b816-5679-afdc-e5de51cd2702` roots consumed that exact accepted V1 → Candidate `13c231ba-bc32-5f91-b391-aeeb930c91c4` → Acceptance `f1127996-a72c-45cf-9b94-ba8839ecf3a2` → Source V2 `b4280990d55ac9da36eaa0dd9644006df7e8762e`, tree `330eb480e850ba9e0a57506db084d9a94ac59562`, version record `8a3b313e-de53-54ee-84e3-c8c79b7cd38b`.
- Durable promotion intent `622e1fc7-c096-5284-b045-aaf0affc12f1` was BLOCKED on PROVIDER_UNAVAILABLE, then COMPLETED for the same Acceptance/target/expected V1. Three exact retries retain the same Acceptance ID. Remote accepted Git revision/tree equals SQL (`git_sql_equal=true`). Three controlled process-cut tests are separate E2 evidence; they do not replace the actual E1 Source chain.

This is PROVEN_SCOPED accepted V1→real subsequent Multi-PWU→accepted V2 continuity. It remains valid historical scope even while N1 G2 lacks its own required corresponding accepted Product V1. No code-existence argument or newer N1 failure erases this retained actual pass; it also does not prove current main universal semantic/GOF conformance.

The receipt's workspace-continuity branch is separately bounded: Work `c3819aa6-f464-59c3-a3dd-2949f038920a` had actual browser submission and Worker execution; execution `689db78c-6ec6-45ff-8cf7-be743cbb1a78` later FAILED with no Candidate after bounded diagnostic rounds/no source modification. Original A Work lineage remained unchanged. This qualifies admission/actual dispatch and preservation only, not successful B software production. Earlier authorization_pending snapshots are observation-time states and must not override later source_promotion Acceptance facts.

### 5.2 Older N1 scoped content/source qualifications

N `docs/evidence/governed-production-context-convergence-v1/qualification-report-0d48353-20261008.md` captured **2026-10-08 11:50 UTC**, application `0d4835353dbdb38abd6abfc19127b84eb5544475`, image `sha256:64289d0a086ecf03efb2dae24ab036bd83906905e00fd71fa30fc51feb160709`, isolated DB `spg_n1_qualification_20261008`, Gitea `watt-n1-gitea-20261008`. These are not M/N latest code identities.

| Case | Retained IDs/results | Real limit |
| --- | --- | --- |
| G1 | Work `044f0268-f9cc-5663-a145-ea4d30b8e5bb`, PWU `6f7c9329-8e9f-4ccd-b69b-4511529bac05`, Candidate `695cc730-849a-5dce-88da-c62c19c9f6b8`, fingerprint `481e481d6f68936f149541f4c8a4b3e5551a4fec318de88deca4b73d92ae7ff7`, Verification `e0b16874-f96f-5e38-964b-73301e4bc3c8` PASS; file `docs/n1-g1-lineage.md` SHA256 `925a7ea9e6b0125c59b3537c19e50073d44e42c60d1e72d2765540e07aa9fbce`; commit `bda800eafa1cf720d6c0f9ade31170608e9d2912`, tree `178dc6e1df7ca50122d6b003c8ddac4f349e01ce` | PROVEN_SCOPED four marker + section check; Guardian NOT_STARTED/required=false; no authorization/integration/Runtime Commit/Manifest/Acceptance. Missing-ID/reversed-section new-Candidate regressions are E2, not current live qualification |
| G3 | Product `d1b0ec92-9d8c-470d-bf20-624680129fb3`, Work `e50a9566-155c-5843-93fd-9b7ec800df7d`, run `9fa07cdd-a8e9-4a63-a280-b3345f4de438`; V0 `c37c2e366650935dde62ef48a6b54a621337a27c`, ref `product-source:d1b0ec92-9d8c-470d-bf20-624680129fb3:0`; Candidate `3d612a3e-bac9-54c9-8a3f-078a981c3362`; PATH_SCOPE `81fd3068-58c0-54d2-9263-78eaab267088` and Git diff `004230ff-36db-55f2-a96f-c9e2db574f46` PASS | PROVEN_SCOPED natural source/diff old-image path; no Human authorization/full Work PASS; must not regress or claim universal natural-source coverage |
| G4 | Work `c616ab6b-d985-5b35-a2c4-47d9b79ad4e7`, PWU `26d38fa0-0f11-41a8-8c87-52f100a4f388`, ordered Fact `7b610ed7-bb57-54fb-88cc-4a4b10bdc6cb`; F01–F14 unchanged across Work/Task/Contract and exact list check PASS; PATH_SCOPE `2c650693-cbe6-50b4-a0a5-ab6019a57eff` FAIL | PROVEN_SCOPED tuple/list preservation only; no sealed Candidate or all-Protected-Context proof. Fourteen tuple entries and nine original summary constraints are different representations, not cardinality loss proof |
| G0/G5 | Work `290e71df-bb46-5298-9a27-77e0091ba440`, Self-Refine event `37f0da00-7eb6-44cb-9a10-c0db46399e20` LOCAL_OBLIGATION_RECOVERED; effect `5bdf6dd0-802b-4c52-8352-6665de6ca1d0` later FAILED | Actual bounded local recovery; no Candidate/full completion. Not end-to-end recovery PASS |
| G6 | WIC exact-value stop before Work/runtime binding | Scoped truthful WIC stop; requested irreparable Context Assembly qualification remains missing |

### 5.3 GOF real failure and unbuilt source recovery

N `docs/evidence/governed-obligation-fulfillment-20261009/qualification-report.md` and raw receipts identify live application `84d16b1f98ee124a4a7fb11761c821e25223ad24`, image `watt-n1-gof:84d16b1`, digest `sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14`, GN overlay. Four isolated G0 trials retain zero Candidate/Verification; none is complete Work PASS.

Latest G0: Product `7e39eefc-5653-4ed7-90c9-c180479681e9`; Work `84d7f3a9-b90c-5341-a007-2661fc6399b3`; PWU `cb30547a-1556-4590-bef0-2c321621d395`; Attempt `e3addc05-7ee4-49f4-9043-c69b6466bcf8`; rejection event `879cdfb4-77e6-4837-a8af-875563dbb59b` at **2026-10-09 01:03:55.715306 UTC**. Only workspace unavailable was retained, without failed predicate/errno. Current mount visibility and successful replay do not establish past observation. Historical root stays UNKNOWN; no unsupported path/wait fix is claimed.

Latest recovery application `9b3ca2f0b3e298a64ba345229c5856e22be931e5` is not in that live image. `blocker-b-regression-receipt.json` binds Work revision `c8372b46-7701-5d8c-bed9-c2a07084f66d`, IR `82132598-0186-58a7-b35d-cf70c02ccda3`, five typed routes, 7 directed tests, negative missing-ref/forbidden-grant/wrong-revision/failed-scope/wrong-target. It says new_image_built=false, new_work_created=false, live_work_pass=false: E2 source-overlay and actual-IR probe, not live production PASS.

Report addendum `:12` withdraws the old assumption that absent prohibition Fact implies admission loss: original typed CONSTRAINT si-3/c7 legally retained prohibition/effects. Historical body `:89` still contains that superseded admission interpretation; treat it as dated audit input, not current root truth, and preserve it rather than rewrite history.

`original-scenarios-read-only.jsonl` preserves old G0/G3/G4 Work/source revisions, all with zero fulfillment bindings because pre-GOF. Counts respectively are Facts/constraints/protected obligations 6/7/8, 5/7/8 and 4/8/9. Counts identify snapshots, not completeness or retroactive qualification. Tracked task evidence and ECS `/data/watt/n1-qualification-20261008/gof-84d16b1/` plus `/data/watt/n1-qualification-20261008/gof-recovery-code/` are retained recovery locations; this sub-audit did not inspect/mutate those server paths.

## 6. Responsibility judgment and unresolved qualification

| Phase B category | Finding |
| --- | --- |
| Useful ability to retain | Exact Fact/Constraint provenance; immutable binding validation; exact Candidate/Git checkers; bounded plan repair; explicit UNVERIFIABLE; exact seal; typed current effect permits; existing Candidate/Human/Integration/Delivery/Product Source lifecycle |
| Belongs in existing Owners | Verification materialization, accepted IR→existing execution/delivery gate binding, ECF protected projection, minimal GN consumption of existing persistent Owner records. No need for a second coordinator is established |
| Confirmed mismatched seams | Fact-only ECF/GN consuming typed Constraint output; baseline/Candidate version-role conflation; main lacks strict governance evidence resolution. Semantic keyword route breadth is an unqualified risk, not automatically a proven failure |
| Still lacks required real qualification | Legal GOF G0/G4→verified Candidate→strict Guardian; mixed Constraint evidence round trip; changed Candidate Native/GN roles; non-prelisted live convergence; N1 corresponding accepted-V1 successor; recovery→resume→required completion boundary |

Future authorized verification should test the shared seams rather than repeat all G0–G6 now: actual IR Constraint→Contract→Verification→ECF→GN with negative missing evidence; changed Candidate baseline/output roles with wrong-version/tree rejection; non-prelisted equivalent expressions with bounded validation and wrong content/value/order/scope/authority/effect rejection; then one final exact-image legal G0. Human gates remain real decisions, not fixtures.

This is an audit input, not a new architecture/implementation plan. It does not alter N1 scope, budget, Closure Conditions or historical results. Existing exact governance and Oct6 scoped accepted-source continuity are preserved; old N1 content/source successes stay scoped; new GOF end-to-end is unqualified with confirmed consumer-contract defects and UNKNOWN preflight cause. Architecture Invariant Establishment is not Runtime Conformance Qualification.
## 7. Explicit eight-question evidence ledger

The question numbering follows the Phase B authorization attachment. Each answer is bounded by the exact revision tags in §1; tests mentioned without a retained execution result are definitions/E3, not newly established PASS.

### B1 — Accepted Work / Task / PWU → Verification (§3.1)

1. **Upstream authority:** admitted Work Reality revision with Fact/IR Constraint provenance, exact Source basis, Task contract and PWU CompletionContract.
2. **Actual consumer:** VerificationService reads produced basis/required obligation; provider reads VerificationRequest semantic refs, contract, Task/ECF projection and exact Candidate commit/tree, not the original Human chat again.
3. **Agreement:** source/plan/PWU/version/obligation membership is checked in M; semantic consumption is incomplete in M and broadened in N. N Constraint output shape fails the managed downstream contract (§4.1).
4. **Fact/constraint/decision protection:** exact admitted membership and current-basis revalidation protect identities; complete admitted obligations must pass before admissibility. They cannot protect requirements omitted upstream, and provider missing consumers require explicit UNVERIFIED/fail semantics. Future Human approval is not invented.
5. **Validation/feedback/convergence Owner:** Verification owns evidence admission and failure; N static provider owns bounded derived-plan repair. It does not own rewriting IRK authority or granting Human authorization.
6. **Evidence and promotion:** exact Git/provider checks generate evidence; VerificationService checks exact returned source/obligation and persists immutable result; VerificationService/admissibility determines technical admission. Model output alone cannot promote.
7. **Generalization:** deterministic scope/diff checks generalize inside their admitted contract; arbitrary Fact-to-check consumption in M is missing. N includes expression fixtures but lacks a successful current live full-chain proof and has a confirmed consumer edge.
8. **Support:** M verification.py:157/193/237/248/314/368; M repository_code_verifier.py:80/98; N verifier:109/148/215/222/257; retained G3 exact PATH_SCOPE/Git diff PASS and G4 scope FAIL (§5.2); N GOF fixture receipt67/actualIR7 are E2, no live GOF Candidate.

### B2 — Exact Human identifiers → Contract → content (§3.2)

1. **Upstream authority:** Human literal identifiers preserved in admitted Work objective/verification and referenced semantic Facts, not IDs invented for a test.
2. **Actual consumer:** steering document Contract emits required_markers/sections; markdown provider reads that tuple and exact Candidate Git blob.
3. **Agreement:** original G1 lost requirements before provider; empty tuple made PASS vacuous. N exact-token matching fixes supplied identifiers, but English classification trigger is not a general semantic guarantee.
4. **Protection:** N derives identifiers from admitted authority, checks nonempty qualifying requirements, exact token boundaries and section order; historical sealed Candidate remains unchanged. Missing IDs must fail a new Candidate. No Human decision is implied by content PASS.
5. **Owner:** existing semantic admission/IRK path retains Human identifiers, Steering builds Contract, markdown Verification validates content and gives failure. Owner-local repair may correct candidates/contracts within authority; it cannot alter the requested identifiers.
6. **Evidence/promotion:** immutable Candidate blob/parsed token+section evidence is generated by repository verifier; Verification admits exact-source record; Candidate sealing remains separate; Human Integration and Delivery remain separate.
7. **Generalization:** UUID/SHA mechanics apply to unseen token values. Detection of arbitrary equivalent natural requirements remains unqualified because English predicates gate extraction.
8. **Support:** M markdown_verifier:201 original empty-marker root plus persisted original IDs (§3.2); N semantic_steps:68/72, steering_production:504/557/567, markdown_verifier:89/234; test_n1_document_lineage_verification.py:30/81/94/115/136 fixture negatives; actual old-image new G1 IDs/fileSHA/PASS (§5.2).

### B3 — Protected obligation → current evidence / later Gate (§3.3)

1. **Upstream authority:** original Fact or typed IR Constraint with Human provenance, original Work revision/source identity, plus exact ECF protected item/package.
2. **Actual consumer:** CompletionContract carries frozen FulfillmentBinding; Native input references and grants/Git scope produce current evidence; ECF consumer projects protected coverage; Candidate/Delivery Gate consumes its own later lifecycle record.
3. **Agreement:** typed effect identity and original-constraint provenance are checked. N new Constraint results and Fact-only ECF/GN consumers disagree; legacy prose keyword routes do not establish universal phase/Owner equivalence.
4. **Protection:** bindings validate against unchanged authority; unresolved requirements fail closed; continuous effects denied at current authorization/execution gates; pending future seal must pass actual seal. No missing logs are treated as full historical audit and no pending Human decision becomes approved.
5. **Owner:** IRK/Engineering Semantic Truth owns accepted meaning; existing execution/delivery permission Owners enforce prohibitions; Verification owns current content/diff, Candidate owns seal, Human owns later authorization/acceptance. Self-Refine may repair derived representation, not those authorities.
6. **Evidence/promotion:** NativeExecutionStore supplies exact current grants/binding; Git verifier supplies exact scope/content; Candidate/Human services supply lifecycle records; GN verifies exact record consistency for strict profile. Current scoped evidence is not complete no-effect history.
7. **Generalization:** typed permission contracts support arbitrary original IDs/source revisions within known effects. Open semantic Owner/phase selection remains keyword-limited and mixed Constraint round trip is defective; no new live generality is proved.
8. **Support:** N domain/governed_obligation.py:39/91/122, application/governed_obligations.py:35/65/108/137/169/275, work.py:1790/1989/2031, managed_context_fulfillment.py:79/91/151; cloud/github authorization+execution calls (§3.3); actualIR five bindings/negative tests E2 and no new image/Work (§5.3).

### B4 — Candidate check plan → bounded repair → exact check (§3.4)

1. **Upstream authority:** exact admitted Fact relation/value/scope/qualifiers/provenance and target Candidate source, not model plan.
2. **Actual consumer:** StaticHTMLPlanRepair receives authoritative reference/value plus legal checker capabilities and exact source; derived plan is validated then consumed by deterministic HTML verifier.
3. **Agreement:** exact path/source quote/method/original expected values are checked. Plan does not become new Fact. Some vocabulary/regex limits can reject equivalent lawful plans; these are not demonstrated live roots.
4. **Protection:** no expected-value/authority rewriting, explicit unsupported result, per-Fact trace, actual mismatch remains FAIL. Protected witness repair cannot turn non-SATISFIED judgment into SATISFIED.
5. **Owner:** Verification provider owns candidate plan validation and feedback; existing model runtime supplies at most two candidate attempts, then returns truthful failure/UNVERIFIABLE. No global Refine coordinator or budget increase.
6. **Evidence/promotion:** model generates candidate representation; exact repository/HTML checker generates actual evidence; VerificationService admits technical result; later Candidate/Guardian/Human Owners retain their own decisions.
7. **Generalization:** fixture variants cover multiple unlisted forms; live model/effect equivalence is unqualified. Finite checker method set is legitimate, fixed wording as a semantic prerequisite is the actual limitation.
8. **Support:** N static_html_semantic_verifier.py:460/491/519/526/543/600/613/631/682; protected_context_verifier.py:119/140/148; test_n1_static_html_semantics.py:771/799/819/858/929/957/1014 uses fixture model responses; retained GOF67 E2, no real verified GOF Work.

### B5 — Sealed Candidate / preview / Verification → Guardian (§3.5)

1. **Upstream authority:** sealed exact Candidate and READY preview, exact Task/PWU/ECF packages, immutable PASS Verification and governed effect requirements; pending Human states stay pending.
2. **Actual consumer:** Watt adapter submits per-package AssuranceRequest; GM reads request and observes runtime effects. GN strict profile also resolves actual Verification/Candidate/Native records through exact ref callback.
3. **Agreement:** exact Candidate runtime and package identity are checked. GM trusts upstream COVERED for unmatched protected items. GN strict identity validation is stronger, but Constraint identity and baseline/output-version roles currently mismatch (§4).
4. **Protection:** independent stored result required; wrong/stale/unsealed/missing strict evidence blocks; acceptance=PENDING and delivery=NOT_AUTHORIZED enforced. Main's independent HTTP checks are retained; broad protected evidence resolution cannot be claimed from a caller flag.
5. **Owner:** Guardian independently owns Assurance Findings/gate. Watt adapter projects Owner facts; it cannot confer Guardian PASS. Model/Executor cannot approve Assurance. No probabilistic retry for absent authority.
6. **Evidence/promotion:** Guardian observes HTTP/API/link effects; RuntimeStore/Native/Candidate Owners produce persistent records; GN validates these records and Guardian alone determines Assurance gate. Watt's cached flags only project the exact stored result.
7. **Generalization:** GM supports its finite runtime oracle contract but not arbitrary governance-record evidence. GN strict profile has fixture evidence and no current real Candidate round trip; broad semantic assurance remains unqualified.
8. **Support:** M guardian_assurance.py:102/173/193/203/294/308; GM runtime.py:100/116/138/188/219; GN contract:88/135/141, runtime:180/199/205/223/256; N adapter:83/86/117/259/281; GN tests58/74/93. Oct6 actual Guardian refs and old N1 scoped cases are historical, not GN live proof.
### B6 — Candidate/Guardian → Human Integration Authorization (§3.6)

1. **Upstream authority:** SEALED exact Candidate fingerprint/source/proposed revision, current eligible Work/PWU basis and independently persisted required Guardian result.
2. **Actual consumer:** Work attention/readiness guard invokes CandidateGovernanceService with exact Candidate/scope; API derives authenticated Human actor and validates resource ownership.
3. **Agreement:** exact fingerprint/source/ref/scope are enforced. Normal configured software path includes Guardian preview guard; an architecture approval is not a Candidate authorization. Upstream omitted requirements are not healed by Candidate identity checks.
4. **Protection:** immutable Candidate and explicit authorization record preserve exact facts/decision; no model-generated Human record; stale basis fails. G1/G3 remain with zero authorization rather than pretending PASS.
5. **Owner:** Candidate Governance owns seal/authorization-contract validation, Guardian owns prior Assurance, authenticated Human owns the decision. Missing authorization is a real wait, not a semantic Self-Refine problem.
6. **Evidence/promotion:** Candidate Owner stores exact Candidate; Guardian stores gate; server authority supplies authenticated actor; Human action creates immutable authorization. Only that exact authority enables integration.
7. **Generalization:** exact identity/permission contract is intentionally deterministic and applies to arbitrary Candidate IDs. It is not a natural-language interpretation mechanism. Actual Human-authorized static paths exist historically (§5.1), but current N1 candidate decisions remain pending.
8. **Support:** M governance.py:79/159/174/175/179/213/372/461, work.py:3538/3549/3553, bootstrap.py:394/400/412, authority.py:59/143/149/175; authenticated authority fixture tests17/47/67; Oct6 Acceptance chain E1; G1/G3 zero authorization retained in N1 report.

### B7 — Human Authorization → Integration → Runtime Commit (§3.7)

1. **Upstream authority:** immutable exact Human authorization, sealed Candidate, current source baseline/plan/completion/admissibility and required exact Verification records.
2. **Actual consumer:** IntegrationService reads Candidate/source/authorization basis and persists effect intent; RuntimeCommitService reads converged Integration plus current exact source and completed basis.
3. **Agreement:** repository/ref/source/proposed commit/tree and scope must match. Git success does not imply SQL commit or all governance complete. No independent core-service Guardian bypass route is proven by this audit; normal lifecycle preceding guard is explicit.
4. **Protection:** PREPARED intent before effect, exact CAS/readback, idempotent replay, changed-baseline block, atomic trusted pointer admission and immutable authorization prevent duplicate/unauthorized advancement. They cannot redefine upstream facts.
5. **Owner:** Integration owns authorized Git effect/reconciliation; Runtime Commit owns trusted admission. Existing replay handles uncertain persistence; it is not new stochastic retry or permission repair. Human remains Owner of missing decisions.
6. **Evidence/promotion:** Git readback/effect record generates integration evidence; Integration verifies convergence; RuntimeCommitService revalidates full basis/authorization/PASS evidence and alone advances trusted runtime source.
7. **Generalization:** version/CAS/effect identity protocols apply to arbitrary legal Candidate/source values. They do not claim arbitrary semantic production completeness. Oct6 real accepted-source chain has scoped proof; present N1 effects do not exist.
8. **Support:** M integration.py:67/71/80/88/102/114/273/288; runtime_commit.py:159/296/458/488/586; work.py:2805/2817; Oct6 actual Runtime/Acceptance/source records (§5.1) and source recovery fixtures E2; N1 G1/G3 no integration/runtime records.

### B8 — Runtime Commit → Manifest → Human Acceptance (§3.8)

1. **Upstream authority:** trusted Runtime Commit and exact Work revision/source/artifacts/verification/authorization lineage, followed by Human review of an actually generated Manifest.
2. **Actual consumer:** Delivery publish constructs immutable Manifest snapshot; decide reads exact fingerprint and current trusted cycle; configured software acceptance reads actual Guardian and served Candidate.
3. **Agreement:** Candidate-to-Manifest identities/currentness are checked; future absent Manifest cannot be preapproved. Integration authorization and Delivery Acceptance are different lifecycle authorities.
4. **Protection:** immutable blob/hash/fingerprint, lock/currentness, immutable prior Human decision, exact runtime probe and applicable Guardian gate protect content/effects and preserve pending Human states. Document path having Guardian required=false does not authorize arbitrary software bypass.
5. **Owner:** Delivery owns Manifest/currentness and acceptance-contract validation, Guardian owns applicable Assurance, Human owns ACCEPT/REJECT. There is no model repair of a missing decision.
6. **Evidence/promotion:** artifact snapshot/Runtime Owner supply exact manifest evidence; runtime probe/Guardian supplies applicable observation; authenticated Human creates Acceptance; Delivery prepares source-promotion intent only on ACCEPT.
7. **Generalization:** typed artifact/runtime identity and exact fingerprint gates apply across supported document/software recipes. They do not prove arbitrary new recipe or new engineering semantics. Oct6 accepted static deliveries are scoped; N1 document Manifest/decision is absent.
8. **Support:** M delivery.py:470/474/502/505/516/620/624/642/646/658/662/675/684; retained exact G1 authorization review; Oct6 Acceptance IDs (§5.1); old Sep17 report expressly lacks durable Acceptance, which does not erase separate Oct6 evidence.

### B9 — Acceptance → Product Source → successor Work (§3.9)

1. **Upstream authority:** explicit exact Acceptance, Runtime Commit/Candidate, current Product Source version/revision/tree and applicable fixed Assurance refs.
2. **Actual consumer:** ProductManagedSourceService reads durable exact promotion intent and source baseline; provider performs CAS; prepare_work reads resulting persisted accepted source version and materializes an isolated Work branch.
3. **Agreement:** stored Acceptance/commit/target/expected baseline/tree must match; Git and SQL accepted source identities must converge; successor uses accepted version, not latest remote HEAD. N1 G1 document is not corresponding Greenfield Product V1.
4. **Protection:** pending-intent block, immutable decision, exact CAS, categorized blocked replay, transactional source-version advancement, applicable Assurance recheck, and version recheck during Work creation preserve authority/continuity. Historical failed Works are never reset to supply source evidence.
5. **Owner:** Product Source Owner owns promotion/source version and subsequent materialization; Delivery rechecks required Assurance; existing durable effect replay handles interruption. Human alone owns Acceptance; no new source coordinator is required by current evidence.
6. **Evidence/promotion:** provider Git observation plus persistent Acceptance/Runtime records generate source evidence; Source Owner validates and advances exact version atomically; prepare_work binds that version into source basis. Oct6 remote Git/SQL equality is retained actual scoped evidence.
7. **Generalization:** accepted revision/tree protocol and existing Brownfield/Greenfield source tests support contract reuse. Oct6 actual V1→real Multi-PWU→V2 is PROVEN_SCOPED; arbitrary natural-language source resolution is separate and keyword-limited; N1 corresponding accepted-V1 successor remains open.
8. **Support:** M product_managed_source.py:150/159/173/201/214/239/247/251/262/274/286/295/300/305/311/320; delivery.py:692; actual Oct6 p0-p1 JSON source_promotion IDs/GitSQL equality and workspace-continuity bounded failure (§5.1); Gitea tests:320/407/462/helper277; N1 isolated version>0 count0 is a distinct scoped blocker, not erased historical continuity.