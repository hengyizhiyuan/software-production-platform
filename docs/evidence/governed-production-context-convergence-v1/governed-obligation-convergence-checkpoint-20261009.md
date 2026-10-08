# N1 governed obligation convergence checkpoint — 2026-10-09

This is a new receipt for the current N1 turn. **N1 PARTIAL — Exact Engineering Blocker.** It does not replace any earlier qualification report or turn an interrupted trial into PASS. Read-only ECS observations below are grade A for the identities and persisted values actually read; exact-source tests and code inspection are grade B. Historical facts absent from durable records remain UNKNOWN.

## Exact identity and protected state

- Watt task branch: `codex/governed-production-context-convergence-v1`. Code revision `8199c0264116ad6e99dc950920f932c0c1e10d4d`; previous stage-routing commit `c783b3eb2cf8713aef4c52459d440ef71e6e7b91`; approved post-admission materialization ancestor `c1193324f8e661ddc9ca5ad7817bb968260507d9`. The `preview.inspect` recovery change `2925e4cef4a5260122a6916ae12b8caacaae864b` remains an ancestor. No N1 branch reset occurred.
- ECS instance `i-0jl386xnbauudq5j9jk0`, region `cn-wulanchabu`; isolated database `spg_n1_qualification_20261008`; isolated Gitea `watt-n1-gitea-20261008`. Production source `/data/watt/runtime/source` still has exact HEAD `ee5bd86a53891f9391785c91d0ccef81ad2d56c3`.
- All four isolated N1 runtime roles still run **old** image `watt-n1-candidate:0d48353`, ID `sha256:64289d0a086ecf03efb2dae24ab036bd83906905e00fd71fa30fc51feb160709`. The previously built `c783b3e` image ID `sha256:19487bca5fc83d6fde50860f76c2b86f4d3f511449b435a6e27f004471bcfc21` was **not deployed** and does **not** contain the safety correction at `8199c02`. No `8199c02` runtime image or real Work qualification exists.
- Guardian authoritative remote `main` was fetched read-only and matches the ECS owner export revision `27bf5691e30104bf9a460df29a6f7dd4fb884a30`. No Guardian or ECF source was modified. No original accident Work, historical Candidate, Human Decision, Quality Ledger, production service, credential or data was modified.

## Repository Reality and root cause

The interrupted work left `c783b3e` committed, clean, and one commit ahead of the remote; no prior pytest process was running. Its extra file-count check was sound: admitted `CARDINALITY=1`, exact create target and original provenance were checked against Git Diff. The earlier deterministic and bounded model-assisted HTML checks for exact target, text, order, value and scope remain.

Two stage/Owner routes in `c783b3e` were **not** sound:

1. Any `EQUALITY=false` Fact was treated as a future governance obligation. A valid content absence such as `page.has_footer=false` would take that route, although an HTML absence must be checked against the exact Candidate now. Typed `SCOPE` qualifiers and one mixed `ACCEPTANCE_ASSERTION` were also routed without proving which actual downstream gate would discharge each original Fact.
2. Every Managed Web ECF protected obligation was marked `DOWNSTREAM_ASSURANCE`, including current Candidate content constraints. `RepositoryCodeVerifier` could return PATH_SCOPE PASS with all of them `UNVERIFIED`. Guardian v1 later maps these to `GUARDIAN_REQUIRED`, but its current runtime can cover that state only with a matching HTTP/API effect; it cannot independently verify source identity, Candidate sealing, Human decisions, lifecycle exclusions, or complete no-effect audit. Guardian also accepts a Watt-supplied `COVERED` flag without resolving the referenced persisted Verification itself. Thus blanket deferral did not prove a lawful Owner handoff.

The correction in `8199c02` removes only these unsupported automatic deferrals. Unknown Fact plans visibly return `UNVERIFIABLE_CURRENT` and fail current Verification. Uncovered ECF obligations fail current Verification. The exact new-file check, post-admission per-Fact trace, bounded method repair, existing exact checks and protected-fact preservation remain intact. A negative regression shows an unrelated `EQUALITY=false` content Fact cannot inherit a governance route. This is truthful containment, **not** the full stage-aware obligation implementation.

### Persisted G0/G3/G4 facts read this turn

| Case | Read-only source | Current-stage content/scope | Lifecycle or governance obligation with no proven consumer route |
| --- | --- | --- | --- |
| G0 | Work `6899ad34-73f1-5180-8323-f1559dd9cc8f`, Work Reality revision `056a1c94-9762-584c-b48e-a60e829a9a06` | `page.index_file`, exact H1/paragraph, `work.change_scope` | `release.preview_requested=false` IDs `3c32bf63-d00a-541f-9b14-8a9ea572d7a1`; `release.deploy_and_publish_authorized=false` ID `a1300ef0-de89-519b-bc6c-8ba71629abff`; ECF has seven constraints plus Product Intent, including both content and exclusions. |
| G3 | Work `e50a9566-155c-5843-93fd-9b7ec800df7d`, revision `54b21d5d-3e03-54bf-8b1c-c46b987b3abb` | One new `status-v0.html`, H1, paragraph, exact diff; accepted Product V0 source identity remains `c37c2e366650935dde62ef48a6b54a621337a27c` | Mixed assertion `116dac76-837f-5976-a605-9c37a471ea6a` contains current content verification **and** future reviewable Candidate/no-delivery claims. Deferring the whole assertion loses the current part. |
| G4 | Work `c616ab6b-d985-5b35-a2c4-47d9b79ad4e7`, revision `071c9671-c68c-5a66-926e-d334e2aa3e8a` | F01–F14 ordered tuple `7b610ed7-bb57-54fb-88cc-4a4b10bdc6cb`, exact page assertion and list assertion | `delivery.authorization` Fact `7d6616a7-b652-5986-88f8-a35e2178779c` and nine ECF obligations include content, a future reviewable Candidate, and deployment/publication exclusions. The fourteen item values alone do not prove all nine. |

No original failure record above was replayed as a new PASS. The unresolved type gap is specific: `SemanticFactReference` carries relation/value/scope/qualifiers/provenance but no trustworthy lifecycle evidence domain or obligated Gate. `ProtectedContextObligation` carries immutable ECF content/source identity but no typed fulfillment phase. A safe derived route must bind each original Fact/ECF obligation to a current check or to a **verified** downstream Gate, with a separate actual evidence result. A generic false value, subject spelling, ECF list position, or free-text retention is insufficient. A negative no-effect claim additionally needs known audit coverage; missing ordinary logs cannot prove it. The present contract cannot establish this for G0/G3/G4, so new Work on `8199c02` would deterministically fail the same unsatisfied obligation and was not created just to repeat the known side effect.

## Tests, cost and evidence grade

- Exact `git archive` of code revision `8199c02` plus the three directed test files and three source documents: SHA256 `5d8d968c33419a9df11a23ee2210cdbed0bfc51cddfdeff39cae11c0f6b6548c`, verified equal on the ECS. With the exact source mounted read-only into a disposable, network-disabled test container and existing Guardian/ECF exports mounted read-only, **64 directed tests PASS** across `test_n1_static_html_semantics.py`, `test_static_protected_context_verifier.py`, and `test_decision_context_integration.py`. This is grade B, not a live Worker/Work qualification.
- Earlier runs in this turn exposed stale test-image code and missing test fixture/doc mounts; they were harness errors, not product PASS or product FAIL. A corrected overlay first yielded 45 PASS, then 19 PASS; the final exact archive yielded 64 PASS. No model call, application image build, isolated runtime restart, live new Work, Guardian assessment, Human authorization, Runtime Commit, or Manifest was made in this turn. Compute usage was not metered; no cost estimate is invented.
- The existing `c783b3e` image was built before this turn and not deployed. The existing `0d48353` live evidence remains historical and cannot qualify `8199c02`.

## G0–G6 and all original Closure Conditions

| Case | Truthful current result |
| --- | --- |
| G0 | **PARTIAL / engineering blocked.** Original failures retained. `page.index_file` can be materialized, but its two negative lifecycle Facts and ECF content/governance split have no validated stage route. No final-code real Work PASS. |
| G1 | **Qualified SEALED document Candidate; Human Integration decision pending.** Candidate `695cc730-849a-5dce-88da-c62c19c9f6b8`, fingerprint `481e481d6f68936f149541f4c8a4b3e5551a4fec318de88deca4b73d92ae7ff7`. Exact independent review is `g1-new-candidate-human-authorization-review-20261008.md`. No authorization, Runtime Commit, Manifest or Delivery Acceptance was created. |
| G2 | **BLOCKED on real accepted Product V1.** A G1 document or fixture cannot substitute for corresponding Greenfield Product V1 source; G0 Candidate and separate Human decisions are prerequisites. |
| G3 | **Historical source binding positive, final-code path open.** Mixed assertion needs a lawful split; no new Work/Guardian/Delivery PASS. |
| G4 | **PARTIAL / engineering blocked.** The exact F01–F14 tuple is retained and current content check exists; all protected content/governance obligations still require verified Owner routing. |
| G5 | **PARTIAL.** Historical `LOCAL_OBLIGATION_RECOVERED` was followed by Work failure; no final-code repair → full Work completion proof. |
| G6 | **PARTIAL.** Historical WIC stop and selected regressions do not prove a live irreparable Context Assembly truthful stop on final image. |

| # | Original closure obligation | Status at this checkpoint |
| --- | --- | --- |
| 1 | G1/G2/G3 original root causes | PARTIAL; G2 live source absent |
| 2 | Document Context readiness | Scoped G1 positive; final exact-source continuity open |
| 3 | Document Candidate to legal Delivery | WAITING Human G1 Integration, later Manifest/Acceptance |
| 4 | Revised Greenfield successor | OPEN; no accepted V1 |
| 5 | Non-new Work classification | Scoped G3 positive; full path open |
| 6 | No Protected Fact loss | Exact facts retained; Owner coverage PARTIAL |
| 7 | Legal Context not incorrectly blocked | OPEN; G0/G4 stage contract unresolved |
| 8 | Full repair convergence | OPEN; G5 incomplete |
| 9 | Irreparable truthful stop | OPEN; G6 live Context case absent |
| 10 | No unbounded retry/budget reset | Directed boundary positive; final live proof open |
| 11 | No duplicate PWU/Task/Execution | Historical selected-case evidence only |
| 12 | Exact Candidate/Revision/Verification/Guardian lineage | PARTIAL; Guardian governance evidence absent |
| 13 | Human authority | Preserved; G1 and future G0 decisions pending |
| 14 | Software production path | OPEN; G0/G4 full Work absent |
| 15 | F26 Guardian regression | Prior regression only; final image open |
| 16 | Related regressions | 64 exact-code directed PASS; full gate open |
| 17 | Real ECS qualification | Historical old-image only; final image open |
| 18 | Restart/recovery | Historical scoped isolated Gitea restart; final qualification open |
| 19 | Preserve original history | Preserved; no incident Work/Candidate rewritten |
| 20 | Push task branch | Pending this receipt's commit/push at capture |
| 21 | Keep production main canonical | Confirmed `ee5bd86a53891f9391785c91d0ccef81ad2d56c3` |
| 22 | Record workspace state | Original task worktree; main workspace untouched |
| 23 | Persist complete qualification evidence | This checkpoint is durable after push; final live receipts open |

## Human Decision Package and recovery location

The only currently reviewable authorization is **G1 Integration**, for the exact Product/Candidate/fingerprint above. File `docs/n1-g1-lineage.md` has SHA256 `925a7ea9e6b0125c59b3537c19e50073d44e42c60d1e72d2765540e07aa9fbce`; Verification `e0b16874-f96f-5e38-964b-73301e4bc3c8` PASS; Guardian is not required for that document. Authorization would persist an isolated PostgreSQL decision, integrate the isolated Work Git Candidate and then allow an exact Runtime Commit. It does not touch production main/business service and is distinct from later Manifest Delivery Acceptance. An explicit Human response is pending. No G0 authorization can be requested before a new Candidate exists.

Cross-computer recovery: tracked task branch directory `docs/evidence/governed-production-context-convergence-v1/`; ECS durable qualification directory `/data/watt/app/owner-runtime/qualifications/governed-production-context-convergence-v1/`. The isolated database, Gitea repositories, Work Git objects and owner-runtime evidence remain in place. The code/Guardian contract blocker must be addressed before creating another G0/G4 Work or claiming Engineering Ready. N1 remains **PARTIAL**.
