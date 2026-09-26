# Repository Asset and Managed Execution Workspace

## Status

Local optional-repository admission is implemented. The P0 extension adds a
PostgreSQL-backed canonical Git bundle for Watt-managed source and a bounded
GitHub grant/push/PR path. Live GitHub write qualification is pending an
authorized credential; deployment durability is pending off-host PostgreSQL.

## Principle

A Repository is an optional Asset associated with Work. It is neither the
identity of Work nor a prerequisite for admitting, designing, or producing a
new software outcome.

```text
Work
  -> optional Assets
       -> optional Repository Asset
  -> Execution Workspace
  -> governed software production
  -> Delivery
```

The Execution Workspace is required by the current Git-based SPG production
mechanics, but it need not be supplied by the Human. When an admitted Work
reaches the design-to-production transition without a selected Repository
Asset, Watt allocates one deterministic Watt-managed Git repository. Its
execution checkout receives an observed repository identity, exact Trusted
Baseline, Engineering Resource binding, and governed Work Reality revision.
Git history is captured as a checked bundle in PostgreSQL at initialization
and Runtime Commit; a new worker checkout can be rebuilt from the bundle.
An explicitly created Work branch from managed source is captured under its
own Watt-internal identity and bundle, so later commits on that branch also
survive loss of an execution checkout.
The checkout is not canonical source. This is infrastructure inside the
existing Work authority envelope and implies no external repository authority.
Machine-loss survival requires PostgreSQL hosted and backed up off the worker
host. Managed bundles are bounded to 128 MiB in this first profile.

Allocation happens only at production readiness. Work admission and
intermediate Guided Design remain valid with an empty asset scope. Human review
of the resulting Production Proposal, Candidate authorization, independent
Verification, Runtime Commit, Trusted Baseline advancement, Delivery, and
Human product acceptance retain their existing authority boundaries.

## User-provided Repository Assets

A repository reference is candidate input, not proof of access:

```text
Repository Reference
  -> Asset Discovery
  -> Capability Check
  -> Authorization
  -> Production Binding
```

The current intake adapter can observe supported local repositories and
reachable HTTPS Git repositories. A GitHub READ grant can supply a scoped
credential without placing it in a URL, Git command or database row. A URL
that cannot be observed is retained as
an `UNRESOLVED` Asset candidate. It does not block Work and cannot be selected
for production. The product explains that authorization and integration are
required before use.

Normative rules:

1. Repository URL does not equal Repository Access.
2. Repository Asset does not equal Work identity.
3. Read and write are distinct capabilities.
4. Production must not rely on unverified write capability.
5. Missing Git permission must not prevent Watt from creating software in a
   managed workspace.
6. No remote push authority is inferred from intake, Work admission, local
   production authorization or a GitHub WRITE credential. The exact current
   software manifest needs Human Acceptance and a separate Human Delivery
   Authorization before a non-force push. GitHub's observed branch SHA is
   recorded after push; optional PR creation confirms its exact head and base.

## Current MVP capability

The current slice supports:

- Work admission and Guided Design without a repository;
- deterministic Watt-managed Git allocation at production readiness and
  full-history bundle export/recovery;
- the existing local Git/SPG/Verification/Delivery path over that workspace;
- explicit Human binding of an independently observed repository;
- durable non-blocking `UNRESOLVED` candidates when remote access cannot be
  confirmed;
- GitHub READ and WRITE grant records, credential rotation/revocation seam,
  exact non-force push and optional PR for an accepted software delivery.

The current implementation intentionally continues to use local Git as SPG's
exact source/baseline/integration substrate. That technical substrate is not a
product requirement for the Human to provide a remote repository.

## Repository capability model

Repository Asset providers may expose capabilities such as:

```text
READ
WRITE
CREATE_BRANCH
CREATE_PR
PUSH
```

Each capability requires an independently attributable authorization state:

```text
UNKNOWN
GRANTED
DENIED
```

Current qualified code supports Local Git, Watt Managed Git and the bounded
GitHub path above. GitLab, Enterprise Git, GitHub App/OAuth enrollment and
generic repository creation remain outside this slice. API tokens are only
referenced by name in grants and supplied at runtime; a token is a credential,
the grant records scoped capability, and Human Delivery Authorization governs
the actual remote write.

## Boundaries

This correction adds no Project lifecycle or generic Git provider system.
Repository Asset admission remains explicit for Human-selected external
assets. SPG owns admitted production execution; the Executor does not gain
ambient remote write authority. The current one-owner authentication profile
uses server-derived `human:owner`, persisted organization membership and
per-resource ownership. A shared multi-actor runtime requires a later IAM
profile rather than treating the self-dogfood token as tenant isolation.
