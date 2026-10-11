# C3 — Native Context references and production recovery

## Checkpoint status

C3 qualification is IN PROGRESS. No C3 Closure, Human Integration, Acceptance or Delivery is claimed. Historical failures remain failures. This report will record the observed continuation, including any further blocker.

## Confirmed capacity cause and correction

The immutable G61 PWU contract contains the same 12 Formation/Review audit receipts at 24 locations. Its payload is 1,054,482 bytes, above the unchanged Native request limit of 524,288 bytes. This is a measured assembly failure before Provider submission, not a guessed token failure.

Source `c125ec674a7537e8cafe7da17fd20be1800fabb5` adds a lossless execution view of existing Owner history. Current requirements, original Fact values/order/Scope/qualifiers, source bindings, permissions and gates remain inline. Historical proposals and feedback are contract-scoped digest references with original locations; authenticated Owner reads return the complete retained records. The persisted original contract remains the governance/Verification/Guardian authority.

[Actual probe](real-g0-g61/native-context-projection-probe.json): execution view 118,960 bytes; complete request 142,090 bytes; original contract digest unchanged; exact round trip; 12/12 [actual Owner readbacks](real-g0-g61/actual-owner-evidence-readback.json). Foreign/missing references, contract drift and contradictory receipt identities fail closed. Oversized current requirements still fail. No new fetch tool, permissions, model retry or context budget was added.

The existing Resume control now makes the same queued Attempt available immediately. The old capacity wait's 2126 sentinel no longer prevents lawful operator resume; original usage, bindings, receipts and effects are preserved. See [control receipt](real-g0-g61/lawful-resume.json).

## Actual G0 progress

Existing Work `6ba2cffa-0bf3-565a-81e0-7f3c6696f21e`, PWU `48781eed-8ead-4fee-9d21-973055ef6653`, Attempt `de98f392-b8d1-40ac-a442-a283fa938060` were resumed, not recreated. Real Native inference completed seven steps and nine settled tool effects with nine receipts; Completion reached PRODUCED. Git proposed commit `43fa0621e0d0e06fd1b84c9b76e06b831a578d97`, tree `c9942900fd4ad60eff68f4133bbf57181390da1a`. See [execution evidence and actual usage](real-g0-g61/actual-worker-execution-chain.json).

The first content Verification failed downstream. Three EQUALITY Facts with legitimate qualified Scope were excluded from the existing independent content consumer solely because they were neither SCOPE nor future-Seal Facts. Their static plan consumer could not represent original qualifiers and exhausted its two-call budget. See [original-source diagnosis](real-g0-g61/current-content-owner-root-cause.json). Those receipts and the original FAIL are retained.

Corrected source `ce62ce24cb12913447d0671f54502cfaeaf2d9e5` selects the existing content Owner from reviewed current bindings. Direct deterministic checks remain conjunctive and can reject a wrong artifact despite an incorrect model approval. All original facts and independent gates remain unchanged. Provider versions identify the corrected implementation, permitting append-only re-verification on the same exact Git subject through the existing Verification service. No settled Native effect will be replayed.

## Further observed defects and continuation

Append-only ce62ce2 Verification correctly passed all 18 Fact/current gate checks, but the overall record remains FAIL (`9393c7c4-a032-5ef2-aae4-469e82ca9edc`). A mixed current-content/future-Candidate clause was judged from current-only bindings: its independently admitted Candidate Owner binding was not supplied to the content consumer. See [exact diagnosis](real-g0-g61-generation63/content-lifecycle-consumer-root-cause.json). The failed judgment is retained; no Candidate seal was invented.

Source `330a171e9dcfd48992da46f0c56dd0a29348870a` supplies related same-source responsibility bindings to the existing independent content checker, selects only current checks, validates original source identity, and binds replay receipts to both selected components and responsibility plan. Future Owner gates remain pending and must independently obtain actual evidence. Controlled missing-plan/source-drift negatives fail before admission; wrong current content still fails.

A separate isolated PostgreSQL reproduction proved Work projection chose the old NOT_ADMISSIBLE after an append-only corrected ADMISSIBLE Owner decision. See [retained pre-fix failure](projection-before-fix/receipt.json). The same source now projects the latest admissibility's exact referenced Verification records; missing references are UNKNOWN. Original records are not edited and historical FAIL is not a signal to replay settled Native effects.

Development regression: [180 checks](development6107/receipt.json), unchanged Guardian 46 checks, then [63 focused final tests](development6108/receipt.json). Frozen source 330a171 installed qualification passed 78 application and 46 Guardian checks. A test Session lifetime defect caused the initial PostgreSQL fixture to hang; its interrupted receipt remains non-PASS. The one-line test-only correction 0af98d9 recovered 5/5 PostgreSQL checks on the unchanged exact 2fe07c2 application image. See [initial fixture failure](generation64/owner-pg-initial/receipt.json) and [separate recovery](generation64/owner-pg-recovery1/receipt.json). Real continuation remains in progress at this checkpoint. These controlled results do not substitute for real G0 or Holdout.

The actual API restart then exposed a confirmed consumer mismatch: Steering paired all historical Verification references with only the current selected results. The old strict positional zip failed with three historical records versus two current results. [Actual startup failure](real-g0-g61-generation64/api-startup-failure.json) records source, image, container and exception; no corrected v4 Verification was run. Source `518fcf9f07c7ddfc9672dde431419af0412d58ed` binds current judgments to exact selected Owner IDs, retains all historical references and fails closed on missing, contradictory or unresolvable records. [17 focused development checks](development6109/receipt.json) passed. Its exact installed image and real same-Work continuation remain in progress; no historical outcome is changed.

## Exact identities and controlled qualification

| Stage | Source | Application image |
| --- | --- | --- |
| Native execution recovery | c125ec674a7537e8cafe7da17fd20be1800fabb5 | sha256:a0f7d82e3655b9cd4dbce21c2f5ef114296385e399b7dea5aea3610bb3f03592 |
| Corrected content Verification | ce62ce24cb12913447d0671f54502cfaeaf2d9e5 | sha256:a2e1339527deee9e89d73a41d9521fc8a40687d1ebad7fd0b8c2fedae56029c7 |

| Related responsibility plan / Work projection | 330a171e9dcfd48992da46f0c56dd0a29348870a | sha256:2fe07c269c6dc7b79e385cd0016bce04f297766cfa2317e6a4c3ec50a722dad9 |

Guardian `5c88ffb9318e68d11b0cfb2af38048e6452bf881`; ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`; migration `20261007_72`. The original execution Environment retained its independently observed c9bae501 image and immutable binding. Application image and execution Environment image are separate identities; no old image is relabelled.

Initial installed c125 qualification: 131/132 passed, one repository-resource fixture path failed. Exact installed resource byte comparison plus isolated single-test recovery gives 132/132 aggregate; original failure remains in [receipts](generation62/image/watt-qualified-aggregate.json). Guardian 46/46, PostgreSQL 4/4. Development regressions and installed qualification are distinguished; no fixture result substitutes for real Work or Guardian Assurance.

Corrected consumer development regression: 180/180 plus Guardian 46/46. Corrected installed regression: 273/274 passed, the same resource-path fixture failure retained and recovered separately on the same exact image, giving 274/274 aggregate. Guardian installed 46/46. PostgreSQL 24/24 passed on the exact installed ce62ce2 image, including unchanged source-identity and independent Guardian negative gates. See [PostgreSQL receipt](generation63/owner-pg/receipt.json).

## Cost and restoration

Actual Native usage: input 441,358; output 4,868; total 446,226; reasoning 4,038 (already included in output). Previous Formation usage remains separately recorded; no budget was reset. Append-only ce62ce2 Verification used three actual Provider requests: input 364,083; output 2,082; total 366,165; reasoning 0. Its largest request had 350,554 input tokens. This retained-history input cost is an observed P2 improvement opportunity, not an observed Provider capacity/transport failure, and does not justify interrupting production or increasing budgets. The Native capacity fix is specifically qualified for typed Native contract history; it does not claim every model boundary has completed context factoring. Provider monetary cost and cumulative CPU/memory consumption are UNKNOWN.

Public evidence manifests verify every downloaded file hash. Private complete Owner exports, model judgments and control state remain on ECS with restricted permissions, outside Git:

- `/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-qualification-20261010/native-context-recovery-generation62`
- `/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation62-qualified-20261010`
- `/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation63-qualified-20261010`
- `/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation64-qualified-20261010`
- `/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-qualification-20261010/native-context-recovery-generation64`

Recover from another computer by checking out the remote C3 branch and using authorized SSH to these persistent ECS paths. Local untracked files are not the only recovery source. No off-site backup or restore drill is claimed.

Production checkout/main, original incident Works, historical Candidates, Human Decisions and Quality Ledger were not modified. No Holdout was read or used to tune this implementation; it remains gated on ordinary G0 qualification.
