# N1 qualification delta — post-admission Verification materialization

Captured 2026-10-08 15:08 UTC. **PARTIAL / OPEN; N1 is not eligible for Closure.** This is a new receipt for the Architecture Lead's approved option 2. It neither replaces the [prior full qualification report](qualification-report-0d48353-20261008.md) nor changes any historical Work, Candidate, Human Decision, or Quality Ledger. Grade **A** below means persisted isolated PostgreSQL and immutable Work Git identity; grade **B** means exact code inspection or isolated test/dry-run. No dry-run is counted as a new Work PASS.

## Identity and isolation

- New task-branch **code-only** revision: `c1193324f8e661ddc9ca5ad7817bb968260507d9`, on `codex/governed-production-context-convergence-v1`. The last live-qualified application revision remains `0d4835353dbdb38abd6abfc19127b84eb5544475`, isolated image `sha256:64289d0a086ecf03efb2dae24ab036bd83906905e00fd71fa30fc51feb160709`. The `preview.inspect` recovery classifier commit `2925e4cef4a5260122a6916ae12b8caacaae864b` is an ancestor of the new code revision. **No image was built or real Worker Work run on `c119332`; the old image is not evidence for the new revision.**
- ECS identity `i-0jl386xnbauudq5j9jk0` in `cn-wulanchabu`; all reads/tests used the isolated N1 database `spg_n1_qualification_20261008`, existing immutable Work Git repositories, or the network-disabled `watt-n1-pytest:20261008` test container. The replay opened PostgreSQL with `SET TRANSACTION READ ONLY` and read exact Candidate commits. It imported the new static checker as a temporary file in the isolated API container. It did not invoke the live Verification service or update any Verification record.
- ECS production `/data/watt/runtime/source` remains canonical `ee5bd86a53891f9391785c91d0ccef81ad2d56c3`; no production source, service, DB, credential, or historical evidence was modified. The local main workspace was not used for edits.

## Root cause and bounded implementation

**A/B root cause:** WIC/IRK admitted intact G0/G4 Engineering Semantic Facts into Work Reality and PWU, but the post-admission static Verification consumer selected checks by a finite subject/scope profile. `page.index_file` and `acceptance.ordered_list_items` were valid admitted expressions outside that profile. The prior checker could also omit an unrecognized Fact entirely. The problem is in consumer materialization, not permission to rewrite Human Intent or invent Approved Facts.

The new Watt code reuses `EngineeringSemanticFact`, `SemanticFactReference`, the Work Reality store, the existing PATH_SCOPE Verification, Git Blob reader, static HTML parser, Model Runtime, and `CONTRACT_MISMATCH` signal. `RepositoryCodeVerifier` reloads each admitted Fact from the exact Work Reality revision, checks PWU reference equality and Work lineage, and supplies immutable provenance to the static consumer. The consumer emits one visible result per Fact. It first reuses existing exact checks, then derives a method from typed relation/value/scope/qualifiers and exact admitted target, never a global subject alias. Its trace binds Fact ID, Work revision, relation, value/qualifier digests, scope, authority, provenance/source record IDs, Candidate revision, exact target, linked Fact and method. Unsupported facts return `UNVERIFIABLE_FACT_PLAN` and make Verification fail closed; they are not silently skipped.

For ambiguous EQUALITY/ORDERED_COMPONENT expression only, the existing model runtime can propose a method and exact source quote. The proposal cannot set a new expected value. It is accepted only if the target matches, the quote is literal admitted provenance, and the method is compatible with typed relation/value; the exact Git Blob is checked after plan validation. At most two attempts occur in this owner-specific repair. Real Candidate mismatch remains FAIL. No fact, budget, authority, source baseline, or side-effect grant is changed.

This implementation is deliberately **incomplete for governance evidence**. Source contents cannot establish release prohibition, Product source acceptance, Human integration authority, or absence of unauthorized effects. The exact additional cross-owner gap and minimum requested Guardian/Watt changes are in the [Guardian governance evidence Finding](guardian-governance-evidence-contract-finding-20261008.md). Per the user's stop condition, scope expansion and new live qualification stop at that boundary.

## Test, replay and Self-Refine evidence

- **B, 43 directed tests PASS** in a network-disabled isolated test container, with the two changed providers and new test file overlaid read-only. Cases cover three previously unlisted file-subject expressions, unlisted paragraph qualifier, G4 ordered assertion bound to exact original tuple, wrong file, missing item, swapped order, wrong value, wrong scope, page assertion drift, unsupported Fact visibility, and a real Candidate H2 defect. These are selected regressions; they are not a complete `c119332` image qualification.
- **B, bounded plan-repair test:** synthetic request `plan-1` proposed `EXACT_H1` with `other.html` and was rejected as a target mismatch. Synthetic request `plan-2` preserved `index.html` and a literal Human source quote; the derived plan converged, then the correct Candidate passed exact H1 inspection. With an extra H2 in the Git Blob, the same lawful plan returned `EXACT_H1_MISMATCH`, not PASS. Separate synthetic requests `invalid-1` and `invalid-2` supplied an invented source quote and exhausted the two-attempt bound with `UNVERIFIABLE_FACT_PLAN`. These are test request IDs, not persisted production Self-Refine events. **No live post-admission Self-Refine event has yet been qualified.**
- **A source + B read-only replay, G0:** historical Verification `ca50583d-a863-5fee-94cf-f03467d5e921` stays **FAIL** on exact Candidate commit `4c158f0c94b70d586ade0797e3b7d41c6469ddd6`. New derivation maps Fact `9b3e65d0-fec7-55c0-9fec-a59a0c62b6c0` (`page.index_file`) to the exact `index.html` target and confirms it; existing H1, paragraph and changed-file checks also confirm. Release Facts `3c32bf63-d00a-541f-9b14-8a9ea572d7a1` and `a1300ef0-de89-519b-bc6c-8ba71629abff` remain `UNVERIFIABLE_FACT_PLAN` pending governance evidence. This is no full G0 PASS.
- **A source + B read-only replay, G4:** historical Verification `2c650693-cbe6-50b4-a0a5-ab6019a57eff` stays **FAIL** on exact Candidate commit `7f144c5456ddf38d437d51dd7fe9a5dc4e4da9ff`. The accepted `acceptance.ordered_list_items` Fact `84f6bfcd-184c-55ad-ada1-8bea7ac9f784` now derives an exact ordered-list assertion tied to original ordered Fact `7b610ed7-bb57-54fb-88cc-4a4b10bdc6cb`, its same Work revision/authority/source record, fourteen positions, labels and once-only condition. The exact Candidate list satisfies that content assertion. `delivery.authorization` Fact `7d6616a7-b652-5986-88f8-a35e2178779c` remains `UNVERIFIABLE_FACT_PLAN`. F01–F14 are unchanged; this does not prove all ECF Protected Context obligations.
- **A source + B read-only replay, G3:** historical Verification `81fd3068-58c0-54d2-9263-78eaab267088` stays **PASS** as a historical record on commit `6bebf8e0a351f58e7a07ed994dc869a85707109a`. New strict per-Fact dry-run confirms H1, paragraph and changed-file content but cannot materialize the admitted one-new-file cardinality and mixed “exact text/file scope verified; reviewable Candidate left” assertion from source alone. It therefore would **not** justify a new PASS yet. This does not alter the previously proven unique Product V0 source binding (`c37c2e366650935dde62ef48a6b54a621337a27c`); the new consumer requires an additional lawful evidence path before final-revision G3 qualification.

## G0–G6 at this stop point

| Case | Real status and still-open obligation |
| --- | --- |
| G0 | **FAIL/PARTIAL.** Two original real Works failed. `preview.inspect` recovery fix and materialization have only code/test evidence; final-revision normal Greenfield Worker → full Work PASS is open. |
| G1 | **Qualified sealed Candidate, Human gate pending.** New Candidate `695cc730-849a-5dce-88da-c62c19c9f6b8`, fingerprint `481e481d6f68936f149541f4c8a4b3e5551a4fec318de88deca4b73d92ae7ff7`, exact review `g1-new-candidate-human-authorization-review-20261008.md`. No Human Integration Authorization, Runtime Commit, Manifest or Delivery Acceptance. The old sealed Candidate is not submitted. |
| G2 | **BLOCKED.** No real Human-accepted Product V1 source in isolated Reality; no fixture or G1 document is substituted. Successor Worker qualification remains open. |
| G3 | **Historical scoped positive; final-revision qualification open.** Unique V0 source resolution is retained. New strict materialization exposes two unverified obligations. No Human integration/acceptance. |
| G4 | **FAIL/PARTIAL.** The exact F01–F14 content and derived assertion check in read-only replay; lifecycle/ECF governance coverage and full new Work PASS are open. |
| G5 | **PARTIAL.** Existing local recovery event was followed by Work failure. Full repair → resume → Work completion on final revision is open. |
| G6 | **PARTIAL.** Existing truthful WIC stop is not an irreparable Context Assembly stop. Required real Context Assembly failure/no-retry qualification is open. |

## Original 23 Closure Conditions

This table preserves the original completion definition; “selected” never means full Work PASS.

| # | Condition | Current status |
| --- | --- | --- |
| 1 | G1/G2/G3 root causes | PARTIAL; G2 live source absent |
| 2 | Document Context readiness | Scoped G1 positive; final source open |
| 3 | Document Candidate to legal Delivery | OPEN; Human authorization/acceptance absent |
| 4 | Revised Greenfield successor | OPEN; no accepted V1 |
| 5 | Non-new Work classification | Scoped G3 source resolution; full path open |
| 6 | No Protected Fact loss | Typed F01–F14 retained; consumer/governance coverage PARTIAL |
| 7 | Legal Context not incorrectly blocked | OPEN; G0/G4 fail and Guardian gap |
| 8 | Full repair convergence | OPEN; G5 full Work absent |
| 9 | Irreparable truthful stop | OPEN; G6 Context Assembly case absent |
| 10 | No unbounded retry/budget reset | Bounded test positive; live final-revision evidence open |
| 11 | No duplicate PWU/Task/Execution | Prior selected-case evidence; final path open |
| 12 | Exact Candidate/Revision/Verification/Guardian lineage | PARTIAL; Guardian governance evidence open |
| 13 | Human authority | Preserved; G1 decisions pending |
| 14 | Software production path | OPEN; G0/G4 full Work absent |
| 15 | F26 Guardian regression | Prior regression PASS; final image open |
| 16 | Related regressions | 43 directed tests PASS; full required gate open |
| 17 | Real ECS qualification | PARTIAL; no `c119332` runtime image/Work |
| 18 | Restart/recovery | Prior isolated Gitea restart scoped PASS; final recovery open |
| 19 | Preserve original history | Preserved; no original Work/Candidate mutation |
| 20 | Push task branch | Pending this report commit/push at capture |
| 21 | Keep production main canonical | Preserved at `ee5bd86a53891f9391785c91d0ccef81ad2d56c3` |
| 22 | Record workspace state | Task worktree on original branch; main workspace untouched |
| 23 | Persist complete qualification evidence | This delta is partial; final live receipts absent |

The approved architecture direction is implemented only for bounded static content checks. A Guardian-owned governance evidence contract and Human G1/G2 decisions remain external gates. **N1 remains PARTIAL; no Closure Condition is waived.** After push, tracked recovery is the task branch `docs/evidence/governed-production-context-convergence-v1/`; ECS durable copies are `/data/watt/app/owner-runtime/qualifications/governed-production-context-convergence-v1/` and `/data/watt/n1-qualification-20261008/app/owner-runtime/qualifications/governed-production-context-convergence-v1/`. Those copies require post-push SHA verification.
