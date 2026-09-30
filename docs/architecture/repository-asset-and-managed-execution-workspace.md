# Repository Asset and Managed Execution Workspace

## Status

Local optional-repository admission and Product-owned Managed Source are
implemented. New Product source uses an independent Gitea Community Edition
service as the first replaceable provider. The older repository-optional Work
allocation path still keeps checked Git bundles in PostgreSQL for its legacy
continuity. A bounded GitHub grant/push/PR path remains separate; live GitHub
write qualification is pending an authorized credential.

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
Machine-loss survival for that older bundle path requires PostgreSQL hosted and
backed up off the worker host. Bundles are bounded to 128 MiB in this profile.

## Product Managed Source

**Watt Managed Source != Gitea. Gitea is the initial reference provider.**
Git is the current source technology, not the Product ontology. Watt owns the
Product source identity, accepted source revision and tree, Work source basis,
Candidate lineage, Human Acceptance and external mappings. The Gitea adapter
owns repository creation, exact Git materialization, Candidate persistence,
accepted-ref synchronization and access metadata. No Product, Work or Candidate
uses a Gitea repository ID as its identity. Watt never queries Gitea's database.

New Product creation provisions a private provider repository with a first
tracked file and records Product source version 0. Brownfield creation uses
`source_mode: import`; the existing repository is observed first, then imported
at its exact revision/tree with its origin recorded. No external Git provider
is required after import. A Work created for that Product receives an isolated
Git branch and Engineering Resource based on the **exact Watt accepted
revision**, not provider HEAD. Its source version, revision and tree are stored
as Work lineage. The existing production owners create a verified Candidate and
Runtime Commit. Runtime Commit persists that Candidate in the provider under
the Work ref. Only an exact Human Acceptance advances the Product's accepted
version. A later Work reads that version. If Product acceptance advanced since
the Work began, promotion fails closed; this slice does not reconcile competing
branches.

The Runtime Trusted Baseline may advance at Runtime Commit before Product Human
Acceptance. It therefore does not determine the Product's accepted source.
Existing legacy Products without a managed source row retain their previous
repository asset metadata; no migration guesses an acceptance decision from
historical Runtime Commits.

The Product Code Assets API/UI shows accepted and Candidate versions, file
tree, changed files, a bounded diff, origin and clone access metadata. A ZIP
export is generated from an explicitly named exact revision. Internal provider
credentials are not returned. Provider unavailability or a missing revision
blocks Work source preparation; the Product's accepted version remains intact.
Human Acceptance does not grant GitHub push, PR or remote delivery authority.

### Provider deployment evolution

1. **Single ECS/host:** Watt and Gitea are separate services. Gitea 1.27.3
   rootless uses a dedicated persistent source volume and a separate SQLite
   database in its data volume for local/single-host use. The Watt database is
   a different application database. Recreating the Gitea container must keep
   both Gitea volumes. The local Compose network uses an internal HTTP endpoint.
2. **Dedicated Managed Source host:** point Watt's provider endpoint and
   public clone endpoint to the new host and mount the Gitea volumes on its
   dedicated persistent disk. Use HTTPS for the remote credential transport.
   Product identities and lineage do not change.
3. **Future provider/storage scale-out:** replace the provider adapter and
   deployment storage while preserving Watt's accepted source records and
   exact source contract. Distributed Git storage and HA are outside this slice.

`compose.managed-source.yaml` supplies the reference service. Configure
`SPG_MANAGED_SOURCE_PROVIDER`, `SPG_MANAGED_SOURCE_ENDPOINT`,
`SPG_MANAGED_SOURCE_PUBLIC_ENDPOINT`, `SPG_MANAGED_SOURCE_USERNAME`,
`SPG_MANAGED_SOURCE_PASSWORD`, `SPG_MANAGED_SOURCE_NAMESPACE` and
`SPG_MANAGED_SOURCE_WORKSPACE_ROOT` for Watt. The provider endpoint is a
service URL, the workspace root is disposable Watt-local materialization, and
Gitea's persistent data/config volumes are independent of both. Use a governed
runtime secret for the credential. The first owner account is bootstrapped by
the Gitea administrator, not hard-coded into an image or Product row.

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
