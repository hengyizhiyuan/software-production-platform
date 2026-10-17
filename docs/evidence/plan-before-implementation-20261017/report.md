# Plan-before-implementation recovery

The current Work correctly selected documentation production, but its first
design proposal could not pass the scope Owner. The validator consumed
code_targets (empty for documentation), omitting the actual artifact path from
the model's candidate set, source sampling and deterministic proof check. This
made a lawful design document impossible to admit. It was a platform defect,
not a need for another Human product decision.

The repair uses the existing typed proposal's documentation paths for document
scope and code paths for code scope. No prompt exception, phrase detector,
additional phase model or relaxed proof rule was needed. Exact source/tree,
Human witness, target membership and complete requirement coverage still apply.
The original game goal, first-plan constraint and historical failures remain.

On exact source c335a94429cb97442d5ce0c2709928ae68b98e9c/tree
4949d7784ce169a513a020da8f1b30af27664a0b, real model read-only replay proposed
docs/design.md as a design plan with no implementation code. The independent
scope model covered all eight unchanged request/outcome/constraint entries;
implementation and Preview remained downstream of Human design review.
Controlled consumption of this same actual scope result fails twice on the
original code with an empty candidate set and passes once after the repair
with the documentation path present. No replay tools or production effects.

Focused regression: 77 passed; the final seven documentation checks also pass
after strengthening the fixture to distinguish long-term application outcome
from current design-plan objective. Coverage includes new/existing/non-ASCII
documents, exact existing-source reading, outside paths, stale revision/tree,
missing requirements and neighboring code scope/recovery negatives.

PostgreSQL semantic/Steering regression: 22 passed, one pre-existing failure.
The unchanged authority-expansion fixture omits the now-required qualified
Human decision object and stops with ATTENTION_NOT_QUALIFIED:
DECISION_OBJECT_MISSING. Re-running that test with the original source at
51f10f414a5bcb07aabe654b3e98f0a4871a9e4e reproduces the same failure. Authority
remains blocked; this mission does not weaken that guard or repair unrelated
fixture semantics. Both logs are retained. This is not an all-suite PASS.

Deployment qualified application 7461217a910cb6904da4e4b4bab4fcb6450b14d3,
image sha256:010d6a5ab4a54e351c7f84d8dfae3c43f64e10070159ee1c6b6d8439666c64d9.
All four services use the same image, service/database health and the existing
independent owner release gate pass. The separately paused game Work's records
are unchanged across deployment. See deployment-qualified.json.

Actual recovery used only the existing recorded Steering attention approval,
with the Human's repair instruction and explicit design-only limit. The original
Work Reality revision and historical self-refine event are byte-for-byte
unchanged. One production Attempt completed and its PWU is SATISFIED. Exact
observed changes contain only ADDED docs/design.md. Candidate
dd956f08-57cb-5176-92e4-ab5e91659301 at
50ba60d17b5be69b2eca98d15b93368a9178f259 is SEALED. Independent document
Verification passes, including plan content and no game source/build output.
The authenticated exact Candidate download matches the observed Git blob and
is preserved as produced-design.md (9,724 bytes, Chinese). See qualification.json.

The Work now truthfully waits for Human Candidate review/authorization. No
Candidate authorization, Runtime Commit, repository integration, acceptance or
delivery was performed. The current document has no runnable Preview and its
existing Guardian projection says required=false / NOT_STARTED; this is not a
game Preview/Guardian PASS claim. The Chinese workspace summary explicitly
says the plan awaits approval and game implementation has not started. Browser
UI interaction was not performed; exact artifact download and workspace API
were checked. The authorized recovery endpoint is achieved; game implementation
still requires Human approval.

BUG_CLASS: typed artifact path omitted at scope consumption.
ROOT_CAUSE: code_targets was used for both proposal variants.
PROTECTED_INVARIANT: scope/proof/source observation must share the actual typed
Candidate paths, while retaining exact evidence and complete obligations.
PERMANENT_TESTS: tests/test_documentation_scope_proofs.py and neighboring existing
code-scope tests. TEST_LEVEL: contract/unit, with PostgreSQL boundary regression
and one real existing Work qualification. GOLDEN_JOURNEY_IMPACT: existing
documentation production/review boundary strengthened; no new expensive journey.
