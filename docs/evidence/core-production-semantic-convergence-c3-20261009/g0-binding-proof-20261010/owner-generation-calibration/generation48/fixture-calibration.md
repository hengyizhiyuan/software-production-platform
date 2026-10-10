# Exact-image regression and fixture calibration

The b7ac98b application image `sha256:20f7bfbc86a24c748375b47c10287612217ab3a3ca242f8bec64ad1574d245df` ran 806 installed-package regressions: 805 PASS, 1 FAIL, zero errors/skips. The failed node was `test_terminal_failure_preserves_exact_sources_and_same_basis_never_reopens_calls[SEMANTIC_REVIEW]`. Its actual terminal stage was MODEL_REQUEST rather than the fixture's expected SEMANTIC_REVIEW.

The fixture constructed a Wire using manually enumerated Owner prerequisites that omitted the new request-bound source-context and presentation contracts. Runtime correctly rejected its request identity before Review. This is a controlled fixture defect, not evidence of a production Review failure. The corrected fixture derives its Wire from the actual request's Owner prerequisites and feedback. No runtime identity, source, semantic, authority or evidence gate was relaxed.

All nine directed Provider-failure/replay regressions PASS on the installed b7 application with only the changed test mounted. This is explicitly a test overlay, not final exact-image qualification. Its receipt is at `/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/binding-boundaries-fixture1-20261011/evidence/`.

The b7 image's 42 PostgreSQL persistence/Guardian integration tests PASS, Migration `20261007_72`, fresh isolated database and credentials, zero live model calls and no business Work. The failed 806-test receipt remains immutable and is not rewritten as PASS.

Final source/test freeze is `8becd1ff3f8389ebeb401794ca44f8bce9adac19`, tree `555553b66a10aeeb6e6e289412d8514c404b76ec`. Comparing application, test, migration, Docker and package inputs with b7 shows only `tests/test_c3_fulfillment_provider_failures.py` changed; additional intervening commits contain evidence. Application and Owner code are unchanged. A new exact image and matching receipts are required before ordinary G0. Real G0 and independent Holdout remain necessary for C3 qualification.
