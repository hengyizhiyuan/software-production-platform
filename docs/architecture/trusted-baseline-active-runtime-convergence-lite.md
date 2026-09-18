# Trusted Baseline / Active Runtime Convergence Lite

## Status

**MVP-RUNTIME-ACTIVATE-1: CLOSED / PASS**

Architecture Lead Reality Review passed. Code Dogfood #2 reached Human Product
Acceptance PASS after exact Trusted Baseline activation.

This slice closes the local-Docker `TRUSTED_BASELINE_ACTIVE_RUNTIME_DIVERGENCE`
found by Code Dogfood #2. It does not create a deployment platform, a new
production-authority gate, or a general Product Acceptance lifecycle.

## Core Semantics

The following are independent facts:

```text
Trusted Baseline
    repository result has been governed and accepted

Active Runtime Revision
    the current Watt process is executing and serving one exact revision

Human Product Acceptance
    a Human has used that active revision and accepted its product behavior
```

Therefore:

```text
Repository Integration
→ Runtime Commit
→ Trusted Baseline B1

does not imply

Active Runtime Revision = B1
```

Repository ref, checkout `HEAD`, Runtime Commit, and Trusted Baseline Pointer
cannot independently prove activation. Active Runtime requires process-local
evidence for application revision, repository tree, source-package
fingerprint, static-asset fingerprint, and source root.

## Local Docker Activation Design

Activation is a bounded startup lifecycle action:

```text
read Current Trusted Baseline
→ safely synchronize Watt-owned checkout
→ validate exact revision/tree and clean checkout
→ classify image-bound changes
→ derive source-package and static-asset fingerprints
→ restart the application interpreter with the synchronized `src` root
→ serve Python code and Web assets from that same root
```

The launcher remains image-provided. The activated application package and its
static assets are both loaded from the exact synchronized Trusted revision.
There is no Web-only hot-read path and no intentional mixed-version mode.
Repeated startup at the same Trusted Baseline is idempotent.

Activation evidence is stored as local infrastructure evidence at
`/var/lib/spg/runtime-activation.json` and projected from process
configuration. It is not a Runtime Commit, Trusted Baseline, authorization, or
Human Product Acceptance record. No database schema or migration is added.

## Convergence States

| State | Meaning |
| --- | --- |
| `ACTIVE_AT_TRUSTED_BASELINE` | Active application revision/tree and package/static fingerprints match the Current Trusted Baseline. |
| `ACTIVATION_REQUIRED` | Repository trust advanced while the current application process remains on an earlier supported revision. |
| `ACTIVATION_BLOCKED` | Exact source, clean-checkout, Git-object, or activation-evidence invariants cannot be proven. |
| `IMAGE_REBUILD_REQUIRED` | The trusted change affects image, dependency, migration, Compose, or startup/bootstrap boundaries and cannot truthfully be activated by source-only restart. |

The API exposes the current projection at `GET /api/runtime-activation` and
includes it in Work Result. The existing UI uses that projection to distinguish
`Trusted repository result` from `Active at trusted baseline` without adding a
new workflow or authority action.

## Explicit Human Review application version (pre-closure)

An uncommitted Human Review build cannot honestly use the normal exact-Git
application activation evidence. A caller must explicitly select
`SPG_RUNTIME_ACTIVATION_MODE=HUMAN_REVIEW`; missing normal evidence never
silently selects this mode. The review launcher first establishes the normal
clean Engineering Resource / initial Trusted Baseline for Work production, then
captures a separate `HumanReviewRuntimeVersion` for the **Watt application**.

The version ID is a SHA-256 canonical digest of its base Git revision/tree,
source and configuration roots, the complete review `src` content digest,
package and static-asset digests, dependency-lock digest, and a digest of
mounted build/startup/Compose/migration inputs plus non-secret runtime/provider
configuration. Paths, bytes, sizes and modes participate; caches are excluded,
and links are rejected. The source and configuration mounts are read-only in
the container. A process-pinned version ID and a retained content-addressed manifest in the isolated
Runtime volume are checked on each activation projection; changes to mounted
source, static assets, lock, or configuration invalidate the old identity.
The next startup computes a new identity. Credentials are not serialized.

`ACTIVE_HUMAN_REVIEW` with `activation_mode=HUMAN_REVIEW` and an exact
`human_review_version_id` means only that the currently mounted review bytes
match their registered identity. It does **not** mean
`ACTIVE_AT_TRUSTED_BASELINE`, release, Runtime Commit, Verification, or Human
Product Acceptance. The independent Work engineering Source Baseline,
Candidate, Verification, authorization and Delivery rules remain unchanged.
Human Review evidence can be attributed to this build identity; final closure
still requires normal committed-version evidence and its applicable regression
gate. Review identity cannot be promoted to trusted application identity.

## Checkout and Image Boundary

The existing guarded Trusted-checkout synchronizer remains authoritative for
materialization. It refuses unexpected staged, unstaged, or untracked changes
and preserves them instead of resetting or overwriting them.

Source-only activation is prohibited when the revision range changes the
equivalent of:

- `Dockerfile` or `.dockerignore`;
- `pyproject.toml` or `uv.lock`;
- `docker/` startup/bootstrap code;
- migrations or Alembic configuration;
- Compose definitions.

Those paths yield `IMAGE_REBUILD_REQUIRED`. This list is a bounded local-MVP
safety boundary, not a general image-promotion design.

## Code Dogfood #2 Activation Evidence

The historical Work remains complete and trusted:

- Work: `740c1a6a-514e-43e5-a2a2-463d53860170`;
- Trusted revision: `84be41abb4e48875107c28d9483f3c8e0e316b68`;
- Trusted tree: `8f71f7959eca3b2e242bac6a22eb320675043a58`;
- active package fingerprint: `973ddaa41a4f6f01e4536df15cf2fbade2a16312`;
- active static fingerprint: `f59632f3b07987098eeddac5a2df86fbe8bdd117`.

After controlled activation, the Uvicorn process source root was
`/var/lib/spg/repository/src`, checkout `HEAD` and tree matched the Trusted
revision/tree, checkout status was clean, and the HTTP-served `app.js` was
byte-identical to the trusted Git blob. Its SHA-256 was
`65df31dd1eeff4c18a5e346f1262f90ab2f950973c3050c504f399d14c33a019`
and it contained the admitted `spg.workComposer.expanded` persistence logic.
A second App-only restart reported `repository checkout already current at
Trusted Baseline` and remained converged.

No Work, Attempt, Provider Report, Observation, Completion, Verification,
Candidate, Authorization, Integration Effect, or Runtime Commit was created or
changed by activation.

## Product Acceptance and Verification Finding

```text
Engineering Verification = PASS
Runtime Activation = PASS
Human Product Acceptance = PASS
```

After activation, the Human Governor exercised multiple collapse/expand state
changes followed by page refresh. For four successive toggle-state cases, the
expected post-refresh state equaled the observed post-refresh state, covering
both collapsed and expanded persistence. This Human evidence establishes
acceptance; activation itself did not manufacture it.

`VERIFICATION_RUNTIME_COVERAGE_GAP` remains **OPEN / NON-BLOCKING / DEFERRED**:
the current typed Node test
validates source-level persistence structure but does not exercise a browser
reload against runtime-served assets. Browser E2E automation is outside this
slice.

## ACT Evidence Map

| Evidence | Proof |
| --- | --- |
| ACT-01–04 | Separate typed Trusted/Active projection with explicit revision, tree, package, and static fingerprints. |
| ACT-05 | One exact synchronized `src` root supplies application imports and packaged Web resources. |
| ACT-06–07 | Existing guarded synchronizer converges exact lineage and blocks/preserves unexpected changes. |
| ACT-08–10 | Required, exact restart activation, and same-Baseline idempotence are deterministically tested and Docker-smoked. |
| ACT-11 | Image/dependency/migration/bootstrap changes yield `IMAGE_REBUILD_REQUIRED`. |
| ACT-12 | No static-only hot-update bypass is introduced. |
| ACT-13 | Activation is an operator lifecycle action and creates no repository authority. |
| ACT-14 | Dogfood Runtime row counts and Trusted pointer remained unchanged before/after both restarts. |
| ACT-15 | HTTP-served Composer asset equals the trusted Git blob after activation. |
| ACT-16 | Human Product Acceptance PASS is separately evidenced by manual runtime behavior checks and remains distinct from engineering Verification. |

## MVP Boundary

This slice does not implement browser E2E, general Product Acceptance,
deployment orchestration, Linux deployment, Kubernetes, blue-green/canary,
automatic image promotion, Provider routing, Retry/Resume, ECF, or Guardian.
