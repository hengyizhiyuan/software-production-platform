# Repository-optional Production Flow

## Result

**IMPLEMENTED / FOCUSED VALIDATION PASS / READY_FOR_HUMAN_ACCEPTANCE**

## Root cause

Work admission, WIC, and intermediate Guided Design already supported an empty
Repository Asset scope. The first divergence was the final semantic
design-to-production transition: Provider guidance required Repository Asset
clarification and production-plan materialization rejected a missing
Engineering Resource/Baseline. This incorrectly made Human-supplied repository
binding a prerequisite for production even though Work identity was already
independent.

## Implemented correction

At the production-transition issue only, Plan Steering now allocates a
deterministically identified local Watt-managed execution workspace when no
repository is selected. The existing asset observation, Trusted Baseline,
Engineering Resource, Work Reality revision, proposal review, SPG,
Verification, Candidate authorization, integration, Runtime Commit, and
Delivery mechanics are reused. Intermediate design does not allocate the
workspace early.

External HTTPS repository intake no longer converts an access failure into a
Work blocker. It persists and returns a sanitized `UNRESOLVED` Asset candidate
with `READ`, `WRITE`, `CREATE_BRANCH`, `CREATE_PR`, and `PUSH` authorization
states `UNKNOWN`. It cannot be bound for production. No credentials, remote
push, OAuth, or SSH behavior was introduced.

The delivery UI presents repository input as optional, excludes unresolved
candidates from production selectors, and explains that Watt-managed local
production can continue.

## Focused evidence

- Semantic wire and UI contracts: 30 passed.
- Repository/Git/PostgreSQL/Node focused integration: 6 selected cases; the
  first run did not enter tests because the isolated test database had an
  inconsistent Alembic marker and missing `repository_intakes` table. Only the
  disposable `spg_delivery_test` schema was rebuilt through normal migrations.
  The rerun produced 5 passes and one test-expectation failure: early Human
  clarification correctly did not allocate a workspace before production
  readiness. The expectation was corrected without product-semantic change;
  its isolated rerun passed. Final focused result: all 6 selected integration
  cases passed across the unchanged successful rerun cases and the corrected
  isolated case.
- The no-user-repository case traverses Work admission, Guided Design,
  Production Proposal review, deterministic Executor production, independent
  Node Verification, Candidate authorization, repository integration, Runtime
  Commit, Trusted Baseline advancement, and Software Artifact package
  publication.
- The existing explicit repository case remains covered by the same focused
  suite.
- The inaccessible remote URL case proves durable unresolved candidate state,
  unknown capability authorization, zero Work binding, and continued Work
  availability.

## Human acceptance

Human acceptance should verify:

1. Start a new Work without entering or selecting a repository.
2. Complete design and review the production proposal.
3. Complete the existing governed production/authorization path.
4. Publish and run/download the resulting Software Artifact.
5. Confirm an existing supported repository can still be explicitly selected.
6. Enter an inaccessible repository URL and confirm it is shown as unresolved,
   cannot be selected for production, and does not prevent the Work from
   continuing.

The existing multi-port acceptance adapter is unchanged and Runtime Manager is
not introduced.
