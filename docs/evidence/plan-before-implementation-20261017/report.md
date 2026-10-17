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

Deployment and actual Work recovery qualification are pending in this initial
implementation report. The authorized endpoint is a reviewable design
artifact; game implementation, Candidate acceptance and delivery remain
unapproved.
