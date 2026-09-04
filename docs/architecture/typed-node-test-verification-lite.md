# Typed Node Test Verification Lite

## Status

**MVP-VERIFY-NODE-1: CLOSED / PASS**

The Architecture Lead Reality Review passed. The
`FRONTEND_VERIFICATION_CONTRACT_GAP` is resolved.

The focused evidence resolves `FRONTEND_VERIFICATION_CONTRACT_GAP` by adding
one typed, path-bounded Node test obligation to the existing contract-driven
Code Verification Lite architecture. It does not implement the Composer state
feature or create another Verification system.

## Typed Contract

`NODE_TEST_TARGET:<repository-relative-target>` identifies one exact JavaScript
test admitted by the Human Code Change Contract. Its target must:

- be a safe repository-relative path below `tests/`;
- use `.js`, `.cjs`, or `.mjs`;
- remain inside the exact or bounded admitted change scope;
- avoid absolute paths, traversal, Git internals, and repository escape.

The contract contains no command, script, shell, or free-form argument field.
The existing path validation and Change Contract authority checks reject an
unsafe or unrelated target before execution.

## Execution and Evidence Boundary

`RepositoryCodeVerifier`, selected through the existing
`ContractDrivenRepositoryVerifier`, owns the fixed execution mapping:

```text
NODE_TEST_TARGET:<target>
    → node --test <validated-target>
```

Only the typed target occupies the variable argument position. Verification
materializes the exact proposed commit, uses the existing narrow verification
environment, and captures bounded metadata: obligation kind, exact target,
exit code, output fingerprint/byte counts, and duration. It does not persist a
large test log or add arbitrary-shell authority. The local Watt Docker runtime
definition installs only the `nodejs` runtime required by this check; no npm/yarn/pnpm
workflow system is introduced.

Node PASS participates in normal Verification aggregation. Node FAIL yields
Verification `FAIL`, no Candidate, and `trusted_result=false`. Completion stays
independent: a required frontend change may be `PRODUCED` while its Node test
fails.

## Repository-aware Proposal Integration

When exact-baseline repository inspection finds a related JavaScript test, the
Change Proposal may now include its typed `NODE_TEST_TARGET`. Against commit
`371bb2b509151569814860387ab8c4364cbb922b`, the Composer-state dogfood input
produces:

```text
Required:
    src/spg/web/app.js
    tests/js/test_web_state.cjs

Conditional:
    src/spg/web/index.html

Verification:
    PATH_SCOPE
    GIT_DIFF_CHECK
    NODE_TEST_TARGET:tests/js/test_web_state.cjs
```

The proposal is derived from repository evidence and remains non-authoritative
until `ADMIT_WORK_DRAFT`. The historical Dogfood Work is not rerun or changed.

## Focused Evidence

| Evidence | Focused proof |
| --- | --- |
| NODE-01–05 | Typed identity, no command surface, safe repository-relative JS test path, traversal rejection, and admitted-scope enforcement. |
| NODE-06 | Existing fixed `node --test <target>` runner is used in an exact materialized snapshot. |
| NODE-07–08 | PASS contributes to Candidate eligibility; non-zero exit produces Verification FAIL and no Candidate. |
| NODE-09–10 | Completion remains `PRODUCED`; evidence identifies exact target/result with bounded diagnostics. |
| NODE-11–12 | Exact-baseline Refinement proposes the real related Node target and forms the truthful dogfood Verification Contract. |
| NODE-13–14 | Existing Python/Pytest and Documentation verifier paths remain compatible. |
| NODE-15–16 | No generic CI/shell subsystem and no Provider Turn are introduced. |

## MVP Boundary

This slice does not add arbitrary shell execution, npm/yarn/pnpm orchestration,
universal JavaScript CI, Composer state persistence, multi-PWU, ECF, Guardian,
Provider routing, Retry/Resume, UI redesign, or Linux deployment.
