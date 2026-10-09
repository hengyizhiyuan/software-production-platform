# C3 — Fulfillment Stop / Prior-Runtime Admission Review

- Reviewed at UTC: 2026-10-09T13:31:10.978766+00:00.
- Implementation: Watt `d8ea0642f0c360794e69c366e8f15fa369eeed0b`.
- Scope: existing Work-governance formation → Steering Production admission → existing `BLOCKED` caller. Guardian and Native contract guards are unchanged by this repair.
- Status: **controlled stop regression qualified; C3 / N1 remain PARTIAL**. This is not Provider recovery or a real Work PASS.

## 1. Actual historical failure retained (E1 scoped observations + E3 code)

The original retry Work `048189aa-0613-5307-b6f4-c430e7977f93`, Reality `332a3a38-8719-580c-a1a2-c331ae14a5ae`, ran Watt `91f5dbc9906d1f857113736981517c1091ec52ae` in image `sha256:6f8d9b3a27e7e2452097a77427115df6e09b9a03276eb72d0170a66160e0578f`, database `spg_c3_retry1_qualification_20261009` / migration `20261007_72`.

The actual `MODEL_REQUEST_PENDING` receipt `2f5111b7-c478-42bb-b670-31d624d61568` preceded terminal, failed `CANDIDATE_VALIDATED` receipt `804b22c0-dcff-4a98-a870-0b7bd6905b29` with `OBLIGATION_FORMATION_TRANSPORT_ModelProviderError`; every binding remained `UNRESOLVED`. No model response or semantic review observation was present. Specific Provider kind, numeric usage, request identity and transport retry count are **UNKNOWN**; elapsed time does not prove timeout.

Known unresolved formation was then incorrectly allowed to create ProductionRun `f9f06c0a-b5fd-41c4-8e09-594cb91ea029`, PWU `395f75c3-6bbb-4028-8565-7a227f4adf04`, Attempt `f5026ead-1f51-4795-935a-85d4045547d4` and Dispatch `106b2585-8205-4244-a736-89f10906e486`. The existing Native validator correctly rejected `OBLIGATION_PROJECTION_UNRESOLVED` before Native binding/Queue/Worker. The orchestration path classified this as generic infrastructure failure. Verification, Candidate sealing and Guardian were not reached; missing Guardian evidence is not the cause of this failure.

Authority: [actual terminal review](retry-1/real-g0-terminal-review.json), which links the unchanged canonical Owner snapshot and captured trace. Design's earlier `LOCAL_OBLIGATION_RECOVERED` event remains only a local scope recovery, not formation or Work success. This repair does not resume/reset that Work or rewrite its history.

## 2. Minimal existing-Owner repair (E3)

`SteeringProductionService._production_contract` checks the returned complete bindings immediately after governed formation and before Planning or `create_initial_runtime_spine`. Any `UNRESOLVED` binding stops this new admission. Native's strict validator is preserved as its independent later consumer check.

The stop uses existing `RuntimeStore.insert_governance` / `governance_for_subject` under the Work row lock. `WORK_FULFILLMENT_STOP_OBSERVATION` / `WORK_FULFILLMENT_STOP_BASIS` is an idempotent observation with a deterministic identity for the exact Work, Reality, Steering Step, baseline/revision, inventory, source refs, unresolved refs and Formation receipt refs. The existing authority is `work-governance:derived-candidate-observation`; `candidate_is_authority=false` and `runtime_admitted=false`. Known sensitive values are scrubbed by the existing receipt helper.

Its distinct decision/subject type cannot enter the Formation `WORK_FULFILLMENT_OBSERVATION` stage query, change the prior terminal record or reopen its budget. A missing terminal receipt remains an unresolved stop with no invented evidence.

`FulfillmentProjectionNotReady` is a local application exception compatible with the existing Product invariant exception hierarchy. `PlanSteeringDriver.activate` handles it specifically and returns the existing `BLOCKED`. It does not call Provider-retry handling, convergence escalation, Human Attention creation or Self-Refine recording. No candidate repair, model attempt, successful recovery, Human decision or permission is claimed by this observation.

Existing lawful `BOUND_PENDING_EVIDENCE` and `RETAINED_CONTEXT` dispositions are not rejected by this stop predicate. Existing Candidate/Human/Delivery gates retain their authority; this repair grants no future authorization. Legacy empty binding behavior and existing Runtime binding reuse are unchanged. No Owner, schema or parallel lifecycle is introduced.

## 3. Controlled regression evidence (E2; not live model / real Work)

[Actual development receipt](dev-terminal-fix-1/watt-receipt.json), [JUnit](dev-terminal-fix-1/watt.xml), [frozen source-file hashes](dev-terminal-fix-1/development-inputs.json) record a Linux, network-disabled process with no database, credentials or real Provider calls:

- 15 PASS / 0 failure / 0 error / 0 skipped; exit 0; wall time `17.62009230896365` seconds.
- Snapshot base `f20b57c1f89f84cec7aa5f14d698480d9859a1f9`; exact source archive SHA256 `76f71a41dedf57810e3ee3d1be96d28f582c2a0de7e065e7455ac774a9ca3ae6`. It was a development source snapshot, not an installed final-image qualification.
- Four prior-admission tests use real formation/projection helpers with declared controlled Provider/store fixtures: terminal failure stops before Planning/Runtime; identical replay makes one candidate call and one stop observation; partial unresolved/no-receipt still stops; lawful routes retain the original Completion Contract; caller does not refine, escalate, create Human authority, retry or reset.
- Nine typed Provider-failure tests and two prior pending-outcome/transport-budget nodes cover safe failure metadata and unchanged terminal replay. Numeric usage is kept unknown where the normalized exception has no numeric data.

The fake Owner store tests demonstrate the application behavior and calls to the existing persistence API. They do **not** constitute a newly executed PostgreSQL Work, actual persisted production stop, full effect audit, Guardian qualification, Provider availability proof or end-to-end G0 PASS. A final installed-image regression is a separate root-owned receipt; this review does not anticipate its result.

## 4. Remaining boundary

The actual Provider failure remains unresolved pending an authorized evidence-based diagnostic or independent recovery. No new random G0 Work is created to seek success. C3 production qualification, independent holdout permission/execution and N1's original remaining obligations stay separately reported; this scoped repair cannot close them. Original production/main, failed Work, Candidate/Human histories and Quality Ledger remain outside the repair.
