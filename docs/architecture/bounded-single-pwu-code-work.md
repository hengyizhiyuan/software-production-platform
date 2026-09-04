# Bounded Single-PWU Code Work

## Status

**MVP-CODE-1: CLOSED / PASS**

This slice closes the two narrow MVP core gaps identified after MVP-PLAN-1B:
bounded Contract Formation for ordinary source-code/test Work and
contract-driven Verification Lite. It preserves the existing one Work → one
Plan Revision → one PWU Runtime, Human authority, Candidate, Repository
Integration, Runtime Commit, Trusted Baseline, and ORCH-1 models.

## Code Work and Change Authority

Refinement now classifies the production target as `DOCUMENTATION_WORK` or
`CODE_WORK`. Documentation Work retains its Artifact Contract. Explicitly
bounded Code Work may form a Human-visible Change Proposal containing the
Engineering Resource, exact Source Baseline, Desired Outcome, inherited
constraints, exact target files and/or bounded repository areas, known
create/update operations, forbidden scopes, and typed Verification obligations.
Only the existing Human `ADMIT_WORK_DRAFT` decision converts that proposal into
the authoritative `CodeChangeContract`. See
[Repository-Aware Code Change Proposal Lite](repository-aware-code-change-proposal-lite.md).

Supported authority shapes are `EXACT_TARGET_SET`,
`BOUNDED_REPOSITORY_AREAS`, and `EXACT_AND_BOUNDED`. Paths must be safe,
repository-relative POSIX paths. Absolute paths, parent traversal, Git
internals, wildcard exact targets, and implicit repository-root authority are
rejected. An unresolved code intent remains `NEEDS_REFINEMENT`; it never falls
back to `docs/*.md` or `**/*`.

The Human may adjust the proposal in the existing Work Draft before
`ADMIT_WORK_DRAFT`. That existing decision admits Work, Plan, and the resulting
Change Contract together; no second approval gate is introduced. Planner
output must preserve the proposal and final contract exactly and cannot widen
its own authority.

## PWU, Execution, and Observation

The approved Plan remains multiple ordered logical steps inside exactly one
PWU. The PWU Completion Contract and Materialized Execution Input carry the
Desired Outcome, Plan steps, constraints, exact targets, bounded areas,
forbidden scopes, and typed checks. The Executor is explicitly instructed not
to widen the Change Contract.

Independent repository Observation remains Production Truth and records every
changed path and operation relative to the exact Source Baseline. Provider
success or self-report does not establish scope compliance.

## Contract-driven Verification Lite

Code Work is verified by the contract-driven repository verifier, not the
Markdown verifier. It executes only obligations present in the admitted
contract:

- `PATH_SCOPE` compares the full observed change manifest with exact, allowed,
  and forbidden scopes and known operations;
- `GIT_DIFF_CHECK` performs fixed-argument Git whitespace/error checking;
- `PYTHON_COMPILE` compiles changed admitted Python files;
- `PYTEST_TARGET:<repository path>` runs only the validated admitted target;
- `IMPORT_CHECK:<module>` imports only a module mapped to the admitted source
  boundary;
- `NODE_TEST_TARGET:<repository path>` runs one admitted JavaScript test through
  the fixed `node --test <target>` mapping.

No arbitrary shell command becomes Production Authority. Commands use fixed
argument vectors, a narrow environment, and an exact temporary materialization
of the proposed commit. Output is represented by exit status and fingerprint,
not promoted into hidden authority.

Completion and Verification remain separate. Completion asks whether the
required production change was independently observed. Verification asks
whether that produced Reality satisfies every admitted check. An unauthorized
path or failing targeted test yields Verification `FAIL`, no Candidate, and a
truthful blocked Work even when Completion is `PRODUCED`.

## Focused Evidence

- Happy Path: a deterministic Executor modifies one admitted Python source and
  its admitted test; Observation captures both; Completion is `PRODUCED`; all
  typed checks pass; exact Human Candidate Authorization leads through
  Integration and Runtime Commit to `trusted_result=true`.
- Authority failure: one admitted source change plus one unauthorized path is
  preserved in Observation; `PATH_SCOPE` fails and no Candidate is formed.
- Verification failure: all changed paths remain admitted and Completion is
  `PRODUCED`, but the admitted targeted pytest check fails; no Candidate is
  formed and `trusted_result=false`.
- Compatibility: the existing same-intent Markdown documentation path retains
  its Artifact Contract and repository-artifact verifier semantics.

Together the focused tests cover `CODE-01` through `CODE-24`: classification,
safe exact/bounded contracts, Human adjustment and admission, one-PWU/MEI
propagation, no Planner/Executor authority widening, independent Observation,
typed contract-driven Verification, Completion separation, Candidate/Human
authority and ORCH compatibility, documentation compatibility, and scope
firewalls.

## Scope Boundary

MVP-CODE-1 does not add Multi-PWU production, repository-wide authority,
general AI refinement/planning, arbitrary-shell CI, ECF, Guardian, Provider
routing, retry/resume, Worker Fleet, Linux deployment, or a second
Orchestrator. No persistence schema or migration is required because the
existing JSON contract boundary carries the new typed fields.
