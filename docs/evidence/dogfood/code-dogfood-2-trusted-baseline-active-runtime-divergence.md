# Code Dogfood #2 Finding: Trusted Baseline / Active Runtime Divergence

## Evidence Status

This record preserves the post-production product-acceptance failure and its
bounded local-Docker repair evidence. It does not rerun the Work, call the
Provider, mutate historical Runtime facts, or reinterpret Human Product
Acceptance as successful.

## Historical Production Reality

| Fact | Observed Reality |
| --- | --- |
| Runtime | `watt-code-dogfood-2` |
| Work | `740c1a6a-514e-43e5-a2a2-463d53860170` |
| Trusted revision | `84be41abb4e48875107c28d9483f3c8e0e316b68` |
| Trusted tree | `8f71f7959eca3b2e242bac6a22eb320675043a58` |
| Engineering Verification | `PASS`, including `NODE_TEST_TARGET` |
| Repository Integration | `CONVERGED` |
| Work | `COMPLETED`, `trusted_result=true` |
| Human Product Acceptance Attempt #1 | `FAIL` before activation |
| Human Product Acceptance after activation | `PASS` |

The Human expected Composer collapse/expand state to survive page refresh. The
running page still returned to expanded state.

## First Divergence

The authoritative ref and Trusted Baseline had advanced, but the Runtime
checkout index/worktree retained source-baseline versions of the changed files.
Even after checkout convergence, the existing FastAPI process served the
install-time package under `/opt/spg-venv/.../site-packages/spg/web`, not the
new trusted checkout.

```text
Primary:
    TRUSTED_BASELINE_ACTIVE_RUNTIME_DIVERGENCE
    STALE_RUNTIME_OR_STATIC_ASSET

Severity:
    NECESSARY_RUNTIME_FIX

Secondary:
    PRODUCT_ACCEPTANCE_GAP
    VERIFICATION_RUNTIME_COVERAGE_GAP
```

The Candidate implementation itself was consistent with the desired behavior.
The Node test passed against Candidate source; it did not prove that the
currently served Runtime had loaded that source.

## Improvement Lineage

The complete evidence lineage is preserved without rewriting earlier outcomes:

```text
Original requirement
    persist Work Composer collapse/expand state across page refresh

Code Dogfood #1
    NEEDS_REFINEMENT
    REPOSITORY_AWARE_CHANGE_PROPOSAL_GAP

MVP-REFINE-CODE-1
    proposal gap resolved

Frontend Verification inspection
    FRONTEND_VERIFICATION_CONTRACT_GAP

MVP-VERIFY-NODE-1
    verification-contract gap resolved

Code Dogfood #2
    real governed production
    Verification PASS
    Trusted Baseline advanced

Human Product Acceptance Attempt #1
    FAIL
    TRUSTED_BASELINE_ACTIVE_RUNTIME_DIVERGENCE

MVP-RUNTIME-ACTIVATE-1
    exact Trusted Baseline activated

Human Product Acceptance after activation
    PASS
```

## Activation Evidence

After the bounded MVP-RUNTIME-ACTIVATE-1 restart:

- checkout `HEAD` and tree matched the Trusted revision and tree;
- checkout status was clean;
- Uvicorn `PYTHONPATH` was `/var/lib/spg/repository/src`;
- active package fingerprint was `973ddaa41a4f6f01e4536df15cf2fbade2a16312`;
- active static fingerprint was `f59632f3b07987098eeddac5a2df86fbe8bdd117`;
- served `/assets/app.js` was byte-identical to the trusted Git blob;
- the served asset contained `spg.workComposer.expanded` persistence logic;
- a second App-only restart remained converged and idempotent.

Runtime fact counts remained unchanged:

```text
Works / Attempts / Provider Reports = 1 / 1 / 1
Observations / Completions = 1 / 1
Verification records = 3
Candidates / Authorizations / Integration Effects / Runtime Commits = 1 / 1 / 1 / 1
Trusted Baseline pointer version = 1
```

## Finding

> Trusted repository acceptance does not prove that the active product process
> is running that trusted revision.

The admitted response is documented in
[Trusted Baseline / Active Runtime Convergence Lite](../../architecture/trusted-baseline-active-runtime-convergence-lite.md).

The Human Governor repeatedly toggled collapsed and expanded Composer states
and refreshed the page. In four successive toggle-state cases, expected and
observed post-refresh states matched. Therefore:

```text
Code Dogfood #2
    COMPLETED
    TRUSTED RESULT
    ACTIVE_AT_TRUSTED_BASELINE
    HUMAN PRODUCT ACCEPTANCE PASS

FIRST TRUSTED WATT CODE SELF-DOGFOOD LOOP
    PROVEN
```

`VERIFICATION_RUNTIME_COVERAGE_GAP` remains **OPEN / NON-BLOCKING / DEFERRED**.
The source-level Node test still does not replace true browser/runtime behavior
verification; no browser E2E is added by this closure.
