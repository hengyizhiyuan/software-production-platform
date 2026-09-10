# Repository Asset and Managed Execution Workspace

## Status

Architecture correction implemented for the current local MVP delivery path.
Remote Git provider authorization remains a future capability.

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
Asset, Watt allocates one deterministic local, Watt-managed workspace. The
workspace receives its own observed repository identity, exact Trusted
Baseline, Engineering Resource binding, and governed Work Reality revision.
This is execution infrastructure inside the existing Work authority envelope;
it does not imply authority over an external repository.

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
reachable HTTPS Git repositories. A URL that cannot be observed is retained as
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
6. No remote push authority is inferred from intake, Work admission, or local
   production authorization.

## Current MVP capability

The current slice supports:

- Work admission and Guided Design without a repository;
- deterministic local Watt-managed workspace allocation at production
  readiness;
- the existing local Git/SPG/Verification/Delivery path over that workspace;
- explicit Human binding of an independently observed repository;
- durable non-blocking `UNRESOLVED` candidates when remote access cannot be
  confirmed.

The current implementation intentionally continues to use local Git as SPG's
exact source/baseline/integration substrate. That technical substrate is not a
product requirement for the Human to provide a remote repository.

## Future Repository capability model

A future Repository Asset provider may expose capabilities such as:

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

Potential providers include Local Git, Watt Managed Repository, GitHub,
GitLab, and Enterprise Git. This direction does not authorize GitHub/GitLab
OAuth, SSH-key management, remote push authorization, repository creation, or
a generic Git provider integration layer in the current slice.

## Boundaries

This correction adds no Project concept, Work lifecycle state, Repository
identity ownership by Work, remote side effect, Runtime Manager, or acceptance
port redesign. Repository Asset admission remains explicit for Human-selected
external assets. SPG continues to own admitted production execution; the
Executor does not gain repository authority.
