# Code Dogfood #1 Pre-execution Finding: Repository-aware Change Proposal Gap

## Evidence Status

This document preserves the first real Code Self-dogfood Work as historical
pre-execution evidence. It records observed Runtime facts and the narrow product
finding; it does not re-refine, approve, execute, repair, or reinterpret the
Work as successful.

## Observed Reality

| Fact | Observed Reality |
| --- | --- |
| Runtime | `watt-code-dogfood` |
| Work | `ef905566-179f-4184-bb66-9c9e23301a2b` |
| Human intent | Preserve the bottom Work Composer expand/collapse choice across page refresh; modify only required frontend files and related tests; do not change other behavior or redesign the UI. |
| Work status | `NEEDS_REFINEMENT` |
| Current step | `PRODUCTION_PLANNING` |
| Exact blocker | `An exact authorized artifact/change target is required before production.` |
| Historical target projection | `DOCUMENTATION_WORK` |
| Source revision | `8ce312765e5e1f611b0ef035594a7000a039dc88` |
| Runs / Attempts / Provider Reports | `0 / 0 / 0` |
| Production started | no |

## Finding

```text
CODE_DOGFOOD_1
    NEEDS_REFINEMENT
    no production started

REPOSITORY_AWARE_CHANGE_PROPOSAL_GAP
    CLOSED by MVP-REFINE-CODE-1
```

Watt could execute and verify an explicitly bounded Code Change Contract, but
ordinary code intent could not reliably become such a contract without Human
path knowledge. The safe pre-execution stop was correct: missing target
authority was not replaced by repository-wide scope, and no production Runtime
or Provider side effect was created.

The historical `DOCUMENTATION_WORK` projection also shows that natural-language
frontend intent needed a narrow classification calibration. It is preserved as
observed Reality rather than rewritten after the product change.

## Admitted Product Response

MVP-REFINE-CODE-1 adds exact-baseline, read-only repository inspection and a
Human-reviewable Change Proposal before `ADMIT_WORK_DRAFT`. The proposal remains
distinct from Production Authority; only Human admission forms the exact
`CodeChangeContract`. The implementation is documented in
[Repository-Aware Code Change Proposal Lite](../../architecture/repository-aware-code-change-proposal-lite.md).

The same natural-language requirement must later be submitted in a fresh Watt
Runtime. This record neither proves that future Work will complete nor
authorizes implementation of Composer state persistence in the development
checkout.

## Preservation Boundary

The historical Work remains unchanged at `NEEDS_REFINEMENT`. No refinement,
approval, Run, Plan Revision, PWU, Attempt, Dispatch, Provider Turn, Candidate,
Integration Effect, Runtime Commit, or Trusted Baseline advancement is created
by this evidence record.
