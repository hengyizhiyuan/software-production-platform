# Real G0: Review receipt identity correction

## Exact failed observation

- Work: `9339266e-8a99-58e6-9cda-fcf2a81594d0`.
- Application: `51e41c113076711bcdc7a3ca6dd071c3cbb2eff8`; image `sha256:19b086d553e631e0c019efddbe58465cf8221d81d64c23e7dfa3c5fbcb373c4d`.
- Work Reality: `5703321f-15f7-5ec6-b58e-e16a1d87e288`; source baseline `c4a506deea224c556ef2ac49335648e189c1e6c3` (not the application revision).
- Inventory: `aaee66b12f8784559c376283de3d020f30b4602c466a746e1127f7e1ba7faf7f`, 20 sources, 28 routes in each Formation.
- Canonical read-only snapshot SHA256: `c02850bc25e17fe8c2395cd26fba2de57a5c9df5822fc6a1d2abe01228f08fe6`.
- Second Review observed receipt: `4ac982b1-f323-404a-a0ee-362dae854f79`; raw Wire SHA256: `9694a747df170255889c4fa9abbf3a2a571dae6f350ec114d5b8326c7bbe3c43`, 25100 bytes.
- Review validation receipt: `37dd15aa-65b9-4649-b261-af1e72fd47b9`, rejected `OBLIGATION_SEMANTIC_COMPONENT_MISMATCH`.
- Terminal receipt: `2f76867e-4a72-48f4-a56f-333c33ebfd34`, `OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT`.

## Proven B defect and bounded correction

Read-only reproduction on the exact installed failed image located `_semantic_repair_observation` at line 2763. Raw Review consumption checks for source ordinals 0 and 2 omitted optional `target_paths`; the existing typed contract persisted their default `[]`. All explicit fields and Wire identity matched; parsing by the already-used typed contract reproduced the stored Review exactly. Comparing raw JSON with the typed serialization falsely classified these existing defaults as identity drift.

Watt now restores only existing optional consumption-check defaults (`target_paths=[]`, `source_component_quote=null`) after independently verifying the original raw Wire digest, byte length, receipt lineage, Candidate, components, Inventory, and Attempt. The shared helper is used by both rejected-review feedback and positive admission. It preserves every explicit field and does not use typed coercion to turn a string verdict into a boolean. Guardian independently restores the same defaults from resolved original Owner Wire, with required digest/length/retention proof. Explicit targets, verdicts, permission, Scope and source references are unchanged. No new Wire version, Fact index, budget, retry, Owner or authority.

Initial correction: Watt `f07eef6339018ea13552df958945fa756ee4bf77`. Exact-image PostgreSQL qualification then found the same comparison defect at positive admission (generation57: 1 PASS, 2 FAIL). Watt `3cd4b6d56b92b83b306cde60bf99012745d64d8f` joins that path to the shared helper; final `881c2c303083be149594f9d79659a037853e302e` preserves explicit verdict types. Guardian `88f5ac35a6d48fb1aace24f94a2100708864e0be`; ECF unchanged `5aa4f8833c359c15bd059eda5972aa3915bcc18c`. Generation59 final-image focused tests: 39 PASS; PostgreSQL/Owner: 3 PASS. Earlier failures remain retained, not converted to successful receipts.

## A variance and retained rejection

The first Formation omitted target operands from three current content routes. Exact original feedback was delivered to the second request; all three necessary-binding failures were repaired. The second Candidate reached independent Review. Review rejected two source/component interpretations: unresolved qualification framing, and claimed insufficiency of the content method for structure/cardinality.

Original IR marks both clauses as current explicit production requests. Current content remains structurally expressible; the content consumer contract already declares static structure and original requested outcomes. This observation does not prove an absent platform capability. The submitted UNRESOLVED route cannot be admitted; the critic's semantic judgement cannot be replaced by Watt or assumed universally correct. No rule or alias is added for either example. Review failure remains failure after the receipt correction.

Formation and Review responses all completed normally, reasoning tokens 0, transport retries 0. Formation totals: 97388 tokens, 19.980794494 seconds. Review: 86992 tokens, 23.023160677 seconds. Combined observed scope: 184380 tokens and 43.003955171 seconds. WIC/design/whole-Work cost: UNKNOWN.

No PWU, production run, Native Attempt, Verification or sealed Candidate existed at the terminal snapshot. Product/source initialization from normal entry is retained. Only the passive GET observer was stopped after durable stop; no Work cancellation or historical mutation. No Holdout execution.

## Evidence and recovery

Safe Owner observations, runtime identities and original feedback metadata: [real-g0-g55](real-g0-g55/). Classification probes make zero new model calls; their zero-call counters do not describe the original Work's three real calls.

Private canonical snapshot and original outputs are retained under `/data/watt/c3-semantic-convergence-20261009/binding-g0-generation55-qualification-20261010/private/`; safe summaries and manifest give exact paths/digests. These remain private and are not copied into Git.

Development validation: Watt 114 PASS (5415 and 5416, same focused suite); Guardian 178 PASS (5417). The 5416 Guardian runner had a test-node setup error and collected zero tests: retained as a failed controller receipt, never counted as PASS. These source overlays are development proof only. Exact-image and PostgreSQL qualification follow separately.

Final-image zero-model historical replay: [replay receipt](generation59/historical55/replay.json). Historical Review rejection and terminal receipt are preserved. A controller-name collision failed before process startup; its separate [recovery receipt](generation59/historical55/controller-recovery.json) records the unique replacement controller without deleting the prior container or making model calls.
