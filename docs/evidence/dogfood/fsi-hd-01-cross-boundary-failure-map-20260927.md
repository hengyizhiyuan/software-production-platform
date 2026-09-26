# FSI-HD-01 — Cross-Boundary Failure Map, Attempts 1–7

**Decision:** stop the FSI-HD-01 rerun loop. Do not create Attempt 8 or make further case-specific repairs. This document is a failure map, not a Golden Case admission or Human Acceptance record. The same unaugmented three-line Human request was entered through `/app` in seven separate isolated product runtimes. No target repository file was edited by the tester, and no target Candidate was delivered or pushed.

The original request was to acquire `https://github.com/hengyizhiyuan/software-production-platform.git`, add one top-navigation text link `关于我们` with `href=/about`, provide an actual preview, and wait for Human review before delivery. The acquired source baseline in Attempts 1–7 was `refs/heads/main` at `0b535f63302fe45e88d0b3e203ae991868ced079`. Creating an `/about` page was not requested. Attempt 7 sealed a one-line Candidate `210f8ad07965e2a3c8a52fd10704d687691cd139`, but its functional Preview failed and Human Acceptance remains pending.

## Preservation ledger

| Attempt | Application revision | Work | Durable runtime | Outcome |
| --- | --- | --- | --- | --- |
| 1 | `dcee20e` | `4cd7f308-f170-4703-810a-433fab578be1` | `watt-fsi-hd01_*` volumes | Manual repository retry; Guided Design demanded redundant prioritization; no Candidate |
| 2 | `baefe6d` | `33835d43-8c55-45f2-bebe-f05b2aab6b11` | `watt-fsi-hd01-r2_*` volumes | Executor stopped `BOUNDARY_CROSSING_REQUIRED`; no change |
| 3 | `c3b4823` | `a119bf95-b50f-4be9-bf51-9d3ff6594432` | `watt-fsi-hd01-r3_*` volumes | Executor `UNABLE_TO_COMPLETE`; no change |
| 4 | `4f0e4ff` | `11bee5e9-db45-45fc-8b14-675fa55c483e` | `watt-fsi-hd01-r4_*` volumes | Inflated Multi-PWU plan; `repository.read` unavailable; `NO_PROGRESS` |
| 5 | `de08d10` | `f775c3d3-35ca-4e79-be42-e974304d4817` | `watt-fsi-hd01-r5_*` volumes | Provider invented `/about` route; adjacent test made required; Multi-PWU `NO_PROGRESS` |
| 6 | `3c11d3f` | `46306fa9-e703-45da-9832-7f13463c72ed` | `watt-fsi-hd01-r6_*` volumes | One-PWU plan blocked at Code Change Contract validation |
| 7 | `4018119` | `c6e017ef-20e2-4a7a-8d7d-f0a3289d9160` | `watt-fsi-hd01-r7_*` volumes | One-line sealed Candidate; test collection failed; Preview manually started for diagnosis and then `STARTUP_FAILED` |

All listed database, app-data, checkpoint, tool-receipt and workspace volumes remain; none was removed with `down -v`. Attempt 7's sealed Candidate ID is `e4198ea5-7521-5bc6-97ec-74a81c49dcab`, fingerprint `b045e2d459addc63823ed33846b4767cf202821ac99607de5ba7c8d832a50d84`, tree `a25ebb9d7dacf36454503e7a50b727a6adfbc196`. Its sole diff adds `<a href="/about" class="text-button topbar-about-link">关于我们</a>` after the existing Deliveries link in `src/spg/web/index.html`. `PATH_SCOPE` and `GIT_DIFF_CHECK` passed; this is not equivalent to a trusted Runtime Commit or served Preview. Attempt-level findings are in the six corresponding `fsi-hd-01-*-attempt-20260926.md` files; this map also records Attempt 7's final failure.

Attempt 7's preview session and failure trace are stored in `watt-fsi-hd01-r7_native-app-data` under `/var/lib/spg/production-environments/candidate-previews/evidence/bb716149-c75d-45df-bef0-b313f5b75f88/failure.log`; build and per-service logs are under the sibling `candidate-preview-runtime/evidence/bb716149-c75d-45df-bef0-b313f5b75f88/`. Its Native Attempt is `289dfcaa-1b67-491e-ac82-d333baecaad9`. The preview session reached `FAILED/STARTUP_FAILED` at `2026-09-26T16:27:25Z` with no endpoint. These are evidence locations, not instructions to restart or rerun.

## Boundary map

Each item names the earliest Watt boundary that should have caught the problem, not merely the component that eventually displayed the error. “Current” means the observed behavior at the end of Attempt 7; it does not assert broad qualification outside this journey. All proposed corrections below are generic requirements for a later system-wide closure task, not fixes authorized here.

### A1.1 — Production intent was treated as research or optional Work admission

- **Type / observation:** intent-stage mismatch and incorrect Human governance. WIC acknowledged the exact change but reported an external fetch failure and the UI required **按当前理解开始** before Work progressed.
- **Earliest boundary / missed validation:** Human message → WIC intent/response contract. The production verb and preview intent did not jointly suppress external-research routing or admit the explicitly requested bounded Work. Local response checks did not assert resulting Work authority and source acquisition from the real entry point.
- **Self-Refine / why not / Self-Converge:** no; no PWU existed and WIC admission had no feedback loop to correct the selected path. No attempt-level convergence governed the extra Human step.
- **Owner / current:** WIC response/admission and external-research applicability. Attempts 2–7 admitted Work and acquired the repository automatically; this earlier symptom was not observed again.
- **Generic signal / generality:** `EXPLICIT_PRODUCTION_REQUEST_NOT_ADMITTED` when interpreted intent, emitted response and created Work disagree. Applies to other direct build/fix requests, not just this link.

### A1.2 — Retryable public repository acquisition required a Human retry

- **Type / observation:** missing recovery wiring. Repository Attempt 1 ended `FAILED_RETRYABLE/NETWORK_FAILURE` after a 90-second clone timeout; a tester retried the same Work manually, and Attempt 2 acquired the source.
- **Earliest boundary / missed validation:** Repository Acquisition outcome → retry scheduler. `FAILED_RETRYABLE` was surfaced as a button rather than converted into bounded automatic retry with a terminal report. Successful isolated Git probes had not exercised this transient full-clone path.
- **Self-Refine / why not / Self-Converge:** no native Self-Refine; this precedes PWU. No governed retry budget automatically advanced the acquisition in Attempt 1.
- **Owner / current:** repository-acquisition scheduler. Attempts 2–7 acquired the public source without Human retry; the exact intermittent transport cause remains unproven.
- **Generic signal / generality:** `ACQUISITION_RETRYABLE_NO_AUTOMATIC_RETRY`, keyed by source and attempt lineage with bounded backoff. Generalizes to transient public connector failures.

### A1.3 — Exact change request became an open-ended design questionnaire

- **Type / observation:** scope inflation and incorrect Human governance. Guided Design asked Human to rank the nav link, preview form, delivery gate and `/about` despite the admitted feature request already fixing those relationships.
- **Earliest boundary / missed validation:** Work admission → Guided Design applicability / Steering bootstrap. A brownfield keyword selected the evolution questionnaire while the assessed intent had `FEATURE`, implementation scope and execution collaboration mode. Validation of individual design schemas did not test whether the schema was appropriate for the admitted Work.
- **Self-Refine / why not / Self-Converge:** no; no production Attempt existed. Steering escalated the redundant question instead of recognizing that the existing Human decision already supplied it.
- **Owner / current:** Guided Design selector and Steering entry contract. Attempts 2–7 closed DESIGN without that questionnaire.
- **Generic signal / generality:** `ALREADY_DECIDED_HUMAN_FACT_REASKED` / `DESIGN_SCHEMA_MISMATCH`, with admitted intent and constraints as evidence. Generalizes to bounded brownfield changes.

### A1–A2.4 — Source Work lacked a long-lived Product relationship

- **Type / observation:** missing Product continuity. Acquisition bound the repository, but `product_id` remained null in Attempts 1 and 2.
- **Earliest boundary / missed validation:** Repository/Product intake, before source Reality is declared complete. Source binding and Product binding were individually possible but not enforced as one continuity invariant.
- **Self-Refine / why not / Self-Converge:** no; asset intake precedes Executor Self-Refine. Repeating new Works was externally orchestrated, not a Watt convergence path.
- **Owner / current:** Product asset binding. Attempts 3–7 auto-created/bound a Product; not a remaining observed blocker in Attempt 7.
- **Generic signal / generality:** `REPOSITORY_BOUND_WITHOUT_PRODUCT_CONTINUITY`. Applies to any repository-backed long-lived Work.

### A2–A4.1 — Human-facing response lagged actual authority and source state

- **Type / observation:** incorrect status/trust projection. Watt said Human still had to admit Work or bind source after those actions were already happening; shadow WIC also floated an unrequested placeholder `/about` page in Attempt 4.
- **Earliest boundary / missed validation:** WIC response expression → current Work/Repository Reality. Generated wording was not reconciled with already persisted Work admission, acquisition and scope constraints; the normal native Compose runtime remained in `WIC_VNEXT_SHADOW` in Attempt 4.
- **Self-Refine / why not / Self-Converge:** no response-stage corrective signal or cross-turn contradiction detector. Repeated Human-facing inaccuracies did not become a governed convergence incident.
- **Owner / current:** response contract expression, runtime configuration and Reality projection. Controlled WIC in Attempts 5–7 described the requested link/preview/delivery boundary correctly at first reply; Attempt 7 still narrowed the durable desired outcome (A7.1).
- **Generic signal / generality:** `RESPONSE_CONTRADICTS_CURRENT_WORK_REALITY` and configuration parity between tested and product runtime. Generalizes beyond this case.

### A2.2 — Executor saw an ungranted tool and escalated a no-effect recipe error

- **Type / observation:** contract mismatch plus missing refinement wiring. Provider inventory advertised `filesystem.operation` without a grant; `wc -c` was denied by the process allowlist, then classified toward `BOUNDARY_CROSSING_REQUIRED` rather than a routine no-effect correction.
- **Earliest boundary / missed validation:** Task Contract → available-tool projection, then tool receipt → failure classifier. The former did not intersect tools with actual grants; the latter did not distinguish a confirmed no-effect `ValueError` from an authority crossing. Tool-level checks did not cover their composition in a live Attempt.
- **Self-Refine / why not / Self-Converge:** diagnostic evidence existed, but the classifier stopped it before a useful bounded retry. No successful local convergence in Attempt 2.
- **Owner / current:** Native Executor kernel/tool inventory and failure classification. Later attempts offered only granted tools and classified no-effect rejections as repairable; A3.1 shows that retry classification alone cannot supply a missing operation.
- **Generic signal / generality:** `ADVERTISED_TOOL_NOT_GRANTED` and `CONFIRMED_NO_EFFECT_TOOL_RECIPE`, with deterministic corrective budget. Generalizes to every restricted tool surface.

### A3.1 — No bounded edit operation existed for a truncated large file

- **Type / observation:** missing capability. `file.read` returned only 32 KiB of `index.html`; the only write form required full-file content. The Executor tried `sed`, `tail` and `wc`, all disallowed, and finished `UNABLE_TO_COMPLETE` without a change.
- **Earliest boundary / missed validation:** Task Contract / Native Tool Host capability matching, before dispatch. The contract admitted a tiny edit but offered no safe exact replacement for content larger than its read window. Tests of read and full-file write alone did not prove the task was executable.
- **Self-Refine / why not / Self-Converge:** bounded retries triggered after no-effect errors, but no permitted action could solve the task. Self-Converge did not reclassify repeated identical dead ends as a missing capability.
- **Owner / current:** Native Tool Host `file.write` contract and tool descriptions. Attempt 7 used `file.write/EXACT_REPLACE` to create a one-line diff; this particular gap was bridged.
- **Generic signal / generality:** `ADMITTED_CHANGE_HAS_NO_SAFE_EDIT_PRIMITIVE`, checked against file-size/read limits and granted tools. Generalizes to any large existing file.

### A4.1 — Product runtime used shadow WIC despite accepted controlled mode

- **Type / observation:** runtime configuration mismatch. The normal native Compose profile ran `WIC_VNEXT_SHADOW`, so Human-facing responses retained the old admission and placeholder wording.
- **Earliest boundary / missed validation:** runtime activation/configuration parity before first message. Unit tests of controlled mode did not establish which mode the actual `/app` runtime used.
- **Self-Refine / why not / Self-Converge:** not triggered; configuration drift was not a runtime refinement signal.
- **Owner / current:** native Compose WIC mode binding. Attempts 5–7 ran controlled mode; durable intent loss still appeared in Attempt 7.
- **Generic signal / generality:** `ACCEPTED_MODE_NOT_ACTIVE_IN_PRODUCT_RUNTIME`. Generalizes to feature-flagged product capabilities.

### A4.2 — Model file guesses became required edit authority and artificial Multi-PWU

- **Type / observation:** scope inflation. Four Semantic DESIGN `code_targets` were promoted to required paths, including style/script/test files, then split into multiple PWUs for a one-link change.
- **Earliest boundary / missed validation:** Semantic provider candidate → repository-inspected Change Proposal. Provider path guesses lacked Human authority or exact-tree necessity; syntactic path validity and planner decomposition were checked after the authority error had already occurred.
- **Self-Refine / why not / Self-Converge:** no semantic scope-reduction refinement fired. Repetition was handled by external Codex repairs and new Works, not Watt convergence.
- **Owner / current:** Semantic Step materialization, repository-aware proposal, production planner. Attempt 7 required one exact `index.html` edit and produced `ONE_PWU_FIT`; this does not qualify true Multi-PWU execution.
- **Generic signal / generality:** `PROVIDER_CANDIDATE_PROMOTED_TO_REQUIRED_SCOPE` and `PWU_COUNT_EXCEEDS_PROVEN_CHANGE_SURFACES`. Generalizes to all model-proposed scopes.

### A4.3 — Inflated Multi-PWU units could not obtain repository.read

- **Type / observation:** contract mismatch and missing capability in that path. Three branch Attempts returned `UNKNOWN` with `Required capability repository.read is unavailable`; Orchestrator stopped `NO_SAFE_PROGRESS`.
- **Earliest boundary / missed validation:** Production Plan admission → per-PWU connector/grant availability, before branch dispatch. Planner could form a graph whose required capability was absent from actual branch execution.
- **Self-Refine / why not / Self-Converge:** no useful Self-Refine because the required capability was not available; repeated branch failures did not trigger governed plan contraction or incident classification.
- **Owner / current:** Multi-PWU capability admission and runtime connector binding. Avoided by Attempt 7's one-PWU plan, **not proven fixed** for legitimate Multi-PWU Work.
- **Generic signal / generality:** `PWU_REQUIRED_CAPABILITY_UNAVAILABLE_AT_ADMISSION`; stop or replan with exact capability evidence. Generalizes to every parallel branch plan.

### A5.1 — Semantic provider invented an `/about` backend route

- **Type / observation:** scope inflation and provider-to-authority leak. Human requested a link, but the Semantic DESIGN proposal objective and test expectation required creating `/about` in `src/spg/api/http.py` without observed necessity.
- **Earliest boundary / missed validation:** Semantic proposal → governed Production Plan. Free-text objective and verification expectation were copied directly despite contradicting admitted constraints. Code target inspection did not validate the behavioral claim inside prose.
- **Self-Refine / why not / Self-Converge:** no semantic contradiction signal; production was allowed to advance. External repair later bounded plan prose; no Watt-owned convergence record.
- **Owner / current:** Semantic Step admission and Human-fact precedence. Attempt 7 plan did not require a new page, but A7.1 shows that using only a lossy desired outcome is not a complete solution.
- **Generic signal / generality:** `PROPOSED_BEHAVIOR_NOT_ENTAILED_BY_HUMAN_INTENT_OR_REPOSITORY_NECESSITY`. Generalizes to unrequested routes, dependencies, refactors and features.

### A5.2 — Adjacent test reference was treated as a required edit and produced no progress

- **Type / observation:** scope inflation plus missing convergence governance. Exact-tree discovery found the nav file, then made an integration test *required* because it mentioned that file; the planner created two branch PWUs and a Join. Run `9552ac94-9852-47db-b555-8c8f03a8d5cf` stopped `NO_PROGRESS`, branches in `VERIFYING`, no trusted output.
- **Earliest boundary / missed validation:** repository-aware proposal target disposition, then planner fitness. “Useful to run” was confused with “must modify.” Existing proposal tests previously encoded the adjacent-test-as-required behavior; they could not catch this semantic error.
- **Self-Refine / why not / Self-Converge:** no successful local refinement; the no-progress state did not contract the unjustified plan or route a systemic incident.
- **Owner / current:** change proposal disposition and plan decomposition. Attempt 7 kept the test conditional and formed one PWU; legitimate test execution remains separately governed.
- **Generic signal / generality:** `TEST_REFERENCE_PROMOTED_TO_WRITE_SCOPE` plus `NO_PROGRESS_WITH_UNNECESSARY_PWU_SPLIT`. Generalizes to any adjacent test or related file.

### A6.1 — Conditional test became an impossible typed verification obligation

- **Type / observation:** contract mismatch. The plan correctly required only `index.html`, but proposed `PYTEST_TARGET:tests/integration/test_mvp_app_work_flow.py` outside its writable boundary. `CodeChangeContract` rejected it: `PYTEST_TARGET must be inside the admitted change boundary`; Steering stopped `BLOCKED` before an Attempt.
- **Earliest boundary / missed validation:** Change Proposal obligation construction. The contract's validator **did** detect the mismatch, but only after Semantic/Planning had admitted it; no repair path translated the validation exception into a new valid proposal. Local tests passed around proposal shape without composing the downstream contract.
- **Self-Refine / why not / Self-Converge:** none; no PWU existed and the invariant exception became a terminal Steering stop. No automatic proposal correction followed.
- **Owner / current:** proposal-to-Code-Contract boundary and validation-failure routing. Attempt 7 no longer typed conditional tests as mandatory obligations; whether read-only focused testing is correctly governed remains open.
- **Generic signal / generality:** `VERIFICATION_TARGET_OUTSIDE_ADMITTED_BOUNDARY`, returned as structured proposal feedback before execution. Generalizes to all code Works.

### A7.1 — Durable desired outcome dropped the requested code change

- **Type / observation:** semantic loss. Attempt 7's Work `desired_outcome` and resulting plan objective became only “生成可实际查看的预览，由用户确认后再决定是否交付。” The nav-link requirement survived in constraints and Work requests, so the Executor still made the correct one-line edit, but the headline Goal no longer described it.
- **Earliest boundary / missed validation:** WIC assessment → Engineering Semantic Truth / Work Reality admission. The full original message was retained in `work_reality_revisions.requests`, yet no completeness invariant required the desired outcome to cover the primary requested change. Later materialization trusted that lossy field.
- **Self-Refine / why not / Self-Converge:** no semantic completeness signal or correction fired; fortunate downstream constraints masked the omission. No cross-attempt convergence governor noticed that the plan objective changed between runs of the same message.
- **Owner / current:** WIC-to-Work semantic reconciliation. **Open** at stop; no further case fix made.
- **Generic signal / generality:** `PRIMARY_HUMAN_CHANGE_MISSING_FROM_DURABLE_OUTCOME`, checked against explicit requests/constraints with fact provenance. Generalizes to any multi-clause request.

### A7.2 — Test environment failed collection; Self-Refine reported recovery too narrowly

- **Type / observation:** validation environment mismatch and false convergence. Native `test.run` invoked `python -m pytest --collect-only -q` across the repository and failed with five `ModuleNotFoundError: openai_codex` collection errors; the baseline lists Codex packages under an optional extra. One Self-Refine event recorded `VERIFICATION_FAILURE` then `final_result=RECOVERED` because the minimum typed obligations `PATH_SCOPE` and `GIT_DIFF_CHECK` were satisfied, although focused test evidence and preview were still missing.
- **Earliest boundary / missed validation:** Production Environment dependency readiness and Task Contract verification design before test dispatch; then Self-Refine closure before claiming recovery. A test command was offered without matching optional dependencies or scope; closure evaluated the narrow written obligations rather than the Human's requested runnable preview.
- **Self-Refine / why not / Self-Converge:** **yes**, one event, but its `RECOVERED` label described the bounded effect/obligation path, not end-to-end Work recovery. No system-wide convergence rule withheld the recovered label until runtime Preview and Human review were possible.
- **Owner / current:** verification planner, Production Environment dependency profile, Self-Refine result semantics. **Open** at stop; Candidate was sealed without a passing project test.
- **Generic signal / generality:** `TEST_ENVIRONMENT_NOT_READY`, `VERIFICATION_EVIDENCE_INCOMPLETE`, and recovery status scoped to the exact obligation set. Generalizes to any project with optional/test dependencies.

### A7.3 — Candidate review asked Human to start Preview

- **Type / observation:** incorrect Human governance and missing refinement wiring. After sealing the Candidate, Work became `NEEDS_ATTENTION` for exact Candidate authorization while Functional Preview showed `NOT_REQUESTED` and a **Start functional preview** button. The tester clicked it solely to diagnose the preview path. That action is inappropriate Human friction for this scenario and does not count as autonomous product success.
- **Earliest boundary / missed validation:** sealed Candidate → preview orchestration / Human Attention projection. Preview creation was exposed as an API/UI action, but the production path did not schedule it before requesting final review. Validation of candidate sealing and preview request separately did not assert their sequence.
- **Self-Refine / why not / Self-Converge:** no; preview had not been requested, so no failure receipt existed for Self-Refine. Human became the missing message bus. No automatic convergence transition advanced Candidate to preview.
- **Owner / current:** Candidate-to-Preview orchestration and governance timing. **Open** at stop; Human authorization itself can be a valid final acceptance boundary only after a healthy exact-Candidate Preview is actually shown.
- **Generic signal / generality:** `CANDIDATE_SEALED_PREVIEW_REQUIRED_BUT_NOT_REQUESTED`, with an invariant that review attention must not precede runnable preview readiness. Generalizes to all preview-required Works.

### A7.4 — Built, healthy Candidate failed served-preview verification across network namespaces

- **Type / observation:** preview runtime contract mismatch. Manual diagnostic request created FULL_APPLICATION_RUNTIME session `bb716149-c75d-45df-bef0-b313f5b75f88`. Exact Candidate image build succeeded; candidate app and nginx logs showed healthy startup. `verify_served()` then tried `http://127.0.0.1:<host-published-port>/auth/session` from the **Watt app container** and received `ConnectionRefusedError`. The preview persisted `STARTUP_FAILED`; no usable URL was handed to Human.
- **Earliest boundary / missed validation:** Preview topology admission / reachability contract, before the long build. Gateway port is published to the Docker **host** loopback, while the verifier's `127.0.0.1` is its own container namespace. The existing probe checked app/proxy container health, not verifier-to-public-endpoint reachability in the actual deployment topology.
- **Self-Refine / why not / Self-Converge:** no automatic preview retry or topology correction. The Preview service persisted failure evidence and cleaned up; Watt did not turn it into a governed repair/replan signal. Repeating the full Human scenario is not an appropriate substitute.
- **Owner / current:** `DockerCandidatePreviewRuntime` endpoint model and Preview failure propagation. **Open** at stop; the network-namespace explanation is strongly supported by the published-host-loopback configuration and exact connection-refused trace, but no fix was attempted here.
- **Generic signal / generality:** `PREVIEW_VERIFIER_ENDPOINT_UNREACHABLE_FROM_RUNTIME_NAMESPACE`, tested before claiming readiness, with separate health and served-behavior evidence. Generalizes to containerized/local/remote gateway topologies.

## System-wide convergence conclusion

The repeated loop itself was **external Codex orchestration**: each run used a fresh Work and a changed application revision after a human-assisted diagnosis/repair. Watt did not own a seven-attempt lineage, aggregate recurring failures, select architecture owners, or decide when to stop retries. Within Attempt 7 it produced the exact tiny source change, but its single Self-Refine event marked a narrow tool/contract recovery while project validation and runtime preview were still unresolved. This is evidence of both **missing refinement wiring** at pre-PWU, Candidate and Preview stages, and **missing convergence governance** over repeated terminal/no-progress states. A later system-wide task should define generic signals, durable incident lineage and stop/repair decisions across those stages; it should not replay FSI-HD-01 as an eighth case-specific patch cycle.

| Failure class | Evidence in this map |
| --- | --- |
| Case-specific bug | **None proven.** The Chinese label and `/about` exposed failures, but their mechanisms apply to other requests. |
| Missing capability | A3.1 bounded edit; A4.3 unavailable branch repository read; A7.2 test-environment readiness. |
| Contract mismatch | A2.2 advertised/granted tools; A4.3 PWU grants; A6.1 test obligation/write boundary; A7.4 preview endpoint namespace. |
| Scope inflation | A1.3 questionnaire; A4.2 required model paths; A5.1 new route; A5.2 required test edit. |
| Incorrect Human governance | A1.1 admission button; A1.2 retry button; A1.3 redundant decision; A2–A4.1 inaccurate response; A7.3 preview-start button before review. |
| Missing refinement wiring | A1.2 acquisition; A6.1 proposal validation; A7.3 Candidate-to-Preview; A7.4 preview failure. |
| Missing convergence governance | A3.1 repeated impossible retries; A4.3/A5.2 `NO_PROGRESS`; A7.2 false narrow `RECOVERED`; the external seven-Work rerun loop. |

`FSI_HD_01_HUMAN_ACCEPTANCE = PENDING`  
`EXACT_CANDIDATE_PREVIEW = FAILED`  
`NO_UNAUTHORIZED_DELIVERY = PASS`  
`GOLDEN_CASE_ADMISSION = NO`  
`ATTEMPT_8 = NOT_STARTED`
