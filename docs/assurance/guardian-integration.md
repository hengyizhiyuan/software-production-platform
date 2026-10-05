# Guardian Integration

## Formal Positioning

**Guardian — Engineering Assurance System**

Guardian is platform-native, but platform-independent.

## Boundary

The platform is responsible for Orchestration. Guardian is responsible for Assurance.

Assurance validates observed results, Evidence, contract satisfaction,
important boundary violations, and quality Findings. It does not micromanage
each Executor move or replace the Executor's autonomy inside an admitted
production envelope. See the
[Work-centric Production and Responsibility Principles](../architecture/work-centric-production-and-responsibility-principles.md).

Model-mediated assurance judgments, where present, are candidates subject to
Guardian's own evidence and exact-subject validation. Watt's governed
Self-Refine semantics may support a bounded re-evaluation after contradiction;
they do not turn a wrong-revision PASS into truth, lower Guardian's evidence
bar, or transfer Assurance ownership to the Executor. Current exact-revision
Verification remains a deterministic rejection boundary; no new Guardian
reasoning runtime is claimed by this calibration.

Guardian is:

- Not an AI Code Reviewer
- Not an ordinary CI Gate
- Not an Agent inside a Consumer Application

## External Product and Work Relationship

For Work that produces or evolves an external product such as 易决, the current
direct integration is a **Reference / Transitional Integration**. The
long-term direction is **Platform-mediated Integration**. Guardian qualifies
Evidence for the governed Work/PWU; it does not own a Project lifecycle, Work,
Plan, or attached Assets.

This document does not design Guardian Core.

## Bounded software assurance station

The `REQUIRED` owner-runtime profile uses Guardian's canonical
`watt-guardian-software-assurance-v1` contract. Watt binds explicit business
effects to the current governed Work basis before Candidate sealing
through `POST /api/works/{work_id}/guardian-assurance/requirements`. The payload
contains `authority_identity` and `required_effects` using Guardian's
`EffectRequirement` contract. A long-lived Work uses its Work Reality revision;
a short Work uses its Human-approved Engineering Scope. The binding is immutable
for that admitted basis.
Watt sends the governed objective and constraints, exact Candidate commit/tree,
Preview identity, and Verification references. It does not send raw Human
conversation for Guardian interpretation.

After the exact Candidate Preview reaches READY, Watt calls the Guardian owner
runtime. `GET /api/works/{work_id}/guardian-assurance` exposes the current gate,
Finding count, summary, and result/evidence references. Watt stores only that
projection; Guardian owns the request, Findings, evidence, and result. The
Candidate authorization and Human Acceptance paths require Guardian PASS.
Neither PASS nor Human Acceptance creates Delivery Authorization.

For an admitted long-lived Work, `FAIL_REPAIRABLE` enters the existing Steering
production path under the same Work scope. The Steering revision names the
Guardian result and Finding evidence; Watt produces a successor Candidate and
submits it again. Work convergence history bounds repeated no-progress
outcomes. A short Work creates a successor Run/Plan/PWU under the same approved
scope and Completion Contract. `BLOCKED` never creates repair authority or a
PASS. A missing governed effect scope also blocks readiness.

## Default static path and complete PWU context (2026-10-06)

In the `REQUIRED` runtime, static software uses the existing Candidate Preview
owner as well. Its private loopback HTTP listener serves immutable Git blobs
from the exact sealed commit/tree; it executes no Candidate code. The Human
preview remains the existing authenticated artifact route. Static paths,
regular-file types and object sizes are bounded; symlinks, traversal and secret
files are not served. Persisted preview identity permits listener restoration
at application startup.

If no explicit business-effect binding exists, Watt derives static route
obligations from the admitted PWU Completion Contracts. It freezes those
requirements against the existing Work/scope basis. Manual binding remains an
optional pre-sealing interface, rather than a prerequisite for ordinary static
production.

The adapter checks the current Candidate's exact plan version, every required
satisfied PWU, Task Contract, source basis, qualified output and PASS
Verification records. Execution references, qualified parent baselines and
JOIN/reconciliation evidence are included. Each required PWU's **own ECF
fingerprint** produces an independent Guardian request against the same final
Candidate; there is no synthetic merged ECF package. The aggregate can PASS
only if every referenced canonical Guardian result still exists and matches
that Candidate, revision, tree and runtime. Removing a result blocks the gate.

Protected context coverage is not inferred from an unrelated PATH_SCOPE or
diff PASS. The existing contract-driven Verification adapter additionally
checks bounded static source against the exact Task's protected obligations.
Its read-only model judgment uses the complete bounded Git subject and must
supply an actual implementation-source quote for every protected item. A maximum of one wire correction may repair only missing identities or
literal source quotes; it cannot change a contradiction into satisfaction.
Missing items, wrong tree/package, invented quotes, README-only claims,
oversized subjects fail closed. Unsupported profiles retain their existing typed
Verification checks; this static adapter supplies no context coverage for them,
so applicable Guardian/test-oracle coverage is still required. Contradicted/unverifiable items
cannot become COVERED. Judgment, witnesses, source digests and model provenance
remain in the canonical Verification record; Guardian receives those exact
references. This is evidence-bearing semantic verification, not a formal proof
or a replacement Guardian reasoning runtime. Existing explicit test-oracle
coverage remains valid.

Verification PASS, Guardian pending/BLOCKED/findings/PASS, exact Candidate
integration authorization and explicit Delivery Acceptance remain distinct.
Neither Verification nor Guardian PASS changes the accepted Product baseline.
The default UI suppresses acceptance while required assurance is missing.

## Exact acceptance and interrupted promotion

An immutable explicit ACCEPT decision first creates a durable
`product_source_promotion_intents` record in the same PostgreSQL transaction.
The intent binds Product, Work, Candidate, Runtime Commit, Human Acceptance,
previous accepted version/revision/tree, exact next revision/tree and canonical
Guardian result references. It does not copy Guardian gate truth.

Managed Source reconciliation validates that authority and exact baseline,
then performs the existing idempotent Git promotion and commits one accepted
source version together with the COMPLETED intent. A crash before Git, after
Git or before SQL completion leaves replayable intent. BLOCKED records retain
safe failure categories; unresolved promotion prevents a new Work from binding
a contradictory accepted source. Repeated exact acceptance or the existing
Delivery `reconcile-source` route reuses the original decision. Startup also
reconciles unresolved Gitea intents. No repository HEAD alone supplies Human
acceptance authority, and conflicting decisions/revisions are rejected.

New Work uses only the canonical accepted Product revision. Rejection and
non-acceptance do not promote source. Existing Human-pending Candidates are
never automatically authorized or accepted by this recovery path.
