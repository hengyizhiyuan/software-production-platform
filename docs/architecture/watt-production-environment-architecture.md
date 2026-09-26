# Watt Production Environment Architecture

Date: 2026-09-22

Status: **ARCHITECTURE DIRECTION FROZEN / FOUNDATION V1 IMPLEMENTED**

This document freezes the responsibility and lifecycle direction for Watt's
Production Environment. Foundation v1 implements immutable contracts,
policy-driven lifecycle transitions, a provider-neutral execution-environment
boundary with an initial container adapter, Git continuity observation, Preview
projection, explicit Human Delivery authorization, resource references, minimal
Production Record lineage, and versioned ECF/Guardian payloads. It does not
implement a general Runtime orchestrator, sandbox engine, managed Git hosting,
automatic cleanup, or full Production Passport.

## 1. Core position

A Production Environment is an **AI-native software production execution
environment** prepared for one governed Work and its admitted production
activity.

It is not:

- a Docker manager;
- a CI system;
- a Git replacement; or
- a generic coding sandbox.

The primary entity is **Work**, not Repository. A Work may use zero, one, or
multiple repositories and may acquire or replace repository assets during its
lifetime. A Production Environment exists to serve the current governed Work;
it must not turn a repository, checkout, container, or tool session into the
identity or authority source of that Work.

This extends, without replacing, the existing
[Work-centric Production Model](work-centric-production-model.md) and
[Repository Asset and Managed Execution Workspace](repository-asset-and-managed-execution-workspace.md).

## 2. Architecture model

```text
Work
  ↓
Production Environment
  ↓
Workspace
  ↓
Runtime / Preview
  ↓
Delivery
  ↓
Production Passport
```

The arrows express governed lineage and dependency, not one shared lifecycle or
one owner:

- **Work** supplies the admitted objective, authority, constraints, and current
  production need.
- **Production Environment** binds the minimum sufficient resources and
  capabilities needed to act for that Work.
- **Workspace** is the concrete production surface in which admitted changes
  are prepared and observed.
- **Runtime / Preview** makes an exact produced result inspectable in an
  applicable execution or presentation context.
- **Delivery** transfers an authorized result through an explicit delivery
  boundary.
- **Production Passport** records the attributable lineage of what happened
  across the production event.

Production Environment coordinates these resources for Work. It does not
absorb the authority of Work, ECF, Executor, Verification, Guardian, Delivery,
or Human Governance.

## 3. Workspace

A Production Environment may prepare a Workspace containing:

- one or more repository working surfaces;
- dependency environments;
- the toolchain and bounded tools required by the admitted Task Contract;
- generated changes and intermediate build outputs; and
- references to the exact baselines, context, authority, and evidence
  requirements applicable to the operation.

Multi-repository support means one Work can bind multiple repository assets
without merging their identity, history, authority, or baselines. Every
generated change must remain attributable to its source repository, baseline,
Work, Task Contract, and execution lineage.

The Workspace consumes current, attributable **ECF Reality**. It does not own
Engineering Reality. In particular:

- the physical Workspace is a Watt-managed production resource;
- Workspace Reality is the ECF-owned engineering representation of the
  workspace's observed state; and
- an Executor may mutate an authorized working surface, but its report is not
  by itself authoritative Engineering Reality.

The current local Git execution workspace remains bounded Repository Reality.
It is not evidence that the broader Production Environment lifecycle described
here is implemented.

## 4. Environment lifecycle

The frozen lifecycle vocabulary is:

```text
CREATED
  → INITIALIZING
  → ACTIVE
  → SUSPENDED
  → ARCHIVED
  → DESTROYED
```

These states describe the availability and retention of the Production
Environment, not Work status, Executor Attempt status, Runtime readiness,
Delivery status, or Assurance outcome.

| State | Meaning |
|---|---|
| `CREATED` | Environment identity and Work binding exist; resources need not yet be prepared. |
| `INITIALIZING` | Required Workspace, dependency, toolchain, access, and context bindings are being prepared or reconciled. |
| `ACTIVE` | The environment is eligible to serve admitted production activity. |
| `SUSPENDED` | Active use is paused while identity, lineage, and required retained resources remain recoverable. |
| `ARCHIVED` | The environment is no longer active; retained records and referenced resources remain available according to policy. |
| `DESTROYED` | Disposable environment resources have been removed after reference and retention policy permits it; historical production records remain governed elsewhere. |

Lifecycle decisions are policy-driven. Inputs may include:

- idle time;
- current Work state;
- Human review dependency;
- the Resource Reference Graph;
- organization retention and security policy; and
- cost policy.

No automatic transition, timeout, retention duration, or recovery behavior is
defined here. A Lifecycle Policy Engine is explicitly not part of this
architecture-foundation task.

## 5. Resource Reference Graph

Future cleanup must be based on governed references rather than resource age or
process liveness alone. The future Resource Reference Graph should make visible
at least:

- active Work references;
- artifact dependencies;
- evidence dependencies; and
- pending Delivery state.

The direction is inspired by garbage-collection principles: a resource becomes
eligible for cleanup only when it is no longer reachable from a governed root
and applicable retention policy permits disposal. Reachability does not itself
authorize deletion, and physical deletion must not erase immutable production,
evidence, or decision history.

The graph, reachability algorithm, retention engine, and garbage collector are
not implemented or specified by this document.

## 6. Source-control continuity

Git remains the underlying source-control mechanism for Git-backed software
production. Watt should provide a Work-centric abstraction over Git rather
than replacing it.

The abstraction must preserve:

- commit history;
- branch identity and relationships;
- commit ancestry; and
- export to an authorized external Git provider.

Production Environment may prepare working surfaces and record source-control
operations, but it does not rewrite repository history or infer remote write,
push, branch, or pull-request authority. Managed Git hosting, provider account
integration, remote push, and pull-request automation remain outside this
foundation.

### 6.1 Repository acquisition policy v1

Repository acquisition is derived from admitted Repository Reality for each
repository asset. ECF owns the selected reality; Production Environment turns
that selection into a physical Workspace asset; the Executor only consumes the
prepared Workspace.

The v1 policy is deliberately bounded:

- an explicit Human branch selects that branch;
- otherwise the Repository Reality default branch is selected;
- acquisition fetches only the selected branch;
- full reachable commit history is preserved (no shallow clone);
- Workspace HEAD is detached at the exact admitted revision; and
- revision, tree identity, provenance, and acquisition policy are verified
  before execution.

Each repository in a multi-repository Workspace carries an independent branch,
revision, provenance reference, and acquisition policy. Sparse checkout,
partial clone, LFS optimization, Managed Git, and enterprise repository policy
remain deferred.

## 7. Production Passport

A Production Passport is the attributable record of a production event. It
connects references to:

- Intent Record;
- Decision Record;
- Context Record;
- Task Contract Record;
- Source Control Record;
- Environment Record;
- Execution Record;
- Verification Record; and
- Delivery Record.

The Passport records what happened, on which governed basis, and with which
outcome. It is append-oriented production history, not a mutable summary that
rewrites old evidence.

Production Passport and ECF have different responsibilities:

```text
Production Passport
  records the attributable history of a production event

ECF
  records and projects current Engineering Reality, including version,
  provenance, applicability, freshness, and relationships
```

The Passport may reference ECF facts and projections but does not become their
owner. ECF may refresh current Reality after a production event without
rewriting the Passport's historical record. This definition refines the
existing [Production Execution Package / Production Passport Direction](production-execution-package-direction.md); implementation remains not started.

## 8. ECF boundary

For the Production Environment integration boundary, ECF owns the governed
engineering representations of:

- Repository Reality;
- Workspace Reality;
- Change Reality; and
- Delivery Reality.

This ownership includes the applicable version, provenance, freshness,
relationships, and consumer projection of those realities. It does not mean
ECF owns or performs the physical operation represented by a fact.

ECF does not own:

- execution;
- containers or sandbox processes;
- Production Environment or Runtime lifecycle; or
- scheduling and capacity allocation.

Production Environment is an ECF consumer. It requests the minimum sufficient,
consumer-specific Reality projection, binds exact references into the
production event, and returns observed change/delivery signals for governed ECF
refresh. It must not independently invent a competing Engineering Reality.

## 9. Guardian boundary

Guardian consumes, as applicable to an Assurance objective:

- Task Contract;
- Production Environment state;
- produced artifacts;
- Verification and other attributable Evidence; and
- Production Passport lineage.

Guardian provides Assurance. It may identify evidence gaps, Findings,
qualification outcomes, or Design Challenges, but it does not provision the
Production Environment, run the Executor, own Work, mutate ECF Reality, or
authorize Delivery on behalf of the applicable authority.

Production Environment is an evidence source, not Guardian's sole source of
truth. Environment evidence must remain bound to exact Work, Task Contract,
resource, revision, and production-event identities.

## 10. Responsibility summary

| Concern | Owner | Production Environment relationship |
|---|---|---|
| Work intent, scope, and current production authority | Watt Work Reality / applicable Human and system authority | Serves the admitted Work; does not redefine it |
| Engineering Reality and context projection | ECF | Consumes exact Reality references and emits observations for refresh |
| Production orchestration and environment lifecycle | Watt | Creates and governs environment availability according to policy |
| Bounded implementation method | Executor | Operates inside the admitted Task Contract and prepared Workspace |
| Verification result | Verification | Evaluates the exact produced subject independently of Executor prose |
| Assurance semantics and judgment | Guardian | Consumes attributable environment and production evidence |
| Delivery authority and operation | Delivery / applicable Human or policy authority | Supplies an authorized, exact result and records its outcome |
| Production-event history | Production Passport | Records cross-boundary lineage without taking over source ownership |

## 11. First vertical slice: Brownfield Feature Delivery

The first vertical slice now has a bounded runtime implementation. It proves a
composed technical chain against a real local Git repository, real Docker
container execution, a Human-accessible loopback Preview, durable local records,
ECF refresh, and Guardian intake. Its automated Human decisions are fixtures for
the two distinct authority boundaries; Human Acceptance of the product journey
remains pending. The completion slice now also binds the existing asynchronous
Work Admission → Task Contract → PWU → Native Executor path to an exact
Production Environment and Workspace. Native execution evidence, independent
Verification, authorized repository integration, Production Record, ECF refresh,
and Guardian intake retain one lineage.

### Scenario

A Human provides an existing Git repository and requests a bounded feature
change.

### Governed journey

1. **Discover repository reality.** Observe repository identity, reachable
   source, current branch/ref, exact baseline, capabilities, and applicable
   context without inferring write authority.
2. **Create production workspace.** Create a Work-bound Production Environment
   and an isolated Workspace from the exact admitted baseline.
3. **Modify feature.** An Executor acts only within the admitted Task Contract,
   scope, capabilities, and repository authority.
4. **Start Preview.** Produce an inspectable Runtime/Preview bound to the exact
   candidate artifacts and revision.
5. **Human reviews.** The Human reviews the exact candidate/preview with
   relevant Verification and provenance visible.
6. **Delivery authorization.** A distinct authorized decision permits the
   delivery side effect; review or successful execution alone does not.
7. **Branch / pull request.** Preserve Git history and ancestry while creating
   an authorized local branch. Remote push, pull-request creation, and
   provider-specific mechanics remain later capabilities.
8. **Refresh reality.** Observe the resulting Repository, Change, Workspace, and
   Delivery Reality, refresh ECF projections, and complete the Production
   Passport lineage.

### Slice proof obligations

The slice must prove:

- Work remains primary while the repository remains an Asset;
- the Workspace is derived from an exact repository baseline;
- ECF Reality references flow into production without being reinterpreted as
  environment-owned truth;
- generated changes, Preview, authorization, branch/PR result, and refreshed
  Reality share exact lineage;
- Guardian can consume attributable evidence without owning execution; and
- failure or suspension preserves history and does not fabricate Delivery or
  current Engineering Reality.

It does not require multi-repository execution, a generic container platform,
managed Git hosting, an automatic lifecycle policy engine, resource garbage
collection, or a complete Production Passport product.

## 12. Foundation v1 implementation boundary

Foundation v1 and the first vertical slice now provide:

- Work-bound Production Environment and multi-repository Workspace contracts;
- the frozen lifecycle vocabulary with an external Lifecycle Policy seam;
- provider-neutral environment operations and a real Docker CLI provider;
- exact-revision isolated Git Workspace preparation and a dependency boundary;
- Runtime/Preview identity and projection over existing runtime observations;
- read-only Git identity, branch, commit, ancestry, and diff observation;
- separate Human acceptance and Delivery authorization transitions;
- Work/Environment/Workspace/Artifact/Evidence/Delivery reference edges;
- a durable local lifecycle/session store and digest-bound Production Record v1;
- ECF Repository/Workspace/Change/Delivery Reality contracts; and
- ECF's minimum durable Git discovery and Reality admission runtime;
- Guardian's minimum durable attributable Assurance Intake contract; and
- an application service that composes the Brownfield journey through separate
  Human acceptance and Delivery authorization decisions;
- a Native Executor Production Environment binding carrying exact Work, PWU,
  Attempt, Task Contract, Environment, and Workspace identities;
- Native tool execution through the Production Environment Provider, with
  command evidence bound to that Environment; and
- authorized Runtime Commit projection into Production Record, ECF Change and
  Delivery Reality, and Guardian Assurance Intake.

Production Environment lifecycle facts remain in the bounded single-host JSON
store, while Work, Task Contract, PWU, Queue/Worker, Candidate, Authorization,
Repository Integration, and Runtime Commit continue through the existing
PostgreSQL Runtime owners. Distributed Production Environment locking and a
general environment control plane remain outside this slice. The implemented
contracts preserve current Work, Executor, Verification, Delivery, ECF,
Guardian, and Human-authority boundaries. They do not infer that a repository
URL, workspace allocation, running Runtime, passing Verification, or available
Provider grants Delivery authority.

## 13. Explicit non-goals

This document does not implement or authorize:

- general-purpose or distributed Production Environment Runtime orchestration;
- enterprise sandbox scheduling or container orchestration;
- new Scheduler or Queue semantics;
- new database models or migrations for Production Environment lifecycle facts;
- managed Git hosting or external-provider integration;
- Delivery Runtime changes;
- Lifecycle Policy Engine;
- Resource Reference Graph storage or garbage collection;
- ECF Core Architecture beyond the bounded Reality contracts/runtime;
- Guardian Core Architecture beyond the bounded Intake contract/runtime; or
- a complete Production Passport implementation.

## 14. P0 runtime extension (2026-09-26)

The bounded Full Application Preview runs Watt-shaped frontend/backend code
against isolated PostgreSQL. An exact Candidate may also declare one Redis
supporting service in tracked `.watt/preview-topology.json` with
`{"schema_version":1,"supporting_services":["redis"]}`. Unknown topology
declarations fail explicitly. The candidate's own Dockerfile, migration tree,
commit and Git tree remain the build source; the fixed gateway exposes only a
loopback preview URL. No arbitrary Compose files or host mounts are admitted.

READY now requires a served-runtime check in addition to process and revision
health: HTML is returned at the expected route, the backend reports database
availability, and a goal created through the gateway can be read back from
the same isolated runtime. These observations are retained with exact
Candidate revision/tree, service identities and the Production Record. A
healthy container alone does not establish functional correctness.

The required owner-runtime profile wires ECF's own Reality runtime and
Guardian's own Assurance Intake runtime into the normal Native Production
Record path. Control Room source inspection reads ECF's latest repository
Reality and refreshes it when Git revision or freshness changes. Guardian's
current owner package supplies intake only; it has no assurance decision API.
Watt therefore cannot claim a Guardian release gate from that intake. The
full-system gate remains an explicit owner-side blocker until Guardian returns
an attributable decision that Watt can enforce.

The accepted P0 path can project a `FULL_APPLICATION_RUNTIME` software
delivery target only when the exact Git tree carries Watt's bounded Docker,
Python and migration runtime definition. The delivery manifest hashes a
bounded, reproducible runtime source subset from the exact Git tree, excluding
unrelated large documentation assets. Human Acceptance of that target requires the same
exact Candidate preview session to remain READY with a persisted served
frontend/backend/PostgreSQL read/write verification PASS; the static-Web
runtime adapter cannot substitute for it. This does not bypass the separate
Guardian owner gate or Human Delivery Authorization for remote Git effects.
