# Candidate document entry in the existing workspace

The original recovery produced a verified Chinese design document, but the user
could not read it in Watt. The workspace already received the exact Candidate
artifact inventory; its renderer omitted those artifacts and displayed Preview
unconditionally. A document-only Candidate correctly has no runnable Preview,
so the button necessarily returned "no verified/openable preview".

The Actions quadrant now lists Candidate artifacts with download links. Text
documents have a View Document button that opens the complete text in a reader,
using the existing authenticated exact Candidate download endpoint. Content is
assigned via textContent, so embedded HTML stays inert. Paths are URL encoded;
stale/missing Candidate reads retain existing Delivery Owner rejection. A closed
or replaced reader ignores late responses. Preview is offered only when the
current Candidate reports a preview kind. Software/mixed-artifact review,
Guardian restrictions, acceptance, integration and delivery controls retain
their existing semantics. WIC's factual review copy now points to files for a
Candidate with no preview instead of requesting an unavailable preview.

Focused UI/reader contracts: 22 pass. This includes real reader-function
invocation, exact path/fingerprint URL, full untruncated inert text, arbitrary
Chinese/punctuation paths, multiple/mixed artifacts, stale-read failure and
late-response isolation. WIC/authority unit checks: 51 initially pass; final cache-hit coverage adds two
checks and all 53 pass. Complete JS suite:
165 pass / two unchanged Admin fixture failures. Both fail because the old
standalone Admin harness lacks window.WattLogin.prefill. The Admin source and
fixture are byte-for-byte identical to starting commit 2229d2a3; their repeated
failure and hashes are retained. This is not an all-suite PASS.

HTTP regression: both neighboring lineage cases passed. The strengthened
document case passes on real PostgreSQL/Git/HTTP after correcting the new
fixture assertion to compare the boolean trusted_result to False, not None.
The document downloads before authorization; forged fingerprint and
outside-inventory paths are rejected; reading leaves authorization pending.
Deployed exact-Candidate qualification is pending.
No production rerun or Candidate authorization is needed for this UI repair.

BUG_CLASS: existing artifact inventory omitted by review projection consumer.
ROOT_CAUSE: unconditional Preview control, missing file/document controls.
PROTECTED_INVARIANT: review entry points correspond to actual Candidate artifact
capabilities and exact version identity, available before Human authorization.
PERMANENT_TESTS: test_workspace_document_review.cjs, existing quadrant/authority
checks and the document HTTP lineage fixture. TEST_LEVEL: UI contract plus HTTP
integration. GOLDEN_JOURNEY_IMPACT: strengthen existing document review; no new
expensive journey or workspace structural change.

The first deployed read exposed an additional consumer defect: cached prose
returned previously cached deterministic fact labels, retaining the unavailable
Preview instruction. Both cache-hit paths now derive those labels from the
current exact Owner facts while reusing qualified prose unchanged. No stored
records, basis identity or model generation is rewritten. Initial deployment
receipt is retained separately; final deployment qualification is pending.
