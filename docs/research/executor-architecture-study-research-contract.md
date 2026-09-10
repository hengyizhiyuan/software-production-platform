# Watt — External Executor Architecture Study
## Blueprint-Readiness Architecture Research Mission

You are acting as the repo-grounded Architecture Research Lead for Watt.

This is a SOURCE-LEVEL, COMPARATIVE ARCHITECTURE STUDY.

The Human has already cloned the following reference repositories under
`reference-lab/`:

1. `codex`
2. `OpenHands`
3. `SWE-agent`
4. `aider`
5. `LibreChat`
6. `claude-code`
7. `open-webui`
8. `lobehub`
9. `langgraph`
10. `autogen`

Do NOT download substitute repositories unless a local repository is clearly
incomplete and external lookup is genuinely necessary.

The strategic sequence is already decided:

External Executor Architecture Study
→ Watt Executor Architecture Blueprint
→ PWU + Watt-native Executor Runtime
→ UX / Human Journey reconstruction

This mission performs ONLY the first step.

Do NOT implement the Watt-native Executor yet.

---

# 0. Mission Objective

The goal is not to learn how to clone Codex.

The goal is:

> Learn how mature coding-agent/runtime systems solve the hard execution problems
> Watt is about to own itself, then translate those mechanisms into explicit,
> Watt-compatible architecture inputs.

Watt currently delegates much of real code execution to a Codex SDK adapter.

The future target is different:

> Watt itself owns the software-production execution lifecycle.
> Models/providers become replaceable production resources rather than the owner
> of execution state.

The study must prepare enough evidence and design input that the following
Watt Executor Architecture Blueprint phase does not need to rediscover basic
industry solutions from scratch.

---

# 1. Inspect Watt Reality First

Before studying external repositories, inspect Watt's current Repository Reality
and Source of Truth.

At minimum understand the current implementation and ownership of:

- Human Collaboration / WIC
- Design Intent Framing
- Guided Design
- Work
- Work Reality
- Work Assets
- multi-repository support
- Plan Steering
- PWU
- SPG
- current Codex Executor adapter
- Verification
- Candidate sealing
- Human authorization
- Trusted Runtime Commit
- Software Artifact Delivery
- Human Product Acceptance
- current runtime / workspace behavior
- future ECF direction
- Guardian boundary
- current known latency / recovery findings

Repository Reality is authoritative for what exists today.

Historical product intent is authoritative for what Watt is trying to become.

Important:

> Repository Reality tells us what currently exists.
> It does NOT by itself define the intended future product.

---

# 2. Preserve These Watt Architecture Invariants

Treat these as hard design context during the study.

## 2.1 Work-centric, not Project-centric

Do NOT introduce or recommend a first-class Project abstraction.

Work is the governed representation of a Human Motive and the center of production.

Repositories, documents, Figma, Jira, APIs and other resources are Work Assets.

A new software system and an existing software system use the same Work model.

---

## 2.2 Repository is optional

A Work may exist before any repository exists.

Software production must not conceptually require a user-provided remote Git
repository.

Future possible production sources include:

- existing external repository;
- Watt-managed repository;
- internally created workspace/repository;
- other future engineering assets.

Repository is infrastructure, not Work identity.

---

## 2.3 Work may span multiple repositories

Do NOT assume:

one Work = one repository

and do NOT freeze:

one PWU = one writable repository.

A legitimate production objective may require coordinated changes across
multiple repositories.

If a PWU becomes too broad or unrecoverable, first examine whether Steering
created a poor production decomposition.

Repository count itself is not the architectural error.

The study must investigate how mature systems handle:

- multiple repositories;
- multiple worktrees;
- read/write scopes;
- cross-repository changes;
- atomicity limitations;
- verification;
- recovery.

---

## 2.4 Steering owns WHAT NEXT

Plan Steering decides meaningful production direction:

- what outcome should be produced next;
- why;
- what scope is admitted;
- what engineering objective is worth executing.

Executor must not steal this authority.

---

## 2.5 Executor owns HOW

Inside an admitted PWU, Executor should have substantial autonomy to:

- inspect reality;
- form local implementation plans;
- choose files;
- choose implementation steps;
- run tools;
- debug;
- self-refine;
- verify ordinary implementation hypotheses.

Executor should NOT need Human micro-management.

But it may not silently redefine:

- Product Intent;
- Work goal;
- admitted scope;
- acceptance criteria;
- Human Authority;
- architectural ownership.

Research how external agents distinguish local planning from task redefinition.

---

# 3. Preserve the Current PWU Product Intent

This is CRITICAL.

PWU is not:

- a Jira ticket;
- a prompt;
- a tiny coding task;
- a chat turn;
- an arbitrary agent invocation.

The intended core property is:

> Execution continuity without execution monolithicity.

中文：

> 生产连续，但执行不必连续。

The goal is to preserve the cognitive/productive continuity currently obtained
from a long Codex run while allowing execution to become:

- splittable;
- pausable;
- resumable;
- recoverable;
- independently verifiable;
- replaceable;
- fault-isolated;
- potentially continued by another model/executor.

A future benchmark should be able to compare:

A. one long continuous agent execution

versus

B. segmented PWU execution with pause/restart/model replacement

and determine whether Watt retains intent and engineering quality while gaining
better recovery and governance.

The study must explicitly identify external mechanisms relevant to this goal.

---

# 4. PWU / Execution Session / Attempt / Step

These relationships are NOT all frozen yet.

Study the external systems and recommend the correct Watt model.

Questions include:

- Is PWU itself executable state, or a governed execution contract?
- Should one PWU have one or multiple Execution Sessions?
- Should one PWU have multiple Attempts?
- What constitutes a new Attempt?
- Is retry the continuation of the same Attempt or creation of another?
- What is an Execution Step?
- Which steps need durable persistence?
- Which steps may remain ephemeral runtime detail?
- What constitutes PWU completion?
- What is preserved when an Attempt fails?
- What happens when an Attempt outcome is UNKNOWN?

Do NOT prematurely freeze a conventional job/task model merely because another
system uses one.

---

# 5. Learn From Real Watt Failure Cases

Use these as explicit architecture test cases during source study.

## Case A — Provider Capacity Failure

Watt has observed:

`Selected model is at capacity`

An Executor Attempt became UNKNOWN even though the production objective still
existed.

Current behavior could require an entirely separate recheck path.

Study how mature runtimes distinguish:

- transient infrastructure failure;
- provider failure;
- deterministic task failure;
- uncertain execution outcome;
- safe retry;
- resume;
- new Attempt.

---

## Case B — Client Restart During Active Execution

A real Codex client became unresponsive and was restarted.

The task later resumed execution without the Human re-sending the mission.

Study exactly what makes this possible where source permits:

- remote task state?
- local persisted session?
- workspace?
- event log?
- server-side execution?
- reconnect protocol?
- resumed model context?
- replay?

For Watt:

> UI/client death must not imply execution death.

---

## Case C — Remote Compaction Failure

Codex produced a remote compact/model-capacity failure during a long task.

Study:

- when compaction occurs;
- where compacted state is stored;
- whether execution blocks;
- recovery;
- provider coupling;
- failure semantics;
- whether compaction can be resumed/recomputed.

---

## Case D — Attempt Outcome != Implementation Reality

Watt has already experienced an execution interrupted by quota after substantial
implementation and partial validation were complete.

The correct recovery approach was:

do NOT blindly replay the whole mission

but:

Repository / workspace Reality Check
→ inspect completed work
→ inspect missing verification
→ continue only unfinished work.

Study whether mature agents support this explicitly.

This principle must survive:

> Attempt status does not automatically equal repository implementation reality.

---

# 6. Agent / Executor Loop

Trace the actual execution loops in Codex, OpenHands, SWE-agent, Aider and other
relevant subjects.

Determine:

- how a task enters execution;
- observe → reason → act loops;
- planning;
- tool call generation;
- tool result ingestion;
- self-correction;
- completion detection;
- runaway prevention;
- retry;
- bounded autonomy;
- failure propagation.

Explicitly separate:

MODEL responsibility

from

RUNTIME responsibility.

For Watt determine what belongs in the Watt-native Executor kernel.

---

# 7. Workspace Architecture

This is HIGH PRIORITY.

Study:

- worktree/workspace creation;
- repository checkout;
- source baseline;
- dirty-tree handling;
- snapshotting;
- isolation;
- concurrent execution;
- workspace persistence;
- cleanup;
- crash recovery;
- repository switching;
- multi-repository workspaces.

Watt's likely conceptual direction is:

Work
→ relevant Assets
→ PWU Execution Scope
→ Execution Workspace
→ Executor

Do NOT encode Workspace == Repository.

A workspace may eventually contain:

- multiple repository mounts;
- generated files;
- temporary build output;
- test/runtime resources;
- context package;
- checkpoint state;
- evidence.

Investigate how external systems handle these.

---

# 8. Repository Capability / Authorization Boundary

Repository authorization is NOT being implemented now, but Executor architecture
must not block its future introduction.

Preserve the product rule:

> Assets are optional inputs to Work.

When a Human provides an Asset, future Watt should perform:

Asset Reference
→ Discovery
→ Capability Check
→ Authorization
→ Production Binding

Repository URL != Repository Access.

Future repository capabilities may include:

- READ
- WRITE
- CREATE_BRANCH
- CREATE_PR
- PUSH

Authorization may be:

- UNKNOWN
- GRANTED
- DENIED

Study how external systems provision repository credentials and permissions.

Do not recommend exposing credential/tool complexity unnecessarily to ordinary
users.

---

# 9. Tool Runtime

Study how external systems implement and govern:

- shell;
- filesystem;
- editing;
- Git;
- search;
- test execution;
- build;
- package manager;
- browser;
- network;
- external APIs;
- process lifecycle.

Research:

- tool registry;
- tool contracts;
- synchronous/asynchronous tools;
- timeout;
- cancellation;
- streaming output;
- output truncation;
- sandboxing;
- environment variables/secrets;
- dangerous actions;
- approval policies;
- retries;
- idempotency.

Important Watt principle:

Tool / Skill / MCP / Harness are implementation mechanisms.

They should not automatically become first-class user-facing product concepts.

---

# 10. Least Privilege / Need-to-Act

Study how tools/resources are provisioned to execution.

Future Watt direction:

> Least Context / Need-to-know for information
> Least Privilege / Need-to-act for capabilities.

An Executor/PWU should receive only the capabilities and Assets needed for the
current production objective.

Explore:

- task/PWU-scoped credentials;
- temporary capability grants;
- automatic provisioning;
- expiration/revocation;
- repository-specific scope;
- tool-specific scope.

The Human should not need to act as a manual permission administrator for
ordinary production.

---

# 11. Context Architecture

Study:

- repository understanding;
- context selection;
- prompt assembly;
- repository instructions;
- history;
- context growth;
- compaction;
- summarization;
- retrieval;
- caching;
- context reuse;
- model-visible runtime state.

But preserve:

> Conversation is not Truth.

and:

> Repository Reality is not automatically Product Intent.

Future ECF is NOT ordinary RAG or chat-summary memory.

ECF's intended role is to provide decision-scoped engineering context such as:

- Product North Star;
- Work Intent;
- Architecture Reality;
- Repository Reality;
- historical rationale;
- invariants;
- required/deferred capability;
- findings;
- evidence.

Executor should expose a clean future ECF seam but must not become ECF.

Identify:

- what context Executor itself must persist;
- what context should be assembled externally;
- what can be compacted safely;
- what must never be replaced by lossy summary.

---

# 12. Pause / Resume / Stop / Retry / Recovery

This is one of the most important study areas.

Do NOT treat these as equivalent operations.

Research exact semantics in external systems for:

- graceful pause;
- hard cancel;
- user stop;
- provider interruption;
- process crash;
- machine/client restart;
- network loss;
- tool timeout;
- partial workspace mutation;
- retry;
- resume;
- fork;
- recovery from UNKNOWN.

For each system determine what survives:

- repository changes;
- workspace;
- execution state;
- conversation/model state;
- local plan;
- tool state;
- event history;
- checkpoints.

The Watt Blueprint must eventually define precise semantics rather than merely
having buttons called Pause/Resume/Retry.

---

# 13. Checkpoint Semantics

Explicitly distinguish:

## Repository Checkpoint

A Git/tree/snapshot state.

## Execution Checkpoint

Where the runtime can safely continue execution.

## Semantic / Context Checkpoint

What the Executor knows about the objective and current reasoning state.

These are NOT automatically the same thing.

Study:

- Git commits;
- worktrees;
- filesystem snapshots;
- event sourcing;
- database state;
- serialized sessions;
- model summaries;
- replay logs.

For every pattern determine:

- what it protects;
- what it cannot restore;
- cost;
- correctness;
- storage;
- portability.

---

# 14. Execution Evidence

Executor must eventually produce native execution evidence.

Study how systems expose:

- commands;
- tool calls;
- file changes;
- patches;
- tests;
- build output;
- failures;
- timing;
- model/provider;
- token/resource usage;
- checkpoints;
- final artifact.

Preserve Watt ownership:

Executor produces execution evidence.

Verification / Guardian evaluates evidence and quality truth.

Executor must not be able to simply declare its own work trustworthy.

Human Product Acceptance remains separate again.

---

# 15. Guardian Boundary

Future Guardian is an independent Engineering Assurance System.

It is not:

- an Executor subroutine;
- a code-review wrapper;
- a second agent inside the Executor.

Study external systems for useful verification/evaluation ideas, but preserve:

Executor
→ Evidence

Verification / Guardian
→ independent assessment

Human
→ final product/governance authority where required.

Also investigate how pre-execution task qualification could eventually prevent:

> correct execution of the wrong task.

But do NOT implement Guardian in this mission.

---

# 16. Human Intervention

Study how mature agents allow Human intervention during long execution:

- message while task runs;
- steer;
- pause;
- change constraint;
- reject approach;
- approve destructive action;
- answer clarification;
- queued input;
- cancel;
- resume.

For Watt, Human input during an active Work/PWU must not be blindly appended to
the model conversation.

It may represent:

- new fact;
- new constraint;
- correction;
- request;
- scope change;
- unrelated Motive;
- Human decision.

WIC / Work governance owns interpretation of Human intent.

Executor receives admitted change to its execution contract/context.

Research how to maintain execution continuity without allowing conversational
input to silently redefine Work truth.

---

# 17. Human Authority

Preserve:

Human Governor owns:

- goal;
- direction;
- important product decisions;
- risk tolerance;
- material authorization;
- acceptance where required.

But Human should NOT become:

- retry button operator;
- test failure relay;
- Git administrator;
- model-error dispatcher;
- micro task planner.

Ordinary engineering recovery must remain autonomous.

Study where external systems overuse Human approval and where they successfully
avoid unnecessary interruption.

---

# 18. Preview / Authorization / Acceptance

Watt has already discovered that asking Human to authorize a Candidate before
the Human can meaningfully inspect its outcome creates poor product experience.

The study should therefore consider future Executor support for:

Candidate / artifact
→ isolated preview/runtime where possible
→ Human visibility
→ governance authorization
→ trusted integration
→ final Product Acceptance

Do NOT collapse:

Verification
Authorization
Product Acceptance

into one status.

Do not redesign the UX now, but ensure the Executor runtime can expose enough
state/artifacts for the future Human journey.

---

# 19. Production Execution Package / Production Passport

Preserve this future concept as a design input.

Long-term Watt should be able to reconstruct:

- what objective was executed;
- which context/version was used;
- which model/provider;
- which tools;
- which workspace/repository states;
- which attempts;
- which evidence;
- which verification;
- what artifact was produced;
- why the result is trusted.

Desired properties include:

- replayability;
- portability;
- root-cause localization;
- multi-model reproducibility where feasible.

Study whether any external system provides useful mechanisms toward this.

Do NOT prematurely implement the Passport.

---

# 20. Model / Provider Abstraction

Future target:

Watt-native Executor Runtime
→ replaceable model/provider resources.

Study:

- model APIs;
- tool-use differences;
- reasoning effort;
- streaming;
- structured output;
- prompt ownership;
- model session state;
- model switching;
- fallback;
- capacity failure;
- quota failure;
- provider timeout.

Watt execution truth must not depend on one provider's proprietary lifecycle.

Study how much execution state can survive replacing the model mid-PWU.

This is directly relevant to the PWU continuity benchmark.

---

# 21. Capacity / Quota / Resource Governance

Real Watt usage has encountered:

- weekly quota exhaustion;
- model capacity failures;
- long active turns;
- expensive high-reasoning runs;
- poor ROI from using top-tier reasoning on low-value refinement.

Executor architecture should treat compute as a governed production resource.

Research possible mechanisms for:

- model capacity failure classification;
- retry/backoff;
- safe provider/model fallback;
- budget;
- token/resource accounting;
- execution cost visibility;
- preventing accidental transition into expensive usage;
- deciding when expensive reasoning is justified.

Do not create billing architecture in this study.

But identify Executor-level seams required for future resource governance.

---

# 22. Performance and Responsiveness

HIGH PRIORITY.

Human testing of Watt currently feels slow across:

- conversation;
- state transitions;
- production execution;
- runtime handling.

Some may come from:

- model latency;
- orchestration;
- Docker/local environment;
- filesystem;
- database;
- polling;
- UI rendering.

Do NOT assume the model is the only bottleneck.

Study mature implementations for:

- time-to-first-action;
- tool startup;
- process reuse;
- persistent execution workers;
- connection/session reuse;
- workspace initialization;
- repo scanning;
- incremental context assembly;
- parallelizable operations;
- async execution;
- event streaming;
- UI progress reporting;
- compaction latency;
- retry latency;
- caching;
- warm runtime;
- command execution overhead.

Distinguish:

1. Model/provider latency
2. Runtime/orchestration latency
3. Tool/workspace latency
4. Infrastructure latency
5. Perceived latency

Future Watt should instrument the lifecycle rather than optimize blindly.

---

# 23. Execution Visibility

A long task may legitimately take minutes.

Human experience should not become:

spinner
→ spinner
→ spinner.

Study what external systems surface during execution:

- current phase;
- current meaningful action;
- completed actions;
- tests running;
- blockers;
- waiting reason;
- next likely action.

Future UX is deliberately postponed until PWU/Executor semantics stabilize.

Therefore this study should define:

> what execution events/state must exist

not:

> what the final UI should look like.

---

# 24. Software / Delivery Form Independence

Do not design Executor only for static Web applications.

Watt delivery may eventually include:

- Web application;
- backend/API;
- CLI;
- library;
- mobile app;
- mini program;
- automation;
- other software artifacts.

Executor Runtime should produce governed software/artifact results without
hardcoding one delivery form.

Deployment/runtime adapters are separate concerns.

---

# 25. Internal Repository / Watt-managed Git Direction

Future Watt may provide a default internal Git/code-management platform.

If Human does not specify an external repository:

Watt should still be able to create and manage a production workspace/repository.

If Human supplies GitHub/GitLab/enterprise Git:

future Repository Provider Integration handles access and authorization.

Study external implementation patterns useful to this future design.

Do not implement Git hosting during this mission.

---

# 26. Research Prioritization

Not all ten repositories should receive equal depth.

Use them according to their strengths.

Expected starting hypothesis:

PRIMARY EXECUTOR SOURCES:
- codex
- OpenHands
- SWE-agent
- aider

HUMAN / CONVERSATION RUNTIME:
- LibreChat
- open-webui
- lobehub

PUBLICLY AVAILABLE CLAUDE CODE MECHANISMS:
- claude-code

DURABLE ORCHESTRATION / STATE:
- langgraph

MULTI-AGENT / ORCHESTRATION REFERENCE:
- autogen

But revise this ranking based on actual source depth.

Do not waste significant time reverse-engineering shallow or irrelevant areas.

---

# 27. Source-level Research Method

For every relevant repository:

1. record local path and exact commit SHA;
2. read architecture/design docs;
3. find runtime entrypoint;
4. trace one real task lifecycle;
5. trace session/state persistence;
6. trace workspace creation;
7. trace tool execution;
8. trace model/context path;
9. trace failure/recovery path;
10. inspect tests proving behavior;
11. inspect UI/event handling only where relevant;
12. distinguish directly proven behavior from inference.

Prefer source + tests over README claims.

Do not exhaustively read every file.

---

# 28. Comparative Architecture Matrix

Do not write ten unrelated project summaries.

Build comparison around engineering problems.

At minimum compare:

- core agent loop
- local planning
- session model
- attempt model
- workspace
- multi-repository behavior
- tool runtime
- sandbox/capabilities
- context assembly
- compaction
- checkpointing
- pause/resume
- cancellation
- UNKNOWN recovery
- client/process restart
- Human steering
- evidence
- verification separation
- provider abstraction
- model replacement
- performance
- resource/cost telemetry
- execution observability

For each important pattern:

External mechanism
→ Why it exists
→ Source evidence
→ Limitations
→ Watt compatibility
→ Adopt / Adapt / Reject
→ Blueprint implication

---

# 29. Adopt / Adapt / Reject

Every important discovered mechanism receives:

ADOPT
ADAPT
REJECT

Examples of the required reasoning style:

Codex session persistence
→ potentially ADAPT
→ valuable for Executor continuity
→ but chat/session state must not become Work Truth.

External one-repository sandbox
→ potentially ADAPT or REJECT
→ useful isolation technique
→ but must not impose one-repository Work/PWU semantics.

Automatic retry
→ potentially ADAPT
→ useful for transient provider failures
→ but UNKNOWN outcome must reconcile workspace reality before replay.

---

# 30. Anti-copy Rules

Do NOT conclude:

"Codex does X, therefore Watt should do X."

Do NOT make any external implementation the architecture authority.

Do NOT import assumptions such as:

- CLI is the product;
- session = Work;
- chat history = truth;
- one repo = task;
- model = Executor;
- provider state = execution state;
- agent self-evaluation = assurance;
- Human must approve every shell command.

Watt is a Software Production System.

These external systems are reference production machines.

---

# 31. Blueprint Questions That Must Be Answered

The final study must provide evidence-backed recommendations for all of these:

1. What exactly belongs inside the Watt-native Executor kernel?
2. What remains in Work / Steering / PWU / SPG?
3. What is PWU's runtime relationship to Execution Session?
4. Should PWU have multiple Attempts?
5. What constitutes a new Attempt?
6. What execution state must be durable?
7. What can safely remain ephemeral?
8. What does Pause mean?
9. What does Resume mean?
10. What does Retry mean?
11. What does Stop/Cancel mean?
12. What is recoverable after client/process death?
13. How should UNKNOWN execution be reconciled?
14. What constitutes a checkpoint?
15. How are repository/execution/context checkpoints separated?
16. How should Execution Workspace be modeled?
17. How should multiple repositories be handled?
18. How should read/write execution scope work?
19. How autonomous should Executor local planning be?
20. How are tools provisioned?
21. How should least-privilege capability grants work?
22. What execution evidence must be emitted?
23. How should Guardian consume that evidence later?
24. How should Human steer a running PWU?
25. How should active Human corrections alter execution safely?
26. How should model/provider abstraction work?
27. Can a running PWU survive model replacement?
28. How should context be persisted and compacted?
29. Where will future ECF plug in?
30. What must be observable for future UX/Control Room?
31. What mechanisms are needed for Production Passport/replay?
32. What performance instrumentation must exist from day one?
33. What architecture mechanisms reduce actual/perceived latency?
34. How should provider capacity/quota failures be handled?
35. What resource/cost telemetry belongs in Executor Runtime?
36. What should Watt intentionally NOT copy from Codex?
37. Which OpenHands / SWE-agent / Aider ideas materially improve Watt?
38. Which external systems expose approaches that conflict with Watt?
39. Which questions still require Human Governor decisions?
40. Is the architecture evidence sufficient to begin the Watt Executor Blueprint?

None of these questions may silently disappear from the final study.

---

# 32. Required Deliverables

Create durable research documents under Watt's documentation conventions.

Recommended:

`docs/research/external-executor-architecture-study.md`

`docs/research/external-executor-pattern-matrix.md`

Optional focused appendices are allowed if the main study would become unreadable.

The output must contain:

A. Executive Summary

B. Watt Current Reality

C. Repositories / Exact Revisions Studied

D. Core Execution Loop Findings

E. PWU / Session / Attempt Findings

F. Workspace / Multi-Repository Findings

G. Tool Runtime / Capability Findings

H. Context / Compaction / ECF Seam Findings

I. Pause / Resume / Recovery / Checkpoint Findings

J. Human Control Findings

K. Evidence / Verification / Guardian Findings

L. Provider / Model / Resource Findings

M. Performance / Observability Findings

N. Production Passport / Replay Findings

O. Adopt / Adapt / Reject Matrix

P. Explicit Watt Blueprint Recommendations

Q. Open Architecture Decisions

R. Architecture Risks

S. License / Code Reuse Constraints

T. Blueprint Readiness Gate

---

# 33. Blueprint Readiness Gate

At the end, explicitly classify:

READY_FOR_WATT_EXECUTOR_BLUEPRINT

or

NOT_READY_FOR_WATT_EXECUTOR_BLUEPRINT

If NOT READY:

list only true unresolved architecture questions that require further study or
Human decision.

Do not classify ordinary implementation uncertainty as an architecture blocker.

---

# 34. Scope Boundary

This mission is RESEARCH ONLY.

Do NOT:

- implement Watt-native Executor;
- change PWU lifecycle;
- replace Codex adapter;
- implement ECF;
- implement Guardian Core;
- redesign UX/UI;
- build Watt Git hosting;
- implement OAuth;
- implement Runtime Manager;
- copy external project code into Watt.

Documentation and evidence only.

---

# 35. Completion Standard

This study is complete only when:

- all ten local repositories were triaged;
- high-value repositories received source-level inspection;
- actual execution paths were traced;
- real tests/source locations support conclusions;
- every major Watt design concern above is covered;
- Adopt / Adapt / Reject decisions exist;
- Blueprint inputs are concrete;
- unresolved questions are explicit;
- no major previously established Watt invariant was silently overridden.

The final response to Human should be concise:

- repositories studied;
- strongest mechanisms discovered;
- most important Watt adaptations;
- most important mechanisms rejected;
- unresolved Human decisions;
- Blueprint readiness;
- documentation paths.

Do not begin Blueprint implementation.

STOP.