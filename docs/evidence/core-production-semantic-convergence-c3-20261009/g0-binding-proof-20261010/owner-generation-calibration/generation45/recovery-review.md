# Narrow recovery classification review

## Recorded outcomes

The exact `fe45aa9993d795e7a58ba1e03229bdc41002834f` application image is `sha256:e3c040cb479c399742604ce0d26c76320aa415a3b73e174ff3ecd38d379d01f4`. Build and actual installed Owner attestation passed. The original installed regression receipt remains **747 PASS / 1 FAIL**. The failure was a controlled fixture hashing the request before including the new generation prerequisite marker. A test-only correction on that same installed application passed 19 targeted tests; this does not rewrite the original receipt or certify changed application code.

The fresh PostgreSQL suite remains **37 PASS / 3 FAIL**, migration `20261007_72`. Both actual C1 admission paths reached independent Guardian successfully. Three existing identity-tamper tests deleted the semantic-selection contract while retaining the generation prerequisite contract. Owner recomputation correctly rejected the illegal combination, but its precise `OBLIGATION_FORMATION_REQUEST_VIEW_CONTRACT_INVALID` ValueError escaped the durable feedback-identity stop path. This is an application recovery defect, separately established from model mapping failures.

## Minimal repair

In the existing feedback lineage validator, convert only that precise invalid restored-contract exception to the existing `OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT` identity error. All other ValueErrors still escape normally. Exact Owner recomputation and request/response fingerprint comparison remain mandatory. Existing handling persists the identity stop, preserves UNRESOLVED and terminal history, and opens no Provider call or new budget.

The targeted marker regression now includes selection-marker and typed-prerequisite-marker deletion. Development 128 passed **425 tests**, with explicit source overlay, zero model calls and no historical database access. These are controlled regressions, not installed-image or real G0 qualification. Independent read-only review found no additional defect in the exact exception conversion; it did not certify model convergence.

## Historical identity and scope

The corrected schema-forensic receipt explicitly associates the generation42 second Wire with its own attempt-2 pending and response receipts. The initial pending receipt is separately identified as the original schema Owner basis. The earlier annotation is retained and corrected rather than overwritten. Historical request, Wire, inventory and terminal receipts remain unchanged. Historical replay makes zero model calls and refuses retrospective marker upgrades.

The actual generation42 whole-current-intent RETAIN_CONTEXT proposal was accepted by the old generation schema but rejected by the existing final Owner. The new schema expresses that same existing Owner prerequisite earlier. This proves an expressibility/generation-contract correction; it does not prove model or Semantic Review success.

## Next required qualification

Freeze the repaired application and corrected controlled fixture as a new source revision; build a new exact image, run installed regressions and the affected PostgreSQL identity/Guardian gate, preserve historical zero-call replay, then run the authorized ordinary G0 once. Independent Holdout remains sealed until the ordinary production path qualifies. No production, historical Work, authority, budget, Wire schema or Owner changes are authorized by these receipts.

Public receipts and their ECS locations are indexed in `manifest.json`. Private artifacts remain on the existing ECS qualification volume; no private Human inventory, prompt, credentials or Provider body is included here.
