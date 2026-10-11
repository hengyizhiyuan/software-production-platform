# C3 Deterministic Identity Binding & Feedback Recovery

Recorded: 2026-10-11. Status: **identity/feedback correction qualified; C3 PARTIAL — exact Native context capacity blocker**.

## 1. What was actually wrong

The prior G60 Formation produced the correct component identity. The **Reviewer** changed one hex character when echoing that identity. Its raw Review was rejected and cannot be treated as an admitted semantic judgment.

| Classification | Evidence-grounded conclusion | Treatment |
| --- | --- | --- |
| A: model variance | Reviewer identity typo; two additional effect prohibitions proposed against different primary exclusion sources. | Keep strict rejection and existing bounded recovery. Do not invent source meaning or hardcode the case. |
| B: capability defect | The existing route-scoped Review already establishes ordered result slots, but still delegates exact identity/hash reproduction to probabilistic output. | Reuse exact persisted request slots deterministically, without supplying semantic answers. |
| C: governance blocker | Wrong explicit identity, source correspondence, permission, version or independent evidence remains inadmissible. | Preserve FAIL/BLOCKED and Guardian independence. |

Historical feedback was delivered with its original Wire/inventory/Attempt/receipt binding. Its first candidate failed **before Review**; the identity and cross-source errors occurred only during the second candidate's first Review. Therefore the earlier feedback cannot be accused of ignoring errors that had not yet occurred. Historical private HTTP serialization details and the model's internal reasons remain UNKNOWN. See [pre-change diagnosis](diagnosis.json) and the [prior preserved report](../formation-feedback-consumption-20261011/report.md).

## 2. Minimal correction and exact identity

| Owner | Frozen commit | Git tree |
| --- | --- | --- |
| Watt | `ca891e0c85371ccce6b6164c735a65b2a97b4ac2` | `5c0e099b212eab4d49468a50192311af5ba16e80` |
| Guardian | `5c88ffb9318e68d11b0cfb2af38048e6452bf881` | `df757ab48aac8928896e3f17619e64a7642a6ea3` |
| ECF, unchanged | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` | `878d39d9c259272bb05f2e02bdf9d60c22fad460` |

Actual new image: `sha256:c9bae501ed17987f4513b09237a801c0115e2f231270536d564badabb2d30afb`. Previous application: `9f9c94d8ebba6138d8e818ea5d368c4a376ad788`, image `sha256:f04fd82180952051b85f7678f05c110b5e6cff84a097a58e24aa3d8c67f047e5`. The new image was built from exact archives; installed qualification and real roles use it without application source overlays. See [build](generation61/image/build.json), [actual imports](generation61/image/actual-imports.json), and [actual environment observation](real-g0-g61/actual-production-environment-image.json).

- Watt [provider](../../../../src/spg/providers/fulfillment_candidate.py): explicit `null` in existing Review identity operands reuses the corresponding exact ordered request slot. Persisted binding authenticates original raw bytes/fingerprint, inventory, candidate/components, slot table and actual model request identity **before decoding**. Missing operands, duplicate JSON keys, wrong explicit identities and cardinality drift are rejected. No verdict, reason, authority or evidence is supplied.
- Watt [existing fulfillment Owner](../../../../src/spg/application/governed_obligations.py): persists slots before Review and independently reconstructs the current basis during replay/feedback validation. Receipt, request, slot or Wire drift stops without another call.
- Guardian `src/guardian/runtime.py::_component_plan_evidence`: independently resolves real Owner records and recomputes the same binding. Its narrow compatible extension resolves only identity operands; it does not accept Watt PASS as Assurance.
- Full-identity legacy responses retain their previous set-based ordering semantics. The canonical Review remains strict. No new Formation Wire version, index space, semantic alias, Owner, retry or budget was added.

## 3. Focused qualification

| Exact installed-image gate | Result | Wall seconds | Receipt |
| --- | --- | --- | --- |
| Watt identity, feedback, formation repair, source correspondence and route-scoped Review | 127/127 PASS | 255.2725 | [Watt](generation61/image/watt-continuation-receipt.json) |
| Guardian independent evidence, identity/slot/request tampering and legacy compatibility | 46/46 PASS | 45.6209 | [Guardian](generation61/image/guardian-installed-receipt.json) |
| PostgreSQL persisted rejected Review → feedback → replay; identity slots and JSONB ordering | 3/3 PASS | 144.9965 | [PostgreSQL](generation61/owner-pg/receipt.json) |

Migration: `20261007_72`. These are controlled regressions, not software Work PASS. Coverage preserves negative semantic verdicts and rejects missing/wrong identities, raw fingerprint/request/slot drift, incorrect source/evidence and replay corruption. See [Watt tests](../../../../tests/test_c3_review_identity_binding.py) and exact Guardian test archive receipts.

Earlier failures remain published: [development-6101](development-6101/receipt.json) had 90 PASS / 13 FAIL: 12 test-harness mistakes and one introduced legacy positional-compatibility defect. These were corrected before freezing; [6102](development-6102/receipt.json) and [6103](development-6103/receipt.json) preserve subsequent results. The first final-image Guardian controller mounted a nonexistent test directory: [original receipt](generation61/image/guardian-receipt.json), exit 4 / zero tests. The corrected controller used verified frozen tests in the **same image**, resulting in the 46 PASS above. None of these failed receipts is counted as PASS.

## 4. One new normal-entry G0: real recovery and progress

Original input file SHA256: `c587f020c43275019b32c49a94ab8559587a01d339e1fe97b2c8e048a386258e`; text SHA256: `a47cd835924ba5082397fd8d1e3fb0ab2805f6336f365f9af6db27272e4cced9`. No facts, decisions or successful outputs were inserted manually.

| Identity | Actual value |
| --- | --- |
| Product | `0c1c6935-d8ff-484f-a8a5-b6d562b2e7ab` |
| Work | `6ba2cffa-0bf3-565a-81e0-7f3c6696f21e` |
| Work Reality | `dc748198-84bc-5cd5-a74b-ea0bb2ab57b3` |
| Inventory | `57b6dd706dfc1f56c7066660add814c7728d17e9096e2347ff1bd4db3989d604` |
| Product V0 source / tree | `084c6f17e2f2625952e4cf6fc3825999410eebc7` / `f736c0aab63f1c66b8fe70f7dc602832072079eb` |
| Production Run | `94e42d44-5291-49a0-a172-29ffd70940c0` |
| PWU | `48781eed-8ead-4fee-9d21-973055ef6653` |
| Attempt | `de98f392-b8d1-40ac-a442-a283fa938060` |
| Native contract | `21df8cf4-5fbc-5316-b5ca-c47e42a085c9` |
| Database | `spg_c3_bindingg0g61_qualification_20261010` |

The initial Product POST timed out at the unchanged 20-second client boundary. Read-only reconciliation proved one exact Product and zero Works at that point. The same Product was adopted and **only the previously unattempted Turn** was submitted. Product creation was not repeated; one G0 Work was created. See [reconciliation](real-g0-g61/product-outcome-readonly-1.json) and [controller recovery](real-g0-g61/controller-recovery.json). Timeout cause remains UNKNOWN.

Actual formation progression:

1. Formation 1 passed structural prerequisites. Review 1 resolved 3 header, 18 source and 32 component/capability identity slots exactly; its output was **not admitted**, failing `OBLIGATION_SOURCE_CONSUMPTION_ABSENCE_CONTRADICTED`: the critic claimed a matching submitted consumer was absent. Its raw output contained six negative source and ten negative component results. These are unaccepted model judgments, not proof that all those first-candidate requirements were intrinsically invalid. This is A runtime Reviewer variance correctly rejected by the existing contract, not a reason to weaken that contract.
2. Existing feedback receipt `a5c5292e-773c-4db5-bc19-06c0b0c04539`, fingerprint `bb0668a4dab43131c8cda5722c26d8eb129c9f5a2b8e9a9b7de8a947ce1ca40c`, was bound to the original Wire and consumed by Formation 2.
3. Review 2 resolved 18 source and 28 component/capability slots exactly and passed. Independent validation receipt: `1bb09466-83d9-4694-a631-f91d335e0ec8`. Terminal fulfillment receipt: `0dbf7c9f-a35d-44c2-a45a-02f4f9103896`, `VALIDATED_PROJECTION`.
4. Production Run, PWU and Attempt were created; the actual Worker was allocated, started and passed Workspace preparation. Worker identity: `watt-c3-bindingg0g61-real-worker-20261010`. Workspace event: `7a7ac00c-22bd-4422-9587-5e6ca4631e0c`.

Thus the existing **two Formation / one feedback / two Review** recovery budget actually converged and production advanced beyond Review. The accepted fulfillment projection is **not a sealed software Candidate**. See [bound model/feedback evidence](real-g0-g61/identity-convergence-review.json) and [actual stage counts](real-g0-g61/runtime-stage-observation-20261011T084659.json).

## 5. New downstream blocker, not the former identity failure

The Worker returned at `2026-10-11T08:37:59Z`, event `eedfe94a-8873-4822-97f7-ae24c351925c`, before Native inference/audit submission. Queue state is `WAITING_RESOURCE`, non-retryable; available-at sentinel is `2126-09-17T08:37:59.574415+00:00`. Work projection remains `RUNNING / WAITING_PRODUCTION`; this is a nonterminal resource wait, not Work PASS or final Work FAIL.

Confirmed **B capability defect**: complete proof receipts are copied into the executable PWU contract and then injected as exact Native context:

| UTF-8 compact JSON part | Actual bytes |
| --- | ---: |
| Entire PWU contract payload | 1,054,482 |
| Fulfillment bindings | 543,705 |
| First binding's formation receipt | 506,700 |
| Production plan | 478,655 |
| Plan's 12 inline formation/review receipts | 475,244 |
| Unchanged Native context limit | 524,288 |

The same 475,244-byte receipt sequence is carried under the binding proof and the production plan. The exact installed assembler reproduces `NativeContextCapacityError` even with **zero tools, previous results or checkpoint**. Contract/binding digests were verified. This is measured byte capacity, not a guessed Provider token limit or model response failure. See [capacity proof](real-g0-g61/native-context-capacity-review.json), [contract construction](../../../../src/spg/infrastructure/executor_runtime/native_compatibility_executor.py), [receipt propagation](../../../../src/spg/application/governed_obligations.py), [Native context](../../../../src/spg/executor/context.py) and [pre-inference call order](../../../../src/spg/executor/kernel.py).

The fresh isolated database contains zero Native execution steps/effects, completion/verification records and software Candidates. Applicable real Guardian Assurance was **not reached**. Installed Guardian regression PASS cannot replace it. Human Integration/Acceptance/Delivery were not granted. No Holdout was opened. The passive GET observer was stopped only after this exact wait was proven; exit 137 is an observer termination, **not the Work result**. See [observer receipt](real-g0-g61/terminal-observer-stop.json).

Next necessary engineering work is a bounded **Native execution-context representation** correction: retain complete immutable Owner proofs and independent Guardian consumption, while preventing historical formation/review transcripts from being duplicated into the executable context. Prove that every current objective, protected Fact, scope, qualifier, permission and gate survives any derived view and that missing/drifting proof references fail closed. Do not raise the envelope, delete original receipts, rewrite this contract or create another trial without that proof. This correction has **not** been implemented or qualified by this identity/feedback task; the remaining blocker is explicit, not reclassified as model variance.

## 6. Cost, persistence and remaining qualification

Formation/Review actual subtotal: 4 logical calls, **248,248 input + 21,117 output = 269,365 tokens**, reasoning 0, Provider time **76.5609 seconds**, transport retries 0. New image build wall time: **390.7448 seconds**. Native production inference was not sent because assembly failed first. Other Work model usage, total monetary cost and cumulative CPU/memory usage: **UNKNOWN**. Diagnostics made no model calls.

Public receipts/manifests are retained in this directory and pushed on `codex/c3-open-semantic-obligation-convergence`. Application source and later evidence HEAD are separate identities. Private raw outputs, canonical Owner exports and controls remain on ECS:

- `/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-qualification-20261010`
- `/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-controls-20261011`
- `/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation61-qualified-20261010`

Final canonical export SHA256: `164c6d045f239c2b1f08f67e9263efdad70e62e62a2d037de2446f68d2164119`, captured `2026-10-11T08:53:29.358692Z`; exact private path is in its [export receipt](real-g0-g61/owner-export-20261011T085258-8c2eaf6c529847198b60f69247ea3f2d.json). The [protected-boundary receipt](real-g0-g61/protected-boundary.json) confirms unchanged production checkout/main refs and the historical G60 canonical hash; it does not claim a complete external-effects audit.

**C3 is not CLOSED**: actual Native software production, Git output, Verification, software Candidate and applicable Guardian boundary remain unqualified; independent Holdout stays sealed. No historical failure was promoted to PASS, and no C4/N1/N3 work was started.
