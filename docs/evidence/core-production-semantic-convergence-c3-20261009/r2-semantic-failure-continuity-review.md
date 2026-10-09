# R2 — Semantic Step Revision Failure Evidence Continuity

## Historical boundary

The user-authorized diagnostic ZIP for Work `408e408a-fab8-5a34-b101-b922043cb6fd` retains Self-Refine event `88b26b47-7310-4460-8cde-72a76338718b`, operation `bd21eead-5e53-4c0d-aa88-c6acb9c47e9d`, at `2026-10-09T09:15:34.463951+00:00`. Its diagnostic evidence has only `basis_fingerprint`, `first_validation_feedback`, and `second_error_type`. The first feedback code is `INTENT_COMPLETENESS_MISMATCH`; the second error type is `ValueError`. The event records two candidate attempts, and the exported Owner section has zero Semantic Step Results. The second failure stage, reason and candidate identity remain **UNKNOWN**. Numeric usage is redacted in this export. Its manifest source revision/tree are null, so this ZIP alone cannot prove the historical Runtime source. The adjacent JSON records safe source hashes and exact IDs; it does not reproduce conversation or model output.

## Confirmed current gap and minimal repair

The C3 Semantic Step Owner had the same three-field failure diagnostic and did not identify whether revision failed during Provider parsing or admission. DeepSeek refinement updated its last result only after parsing, leaving the first candidate observation available when a revised response failed parsing. These are current code findings, not inferred explanations for the historical second ValueError.

The existing Self-Refine diagnostic now records the original Step/Plan/basis, safe stable failure classification, actual bounded redacted feedback supplied to revision, first/revised candidate canonical SHA256 identities, parent fingerprint, and failure phase. Candidate bodies, proposed content and reasoning are excluded. Strict schema failures retain only field locations and error types. Typed ModelProviderError uses the existing normalized safe field whitelist; arbitrary transport exception prose is omitted. Semantic diagnostics remain under the Semantic Step Owner and do not use a formation receipt as substitute evidence.

Provider candidate observations are made before typed parsing and contain response SHA256/size, exact basis identities, bounded request/model identifiers, declared usage/timing and observed transport retry count when StructuredModelResult supplies it. Initial, existing wire-repair and revised candidates are distinguished. Provider errors supply no numeric usage or HTTP replay count, so those remain UNKNOWN. Per-attempt state clears stale success observations. Scope usage preserves unknown fields and does not present a previous successful subtotal as complete after a failed Provider call.

The existing two candidate attempts and one feedback refinement remain unchanged. No authority, fact, admission guard, Self-Refine Owner, schema, global trace layer or runtime route is introduced. Existing wire-repair and Scope model call conditions are retained. Completed routine recovery remains a local result and is not full Work PASS. This repair records completed refinement evidence in the existing sink; it does not claim an atomic pre-call journal or recover old unrecorded details.

Root separately approved the R1 actual-tree guard: a required path absent from the full exact source tree triggers complete canonical behavior coverage even when its proof cites existing source. This closes tag-dependent coverage without expanding permission or model retries; R1 owns its independent test.

## Qualification

`tests/test_c3_semantic_failure_continuity.py` has eleven controlled nodes covering revised admission, typed Provider failure, parse failure, wire repair, parent candidate identity, unchanged basis, actual feedback, success/supersession/authority boundaries, and UNKNOWN cost propagation. AST/compile and Git diff hygiene passed. Root's isolated Linux regression is pending. These are controlled candidates and Runtime fixtures; no live Provider, Work, ECS, canonical main or sealed holdout was touched. No history is rewritten and this report does not claim that Work408 has been recovered.


## Final exact continuation qualification

Application source `e8e04b296b31d776a13dda728fa19469681cbaab`, tree `a349e40ea0c328ad55574dc668e884a137a19944`, new image `sha256:4d3c64b1e3543a3574cd69b435d6f703fad6edc23b9db7d54d799dc1a652bf6e`: [321 installed-image tests](continuation-20261010/continuation-final-image/watt-continuation-receipt.json) and [5 isolated PostgreSQL tests](continuation-20261010/semantic-owner-pg/receipt.json) PASS. No source/test overlay or live model calls. New fixture DB `spg_c3_continuation_fixture`, migration `20261007_72`, is stopped. These are bounded engineering qualifications, not real G0 or historical Work408 repair.
