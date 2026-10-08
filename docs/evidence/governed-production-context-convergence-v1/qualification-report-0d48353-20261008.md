# N1 qualification report — 2026-10-08, final tested application source

Captured 2026-10-08 11:50 UTC. **Overall PARTIAL / OPEN. Do not close N1.** This is a new report from current isolated ECS reality, not a recreation of missing old-computer receipts. Evidence grade **A** means persisted isolated PostgreSQL event/contract plus exact immutable Git identity or downloaded bytes; **B** means live API projection or exact-source isolated regression; **UNKNOWN** means no recoverable historical fact. A Verification PASS is scoped to its admitted obligations and is never full Work PASS by itself.

## Identity, isolation and preservation

- ECS `i-0jl386xnbauudq5j9jk0`, `cn-wulanchabu`. Application source tested: `0d4835353dbdb38abd6abfc19127b84eb5544475`; isolated image `sha256:64289d0a086ecf03efb2dae24ab036bd83906905e00fd71fa30fc51feb160709`. The image was built offline by overlaying exact Git `src/spg` on the previously isolated dependency image. Isolated API, Coordinator, Worker and Tool Host all ran that digest; PostgreSQL database `spg_n1_qualification_20261008`, dedicated Gitea `watt-n1-gitea-20261008`, qualification Product/Work repositories and Docker workspace volume were separate from production. Mounted ECF/Guardian Python source hash manifests were `48b10918282db55267b86fceb355c5d87c8bb29b5761bf38dbca10d2a53df7d5` and `5931bfa3488d6af25ac27a7527ec6a0c749043387608b508c958a06b6554683f` respectively; these mounted directories are not Git checkouts.
- Production `/data/watt/runtime/source` remained clean at `ee5bd86a53891f9391785c91d0ccef81ad2d56c3`; production service containers were not restarted. Local `D:\hy\software-production-platform` remained clean on `feature/production-environment-foundation` at the same commit. N1 code and reports were edited only in `C:\Users\yuchunbo\.codex\worktrees\governed-context-convergence\software-production-platform` on `codex/governed-production-context-convergence-v1`.
- Original G1 Candidate `7d410081-4319-5529-a12e-ce844f9d9ac2` remained SEALED with unchanged fingerprint `f2fa919001abb1b5af8dc14a34a9991fc25d725ec5164b16bdae89433879c7d5` and zero Human authorization. Original failed Works, Candidate Git objects, decisions and Quality Ledger were not modified. Historical events absent from persistent Reality remain **UNKNOWN**.
- Credential exposure categories and controlled rotation sequence are in `credential-exposure-inventory-20261008.md`; no secret value is repeated here. No production credential, configuration or service was changed.

## G cases on the exact tested image

| Case | Grade and observed result | Open obligation |
| --- | --- | --- |
| G0 | **A, FAIL / PARTIAL.** Product `d1b0ec92-9d8c-470d-bf20-624680129fb3`, Work `290e71df-bb46-5298-9a27-77e0091ba440`, run `01def535-d49b-4656-87ae-77f36534bfbf`: one real Worker attempt, then `preview.inspect` effect `ValueError`, Self-Refine `LOCAL_OBLIGATION_RECOVERED` followed by final `FAILED`; no Verification/Candidate. Independent short case Product `c4c9dbbd-f283-40db-be9d-74615da77fd9`, Work `6899ad34-73f1-5180-8323-f1559dd9cc8f`, run `841e3280-0706-43e2-8385-caa87206829f`: exact H1/paragraph/diff checks passed, but `PATH_SCOPE` `ca50583d-a863-5fee-94cf-f03467d5e921` **FAIL** on unconsumed `page.index_file`; no sealed Candidate. | Final-revision normal Greenfield Work PASS and reliable semantic consumer contract. Neither trial is PASS. |
| G1 | **A, qualified Candidate only.** Product `252cce32-842b-4da7-b998-3ca04237c501`, Work `044f0268-f9cc-5663-a145-ea4d30b8e5bb`, PWU `6f7c9329-8e9f-4ccd-b69b-4511529bac05`, run `6f32fe5b-1450-49b4-8ee8-3632be67882f`, new SEALED Candidate `695cc730-849a-5dce-88da-c62c19c9f6b8`, Verification `e0b16874-f96f-5e38-964b-73301e4bc3c8` **PASS**. Four literal historical IDs are nonempty PWU `required_markers`, present in the exact file, and independently checked. New negative Candidate regression omitting the Semantic IR ID **FAILS**; reversed sections FAIL. Guardian `NOT_STARTED`, `required=false`. Exact review is `g1-new-candidate-human-authorization-review-20261008.md`. Earlier final-image G1 Turn `324f4a48-46d6-4f07-aace-9dd4a61685b5` failed Context Budget after creating READY Work `8206dda8-5cb0-580a-9224-d54c03f5d122`; it was not retried or counted PASS. | Exact Human Integration Authorization for the new Candidate, subsequent trusted Runtime Commit, Document Package Manifest and separate Human Delivery Acceptance. None was fabricated. |
| G2 | **A, BLOCKED.** Read-only isolated `product_source_versions WHERE version>0` count **0**. The prior fixture V1 regression is B evidence only. | A real Human-authorized and accepted V1 source, then revised Greenfield successor Worker/Candidate and complete governance. |
| G3 | **A, scoped positive / Work still at Human boundary.** Existing Product `d1b0ec92-9d8c-470d-bf20-624680129fb3`, new bounded Work `e50a9566-155c-5843-93fd-9b7ec800df7d`, run `9fa07cdd-a8e9-4a63-a280-b3345f4de438`. Natural-language “currently accepted Product V0 source” resolved to the unique persisted source revision `c37c2e366650935dde62ef48a6b54a621337a27c`, `REPOSITORY_OBSERVED` with `product-source:d1b0ec92-9d8c-470d-bf20-624680129fb3:0`; real Worker produced SEALED Candidate `3d612a3e-bac9-54c9-8a3f-078a981c3362`, exact file `status-v0.html` SHA256 `cb289ddbaa0886aa1f602775467a9353ea715c8d8b09239ddb01ea843e6dc016`; `PATH_SCOPE` `81fd3068-58c0-54d2-9263-78eaab267088` and Git diff `004230ff-36db-55f2-a96f-c9e2db574f46` **PASS**. Zero Human authorization. | Integration/acceptance and a broader producer/consumer seam assurance; this is no full Work PASS. |
| G4 | **A, FAIL / PARTIAL.** Product `d9a37f3b-5847-4148-94d6-aeda2ec17f7a`, Work `c616ab6b-d985-5b35-a2c4-47d9b79ad4e7`, PWU `26d38fa0-0f11-41a8-8c87-52f100a4f388`, run `acb9e95a-0b75-4675-8136-9a64746c1119`: exact Human F01–F14 ordered values survived Work Reality, Task and CompletionContract under fact `7b610ed7-bb57-54fb-88cc-4a4b10bdc6cb`; exact Candidate blob ordered-list check passed. `PATH_SCOPE` `2c650693-cbe6-50b4-a0a5-ab6019a57eff` **FAIL** because `acceptance.ordered_list_items` scope `index.html ordered list` was not consumed as the exact target. Other facts remained outside the checker. No sealed Candidate. Earlier original nine summary Work constraints are not fourteen separate fact identities; the lossless typed tuple is the per-item engineering fact. | Correct WIC/IRK/ECF/Verification consumer contract; no claim of all Protected Context. Architecture Finding filed separately. |
| G5 | **A, PARTIAL.** In G0 Work `290e71df-bb46-5298-9a27-77e0091ba440`, Self-Refine event `37f0da00-7eb6-44cb-9a10-c0db46399e20` reported bounded `LOCAL_OBLIGATION_RECOVERED`, but later tool effect event `5bdf6dd0-802b-4c52-8352-6665de6ca1d0` ended `FAILED`; no Candidate or full Work completion. Earlier G1 local recovery evidence also does not substitute for Delivery. | A real repair → resume → **complete** Work with all obligations. |
| G6 | **A, bounded WIC stop only / PARTIAL.** Product `f95a3a92-9e01-44e9-9e48-71429d03650e`, Interaction `4a5ccac0-2dd8-4c05-8153-dad7c56c37d3`, Turn `67236529-2820-410d-ba86-c015e699efde`: user-visible `FAILED`, `InteractionInvariantViolation`, “WIC ordered page values differ from exact Human constraints.” Recheck found zero Work and zero runtime bindings; no automatic retry or forged PASS. | This is a WIC exact-value stop, **not** the requested irreparable Context Assembly failure. A dedicated real G6 Context failure with truthful terminal Work state and stable no-retry evidence remains open. |

### G4 individual Human constraint trace

The original Human record `367c2a56-0c4d-413b-b69f-63706e11eb1d`, assessment `5e4f0cc9-9ddd-4f2a-983c-7784eb1acdfd`, original Work `4a9f9064-d307-5261-a1c5-e734a52db4bf` and nine Work summary constraints are retained; see `g1-g3-g4-root-cause-trace-20261008.md`. On the final-image case above, each item below is an exact element of the single Human-authorized `ORDERED_COMPONENT` fact, in the same position in Work Reality, Task, CompletionContract and Candidate `li` parsing. This does **not** mean 14 ECF protected objects exist. The final `PATH_SCOPE` remains FAIL, so the last column is only a scoped exact-list check.

| Item | Exact Human value | WIC/IRK → Task/PWU position | Exact blob list check |
| --- | --- | --- | --- |
| F01 | `F01: N1 protected fact 01` | 1 → 1 | position 1 |
| F02 | `F02: N1 protected fact 02` | 2 → 2 | position 2 |
| F03 | `F03: N1 protected fact 03` | 3 → 3 | position 3 |
| F04 | `F04: N1 protected fact 04` | 4 → 4 | position 4 |
| F05 | `F05: N1 protected fact 05` | 5 → 5 | position 5 |
| F06 | `F06: N1 protected fact 06` | 6 → 6 | position 6 |
| F07 | `F07: N1 protected fact 07` | 7 → 7 | position 7 |
| F08 | `F08: N1 protected fact 08` | 8 → 8 | position 8 |
| F09 | `F09: N1 protected fact 09` | 9 → 9 | position 9 |
| F10 | `F10: N1 protected fact 10` | 10 → 10 | position 10 |
| F11 | `F11: N1 protected fact 11` | 11 → 11 | position 11 |
| F12 | `F12: N1 protected fact 12` | 12 → 12 | position 12 |
| F13 | `F13: N1 protected fact 13` | 13 → 13 | position 13 |
| F14 | `F14: N1 protected fact 14` | 14 → 14 | position 14 |

## Regression and original Closure Conditions

On exact source `0d48353`, 70 directed unit tests, eight PostgreSQL/Guardian/Multi-PWU integration tests, and the dedicated Gitea restart/accepted-source isolation test passed. The Gitea test restarted only `watt-n1-gitea-20261008` and preserved its independent volume. The exact negative G1 test creates a new isolated Git Candidate lacking one required ID and obtains Verification FAIL. These regressions are **B**, not substitutes for missing live Work outcomes.

| Original Closure Conditions | Current result |
| --- | --- |
| 1 G1/G2/G3 original root causes; 2 Document Context readiness | **PARTIAL / PASS scoped**: G1 vacuous marker chain and G3 source provenance root causes proven; G1 new Work reached Candidate. Full G2 live root/closure remains open. |
| 3 Document Candidate → legal Delivery; 4 revised Greenfield; 5 non-new/bounded classification | **OPEN / OPEN / scoped G3 positive**. G1 awaits separate Human gates; no accepted V1 exists. |
| 6 no silent Protected Fact loss; 7 legal Context not incorrectly blocked | **PARTIAL / FAIL**: typed F tuple survives, but G4 consumer mismatch and G1 long request budget failure remain. |
| 8 full repair convergence; 9 irreparable truthful stop; 10 no infinite retry/budget reset | **OPEN / OPEN / selected boundary observed**. G5 incomplete, G6 only WIC stop; no budget was enlarged or protected fact deleted. |
| 11 no duplicate PWU/Task/Execution; 12 Candidate/Revision/Verification/Guardian lineage; 13 Human authority | **Selected-case scoped / partial / preserved**. No Human decision was fabricated. |
| 14 software path; 15 F26; 16 related regression; 17 real ECS qualification | **FAIL / PASS regression / PASS selected regression / PARTIAL**. G0 and G4 final live paths did not pass. |
| 18 restart/recovery; 19 original history; 20 branch push; 21 main unchanged; 22 workspace state; 23 evidence persisted | **Scoped restart PASS / preserved / code branch pushed / preserved / recorded / this new report and ECS copy required**. Full N1 evidence closure remains open. |

## Cross-computer recovery and authority boundary

Tracked recovery location: branch `codex/governed-production-context-convergence-v1`, directory `docs/evidence/governed-production-context-convergence-v1/` on the remote. ECS durable qualification location: `/data/watt/app/owner-runtime/qualifications/governed-production-context-convergence-v1/`; isolated API writes are also retained at `/data/watt/n1-qualification-20261008/app/owner-runtime/qualifications/governed-production-context-convergence-v1/`. Exact isolated PostgreSQL database, Gitea repositories, Work Git commits, events and Quality Ledger remain in place. No production rotation, deployment, Runtime Commit, Manifest or Human Delivery Acceptance was performed by this report.

The feature branch report commit may be newer than the tested application source commit; only documentation/evidence changes follow `0d48353`. Do not treat that Git HEAD difference as a new app image qualification. N1 Closure Conditions are **not all met**.
