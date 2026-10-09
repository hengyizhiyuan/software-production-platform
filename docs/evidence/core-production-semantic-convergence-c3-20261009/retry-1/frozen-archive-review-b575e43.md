# C3 retry-1 independent frozen archive review

- Captured: 2026-10-09T12:42:12.764741+00:00
- Status: **PASS_SCOPED_GIT_EXPORT_LINE_ENDING_BOUNDARY** (E3, exact input scope only).
- Application: `91f5dbc9906d1f857113736981517c1091ec52ae` / tree `50c6b8fad3f321638135fbec8afcba060b3fb2bc`.
- Control: `b575e4346bf50d9046e4ed888daaeaccc4d5e8ee`.
- Independent engineering reviewer, not Human Acceptance.

| Owner | Files | Byte identical | Only LF to CRLF | Other differences |
|---|---:|---:|---:|---:|
| watt | 571 | 2 | 569 | 0 |
| guardian | 11 | 0 | 11 | 0 |
| ecf | 6 | 0 | 6 | 0 |
| ecf-unsupported | 6 | 0 | 6 | 0 |

Every archive SHA and physical file SHA matches its manifest. File membership equals
`git ls-tree` at the exact Owner revision under explicit archive inputs; original
Git Blob bytes were independently obtained using read-only `git cat-file --batch`.
All 12 committed/current control hashes match. Application Docker COPY inputs
have no differences between application91f5 and controlb575.

The physical archive files differ from raw Git Blobs only by LF to CRLF conversion;
non-newline differences: 0. Per-file original object IDs, both SHA256 values, byte sizes
and classifications are retained in the JSON report. Physical archive bytes must
not be described as byte-identical to raw Git Blobs. Installed identity attestation
must use the actual exported input bytes. No other content transform was observed.

The retained dependency archive is absent locally and was not contacted remotely;
its actual bytes are UNKNOWN in this review. This is an input review only, not
image/import, Work, Guardian or Runtime Conformance qualification. Existing
Quality test filenames containing holdout are ordinary archived code; no sealed
reviewer specification was opened. No service, test, model or Work ran; no prior
report or source was changed.
