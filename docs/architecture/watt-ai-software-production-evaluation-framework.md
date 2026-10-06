# Watt AI Software Production Evaluation Framework

Date: 2026-09-21

Status: **ARCHITECTURE BASELINE / VERSIONED EXECUTABLE EVALUATION / BOUNDED ADMIN QUALITY OWNER v1**. This document
defines the evaluation dimensions, evidence boundaries, corpus strategy, and
improvement loop for Watt as an AI-native software production system. It does
not implement a benchmark platform, leaderboard, public ranking, or a general
automated evaluation platform. The repository's `spg-evaluate` command runs a
bounded, versioned four-domain corpus, supports focused/milestone/release
selection, persists run/failure evidence, compares a prior qualified release
on shared cases, and fails on critical regressions. Changed case sets are
flagged as partial comparisons. Token, compute and Work cost remain
UNREPORTED when evaluation cases do not provide these facts. These automated
results are separate from Human Acceptance.

## 1. Purpose

Watt needs both the ability to produce software and a durable way to evaluate
and improve that ability.

Traditional software delivery evaluation commonly asks whether the software
compiled, tests passed, and an artifact was delivered. Those checks remain
necessary, but an AI-native software production system must also evaluate:

- whether it understood the Human's intent;
- whether it completed the production task well; and
- whether it can demonstrate that the result is trustworthy.

This document establishes the **AI Software Production Evaluation Framework**
for those three concerns. Evaluation is a cross-cutting capability: it observes
the production chain and turns attributable outcomes into improvement input. It
does not become a new owner of Work Reality, Semantic Truth, production
authority, or Human Acceptance.

## 2. Core principle

Watt must not optimize its software production capability against one score.
The capability being evaluated is the balanced system outcome:

```text
Understand well
      +
Produce well
      +
Assure well
```

The framework therefore has three dimensions:

```text
AI Software Production Evaluation Framework
        |
        +-- Interaction Intelligence Evaluation
        |
        +-- Production Capability Evaluation
        |
        +-- Assurance Capability Evaluation
```

No dimension can substitute for another. Correct code produced from the wrong
meaning is not success. A convincing explanation without a valid product is not
success. A working artifact without sufficient evidence remains an assurance
risk.

## 3. Evaluation boundary and authority

The framework evaluates governed Reality; it does not create that Reality.

It may consume versioned references to:

- Human Intent and Human corrections;
- Response Contract and Interaction outcomes;
- Engineering Semantic Truth and Work Reality;
- ECF projections and repository/runtime observations;
- SOP and Task Contract lineage;
- Executor results;
- Guardian findings and Assurance Evidence; and
- Human Acceptance outcomes.

Evaluation results are measurements, classifications, and improvement signals.
They are not permission to admit Work, change current Semantic Truth, execute a
side effect, waive a gate, authorize a Candidate, or declare Human Acceptance.

Every material evaluation result should identify:

- the exact subject and version evaluated;
- the scenario or corpus item;
- the source evidence and its provenance;
- the evaluation method and framework version;
- unavailable or ambiguous evidence; and
- the Human or system authority behind any judgment.

Historical evaluation results remain historical when the underlying Work,
artifact, or framework changes. They must not be silently rewritten to match a
new version.

## 4. Interaction Intelligence Evaluation

### Purpose

Evaluate whether Watt genuinely understands the Human and collaborates
effectively. This dimension corresponds primarily to WIC and the Response
Contract.

### Evaluation scope

#### Intent understanding

Evaluate whether Watt:

- identifies the actual goal and relevant constraints;
- binds ambiguous language to governed meaning before downstream use;
- distinguishes an interpretation from a Human-explicit fact; and
- avoids confident misunderstanding.

#### Collaboration behavior

Evaluate whether Watt:

- matches the current Interaction Mode;
- leaves appropriate space during exploration;
- converges efficiently during execution;
- asks only questions that materially affect the outcome; and
- advances when sufficient information and authority exist.

#### Judgment consistency

Evaluate whether Watt:

- maintains evidence-based judgment rather than unsupported agreement;
- states uncertainty truthfully;
- updates its conclusion when new governed facts appear; and
- does not present superseded meaning as current.

#### Multi-turn stability

Evaluate whether Watt:

- preserves the active objective across a long conversation;
- avoids semantic drift;
- retains relevant decisions and corrections; and
- restores the correct collaboration state after refresh, retry, or recovery.

### Data sources

Candidate sources include:

- a versioned WIC Golden Interaction Corpus;
- Watt Dogfood cases;
- expert-designed interaction scenarios; and
- attributable Human review outcomes.

The corpus is an evaluation input, not an authority source. Its cases must state
the expected invariant, relevant context, permissible variation, and review
authority. The executable v1 corpus lives in `spg.evaluation.release_gate`;
the broader corpus platform remains outside the current scope.

Each executable case now records its capability and failure family, protected
invariant, risk, scenario type, origin, similarity group, required environment,
estimated cost, failure history, and baseline version. Focused development
qualification selects affected capability/failure families. Milestone release
qualification selects every critical invariant and Golden Journey. Similar
noncritical cases may share one representative, preferring a case with a
meaningful regression history before the cheaper case; no historical case is
deleted and critical protections are never consolidated away.

## 5. Production Capability Evaluation

### Purpose

Evaluate whether Watt can complete software production tasks with high quality.
This dimension corresponds primarily to Domain Grounding, Software Production
SOP, Task Contract, PWU, and Executor behavior.

### Evaluation scope

#### Task understanding

Evaluate whether Watt understands:

- the production objective;
- scope and boundaries;
- acceptance criteria;
- required evidence; and
- applicable authority constraints.

#### Repository understanding

Evaluate whether Watt can:

- understand the existing code and architecture;
- locate the correct change surface;
- preserve unrelated Human-owned work; and
- follow repository-specific conventions and constraints.

#### Implementation capability

Evaluate:

- functional correctness;
- code quality and maintainability;
- architectural consistency;
- change-scope discipline; and
- execution efficiency appropriate to the task.

#### Verification capability

Evaluate whether Watt:

- derives verification from the accepted requirement and contract;
- runs the cheapest sufficient checks before broader qualification;
- classifies failures before changing implementation or expectations;
- repairs genuine defects without hiding them; and
- identifies important omissions and residual risk.

#### Regression resistance

Evaluate whether a new capability preserves existing accepted invariants. Use
the adopted regression-governance model: protect invariants at the lowest-cost
reliable layer and consolidate cross-layer behavior into Golden Journeys rather
than adding one end-to-end test for every historical bug.

See [Watt Regression Protection and Golden Journey
Governance](watt-regression-protection-and-golden-journey-governance.md).

### Data sources

Candidate sources include:

- public software-engineering tasks such as SWE-bench-style cases;
- agent-system benchmark patterns associated with systems such as SWE-agent or
  OpenHands;
- Watt's own governed production cases;
- repository and runtime evidence; and
- existing Production Benchmarks and Production Measurement projections.

Public benchmarks are comparison inputs, not complete definitions of Watt's
capability. They must be mapped to Watt's authority, Reality, execution, and
Assurance invariants before their results are interpreted.

See [Production Benchmarks](production-benchmarks.md) and [Production
Measurement v0](production-measurement-v0.md).

## 6. Assurance Capability Evaluation

### Purpose

Evaluate whether Watt can demonstrate that its production result is
trustworthy. This dimension corresponds primarily to Guardian and the Evidence
Architecture.

### Evaluation scope

#### Requirement compliance

Evaluate whether the result satisfies the current:

- Human Intent;
- Engineering Semantic Truth;
- Task Contract; and
- applicable acceptance and authority boundaries.

#### Evidence quality

Evaluate whether claims are supported by attributable:

- Human Evidence;
- Engineering Evidence;
- Runtime Evidence; and
- Assurance Evidence.

Evidence quality includes identity, provenance, freshness, scope, integrity,
and relevance. Evidence volume alone is not quality.

#### Risk detection

Evaluate whether Guardian and the production system can identify:

- potential defects;
- architecture and boundary violations;
- regression risk;
- missing or stale evidence; and
- uncertainty that prevents a trustworthy conclusion.

#### Assurance effectiveness

Evaluate whether Assurance:

- finds material problems before delivery or authorization;
- reduces the Human's verification burden without taking Human authority;
- avoids false confidence and ceremonial gates; and
- increases the trustworthiness of delivery decisions.

See [Watt Decision and Evidence
Architecture](watt-decision-evidence-architecture.md) and [Guardian
Integration](../assurance/guardian-integration.md).

## 7. Evaluation feedback loop

Evaluation is an improvement entry point, not a terminal score:

```text
Production Reality
        ↓
Evaluation
        ↓
Failure Classification
        ↓
Architecture / Pattern / SOP Improvement
        ↓
New Version
        ↓
Re-evaluation
```

The initial routing model is:

| Failure class | Primary improvement destination | Example concern |
|---|---|---|
| Interaction failure | Response Contract / WIC | Intent misunderstanding, collaboration mismatch, semantic drift |
| Production failure | Domain Grounding / SOP / Task Contract / Executor | Wrong change surface, incomplete implementation, invalid execution |
| Assurance failure | Guardian / Evidence Architecture | Missing proof, undetected risk, unjustified confidence |

Routing identifies the most likely improvement owner; it does not pre-judge the
root cause. Cross-layer failures may require evidence from several owners before
classification.

Evaluation failures should be converted into one of the following only when the
evidence warrants it:

- a corrected architecture invariant;
- a reusable Domain Pattern;
- an SOP or Task Contract refinement;
- a lowest-cost regression assertion;
- a consolidated Golden Journey; or
- a documented future capability.

## 8. Relationship with Watt architecture

The framework evaluates the core production chain:

```text
Human Intent
      ↓
Response Contract
      ↓
Context Intelligence
      ↓
Domain Grounding
      ↓
Software Production SOP
      ↓
Task Contract
      ↓
Executor
      ↓
Guardian
      ↓
Evidence
```

It is cross-cutting rather than a new stage inserted into that chain. Evaluation
may examine intermediate and end-to-end outcomes without becoming the owner of
those outcomes.

## 9. Current scope

The current architecture scope establishes:

- the framework definition;
- the three evaluation dimensions;
- authority and evidence boundaries;
- failure-classification and feedback routing; and
- the corpus strategy; and
- a bounded executable release gate covering interaction, production,
  resilience, and assurance cases with distinct first-pass, recovered,
  escalated, and failed outcomes.

The current scope does **not** implement:

- a Benchmark Platform;
- a leaderboard or public ranking;
- a general automated evaluation platform or leaderboard;
- a new Evaluation service, database, or UI;
- autonomous architecture, Pattern, or SOP mutation; or
- replacement of Full Regression, Guardian, or Human Acceptance.

## 10. Future evolution

### Internal quality system

The first intended use is Watt's own quality system, to:

- detect capability degradation;
- prevent major regressions;
- compare version-to-version improvement; and
- expose recurring failure patterns for governed improvement.

### External evaluation framework

A later exploration may determine whether the framework can contribute to a
broader evaluation system for AI-native software production. That direction is
not a current product or milestone objective.

## 11. Design principles

### No single-metric optimization

Coding score or task success rate alone cannot represent AI-native software
production quality. Aggregate reporting must keep the three dimensions visible
and must not conceal a material failure behind a composite score.

### Reality-based evaluation

Evaluation should derive from actual tasks, governed production, runtime
behavior, attributable evidence, and real Human experience. Synthetic cases are
useful when they isolate an invariant, but must not replace Reality evidence.

### Capability balance

High-quality AI software production requires Watt to understand well, produce
well, and assure well. Improvement in one dimension must not silently weaken
another.

### Versioned and reproducible judgment

The evaluated system version, scenario, configuration, evidence basis, and
evaluation method must be reproducible. Local overrides and unavailable inputs
must be explicit.

### No benchmark gaming

Evaluation must reward durable capability and governed outcomes rather than
case-specific prompts, fixture loopholes, or assertions weakened to match an
implementation.

## 12. Roadmap placement

```text
Core Architecture
  Response Contract
  Semantic Truth
  ECF
  Domain Grounding
  Software Production SOP
  Task Contract
  Guardian

Cross-cutting Capability
  AI Software Production Evaluation Framework

Future
  Pattern Evolution
  Pattern Studio
  Evaluation Platform
```

The framework is an architecture baseline now. An Evaluation Platform remains
future work and requires separate objective, authority, data, privacy,
operational, and implementation design.


## Watt Admin v1 implementation (2026-10-06)

The dedicated `/admin` surface shares Watt authentication and static assets. It
reads canonical owners and invokes Quality commands. Workspace quadrants and
Human Acceptance authority remain unchanged. Quality owns its Cases, Campaigns,
measurements and feedback; it does not own Worker, Product, Context or Guardian
Reality. There is no separate Admin operational database or commercial RBAC.

### Canonical cases and repeatable qualification

`spg.evaluation.catalog` contains the reviewed Core Production Qualification
recipes. Each canonical `watt.<recipe>` Case has a stable UUID derived from its
key, immutable material versions, provenance, legacy corpus aliases and multiple
cohorts. Cohort changes do not copy Cases or rewrite previous attempts. Historical
owner evaluation records are linked through aliases rather than recreated.
Unreviewed generated/production-derived scenarios can be registered using the
`unqualified-scenario` recipe, but remain BLOCKED until a reproducible oracle is
reviewed in source. A scenario cannot borrow another recipe's invariants to pass.

Campaign versions pin exact Case versions. Later versions include relevant
permanent regression Cases automatically; requesting an obsolete collection that
omits their current version fails closed. Each run pins the source revision,
nonsecret configuration, policy fingerprint and optional exact experiment variant.
Run and Case attempt histories are durable. One fenced qualification slot prevents
concurrent recipes sharing the isolated test database. Expired leases mark unfinished
attempts INTERRUPTED, reuse the run identity and skip already completed Cases.
The runner has a two-attempt recovery budget, bounded time/output, a read-only
container, bounded tmpfs and memory/CPU limits. It is separate from the production
Execution Queue and only orchestrates reviewed qualification recipes; it does not
provide another production execution stack.

Recipes exercise existing Work/Managed Source/PWU/Queue/Worker/Verification/
Guardian/Acceptance owners, using an explicitly isolated `_quality_test` database
inside the existing PostgreSQL service. Production tables and pending Candidates
are never test fixtures. Owner identities, exact revisions, dispatch workspace,
context/contract fingerprints and verification references are captured before test
cleanup. Prompts, credentials and unstructured tool logs are excluded. Some recipes
use deterministic compiler/executor/provider seams; the UI and run records describe
that scope and do not claim a live model or live external search from those seams.
The separate generated Holdout exercises the configured real semantic compiler/IRK.

### Evaluation and learning boundaries

Deterministic oracle, Runtime, Guardian, LLM and Human records remain separate.
Objective PASS needs a deterministic oracle, and any failing/blocking objective
owner prevents PASS. LLM/Human opinions never overwrite objective state. An optional
LLM evaluation uses Watt's existing purpose-scoped model runtime and stores exact
model/provider/request provenance. Guardian observations are compared with an
independent known-case oracle, with explicit coverage and potential false-positive/
negative fields; Guardian is never its sole oracle.

Earliest divergence means earliest **observed** failing stage. It does not prove
unobserved earlier stages passed. Ambiguous failures retain UNKNOWN attribution.
Failure clusters use typed stage/code/evaluator/oracle evidence, not text similarity.
A Human may promote a finding into Regression using the same Case identity. Closure
requires a later qualified regression attempt and explicit authority/rationale;
new occurrences remain OPEN. A sealed Holdout may close against a later PASS
of the same sealed Case, without becoming Regression or optimization input. Case and failure history are retained.

Arena experiments pin a Case version and declare the exact model/provider/policy
differences. v1's executable strategy adapter compares bounded qualification timeout
policies. Other model, prompt or planning strategies can be represented but fail
closed as unqualified until an actual application adapter exists. This avoids
claiming that metadata alone changed a production strategy. Human preference stores
ranking, acceptability, confidence, reason tags, rationale and each variant's exact
Case run, Watt/configuration and owner evidence. Owner attribution creates only
HYPOTHESIS learning signals with source lineage; it never changes production.

Fresh Holdout inputs/answers are generated after a revision is pinned, stored in
sealed Case material, passed privately to the recipe, and redacted from all Admin
optimization/history/evaluation APIs. Holdout Cases cannot enter Arena, attribution,
regression promotion or LLM opinion. Promotion requires exact PASS runs of the same
experiment/variant/revision/configuration covering Golden, Regression and a Holdout
created after the experiment. Human explicitly selects evidence and gives a
rationale. The decision approves a subsequent governed change, **not** an automatic
runtime policy mutation, source modification or model fine-tune.

### Operations and topology

Operations reads Worker Registry, native queue and fenced allocation truth directly.
Docker calls are fixed read-only queries. Node CPU uses host tick deltas; memory uses
MemTotal minus MemAvailable; `/data` uses statvfs; uptime uses host proc. Networking
uses a separate read-only mount of host PID 1's network namespace proc directory,
not container `/proc/self/net`. Interfaces are reported separately to avoid double
counting bridges/veths. Missing measurements are UNKNOWN, not zero/healthy.
Service process state and configured health probes remain distinct. Storage
breakdowns state their measurement scope and may overlap; they are not summed.

The topology contract exposes node IDs, service placements, Workers, storage
placements and configured runtime relationships. Only the current single ECS is
qualified. Host samples record timestamps, queue depth and active executions every
60 seconds with 72-hour retention (bounded configuration and display count). Stale
samples are explicit. Overview surfaces failures, capacity starvation, unhealthy
services, low disk and missing/stale observations. Observation never increases
Worker concurrency, changes runtime owners or administers an ECS.

### Deployment and deferred work

The canonical cloud-worker Compose exposes Admin through the existing Web entrypoint.
`quality-runner` is an optional profile, built from the same exact source revision
with the existing test dependency. Create `spg_admin_v1_quality_test` in the existing
PostgreSQL service before enabling that profile. Run
`deploy/cloud-worker/prepare_quality_source.py` from the accepted deployment
workflow and set WATT_QUALITY_SOURCE to its exact immutable Git snapshot. The
runner rejects a source revision that differs from the Campaign. Its private
tmpfs allows reviewed Git authentication scripts to execute; all mutable runtime
roots resolve inside that bounded tmpfs. Gitea is enabled only for reviewed Gitea
recipes, and other fixed fixtures retain their declared source configuration. Set WATT_REVISION to the committed
source SHA and WATT_NODE_ID/REGION/HOSTNAME from observed deployment facts. Migration
`20261006_69` descends from `20261005_68` and adds only Quality ledger/metric tables.

Filesystem hard quotas, automated workspace/image cleanup, HTTPS, external Git
access, cross-host Worker Pool and off-host DR remain separate. No Admin action
resolves or silently closes those debts. The current Worker max_concurrency stays 1.
