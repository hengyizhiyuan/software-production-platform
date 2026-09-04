# Repository-Aware Code Change Proposal Lite

## Status

**MVP-REFINE-CODE-1: CLOSED / PASS**

The Architecture Lead Reality Review passed. The
`REPOSITORY_AWARE_CHANGE_PROPOSAL_GAP` is closed. The separately confirmed
`FRONTEND_VERIFICATION_CONTRACT_GAP` remains open and is not fixed by this
checkpoint.

This slice adds bounded repository understanding before Code Work admission. It
does not change the authority of the Human, Production Planner, Executor,
Candidate, or Repository Integration flow.

## Change Proposal Contract

During Code Work refinement, Watt may inspect the exact current Source
Baseline and produce a provider-neutral `RepositoryChangeProposal`. The
proposal records:

- exact proposed targets with `REQUIRED` or `CONDITIONAL` disposition;
- optional bounded allowed areas and explicit forbidden areas;
- concise repository-grounded rationale, evidence, and confidence;
- typed Verification obligations supported by MVP-CODE-1;
- the exact Engineering Resource, Source Baseline ID, ref, and revision;
- provider identity/version, inspection method, and unresolved scope questions.

The proposal is durable and Human-visible, but is not Production Authority.
Conditional targets remain informational and are never silently admitted.
Ambiguous inspection produces `NEEDS_REFINEMENT`; repository root, `src/**`,
`tests/**`, and `**/*` are not convenience fallbacks.

## Read-only Inspection Boundary

The deterministic MVP provider uses fixed read-only Git object operations to
verify the exact commit, enumerate paths, search text/symbol evidence, and read
small candidate files. It does not check out a revision, mutate the worktree,
index, or refs, create Runtime facts, call an Executor, or start a Provider
Thread or Turn. The application boundary rejects provider output that changes
the Engineering Resource or any Source Baseline identity.

This is Repository Inspection Lite, not ECF, a semantic index, embeddings, an
AST dependency graph, or a general code-intelligence platform.

## Human Admission and Staleness

The existing Work Draft surface shows the proposed targets, conditional paths,
areas, rationale, confidence, constraints, Verification approach, provenance,
and unresolved questions. The Human may edit exact targets and areas or request
another refinement. No second mandatory approval action is introduced.

Only `ADMIT_WORK_DRAFT` converts the then-current proposal into the
authoritative `CodeChangeContract`. Admission includes only required targets,
retains the exact allowed/forbidden boundaries and supported typed obligations,
and records the source Proposal ID and fingerprint. It then regenerates the
single-PWU Production Plan from that admitted contract. A proposal whose
Resource, Baseline ID, ref, or revision differs from current Reality is rejected
as stale; it is never silently rebased.

The Production Planner may carry the proposal while the Work is a draft, but
the application rejects any Planner change or widening. Existing Executor,
Observation, Completion, Verification, Candidate, Human Authorization,
Integration, and Runtime Commit semantics remain unchanged.

## Dogfood Proposal Reality

Against an exact repository baseline, the first Code Self-dogfood intent about
preserving Work Composer expansion state now yields a bounded proposal derived
from repository evidence:

- required implementation target: `src/spg/web/app.js`;
- required adjacent test target: `tests/js/test_web_state.cjs`;
- a related UI file may remain conditional rather than authorized;
- backend, domain, infrastructure, and migration areas remain outside the
  frontend-only authority envelope.

The provider derives this result from path and content evidence; it does not
hard-code the complete dogfood sentence. The historical Work is not rerun or
changed by this result.

## Frontend Verification Reality

Classification: **B — FRONTEND_VERIFICATION_CONTRACT_GAP**.

The repository has a targeted Node test at `tests/js/test_web_state.cjs`, but
the current MVP-CODE-1 typed set contains only `PATH_SCOPE`, `GIT_DIFF_CHECK`,
`PYTHON_COMPILE`, `PYTEST_TARGET`, and `IMPORT_CHECK`. It therefore cannot
truthfully represent execution of that Node test. Refinement proposes the two
supported structural checks and surfaces the unresolved gap. It does not invent
a Python check, weaken Verification, or grant arbitrary-shell authority.

The narrow follow-up for Architecture Lead review is one typed, path-bounded
Node test obligation within the existing contract-driven verifier model. That
follow-up is not implemented or authorized by this slice.

## Focused Evidence

| Evidence | Focused proof |
| --- | --- |
| REFCODE-01–02 | Git status/HEAD/refs remain unchanged and inspection is bound to the exact revision. |
| REFCODE-03–04 | Draft persists only a Proposal; Human admission creates the formal Contract and Runtime binding. |
| REFCODE-05–07 | Exact paths, bounded areas, and conditional targets are represented without converting conditional paths into authority. |
| REFCODE-08–09 | Per-target repository evidence, proposal rationale, confidence, and provider provenance are explicit. |
| REFCODE-10–12 | Root-wide fallback is rejected; ambiguity blocks; frontend-only constraints exclude unrelated backend scope. |
| REFCODE-13–14 | Provider Resource/Baseline changes and stale admission are rejected. |
| REFCODE-15–17 | Human edits precede the sole admission gate; admitted Contract traces to Proposal ID/fingerprint and Baseline. |
| REFCODE-18 | Planner carries but cannot change the proposal or admitted authority boundary. |
| REFCODE-19–21 | Executor and contract-driven Verification semantics remain unchanged; Documentation Work still follows its Artifact Contract. |
| REFCODE-22–23 | No production Attempt/Provider is used and no ECF/indexing subsystem is introduced. |
| REFCODE-24 | The exact natural-language dogfood intent receives a repository-grounded bounded proposal without sentence hard-coding. |

## MVP Boundary

This slice does not implement Composer state persistence, multi-PWU production,
general semantic search, embeddings, ECF, arbitrary-shell Verification,
Guardian, Provider routing, Retry/Resume, Worker Fleet, Linux deployment, or a
UI redesign. The Composer behavior remains input to a future fresh Watt Work,
not a feature implemented directly in the development checkout.
