# Watt — External Executor Architecture Study

Research baseline: **2026-09-10**; completed **2026-09-11 (Asia/Shanghai)**. Watt source: `a0394daaa59351f7e92a3f4f2482e675e751a64e`.

Status: **READY_FOR_WATT_EXECUTOR_BLUEPRINT**. This is evidence and proposed Blueprint input, not an admitted Blueprint, lifecycle change, implementation authorization, or Human product acceptance.

Mission: [research contract](executor-architecture-study-research-contract.md).

Companions: [problem-oriented pattern matrix](external-executor-pattern-matrix.md) · [exact revisions and source evidence](external-executor-source-evidence.md).

## A. Executive summary

Watt should own the execution contract binding, workspace, tool effects, recoverable execution state, evidence and resource accounting. The model should supply reasoning and proposed actions through a replaceable inference interface. None of the ten systems supplies Watt's complete production/governance model. The useful result is a set of mechanisms with explicit limits, not selection of an external architecture as authority.

The strongest mechanisms are:

1. **Codex:** a runtime-owned model/tool loop; canonical rollout and context reconstruction; a separate server/client lifetime; centralized sandbox/approval handling; reusable interactive processes; compaction and phase timing. Its provider-specific compaction and conversation authority need substantial adaptation.
2. **LangGraph:** checkpointed execution state and pending successful writes, explicit durability modes, resumable interrupts, and bounded retry/timeout machinery. Node replay does not make arbitrary shell or API effects safe to repeat.
3. **SWE-agent:** explicit action/observation trajectories and salvage of patches after cost/environment failure. Its clean-reset retry strategy is unsuitable as Watt's default recovery.
4. **Aider:** dirty-change preservation, structured editing with local feedback, and incremental repository context. Automatic commits, per-file conversational approval and a single-repository assumption are not Watt governance.
5. **LibreChat and LobeHub:** surprisingly substantial generation/step runtime code in these revisions. Generation fences, receipts, replayable progress, owned locks, persisted cancellation and context replacement discipline materially improve the Blueprint inputs.

The inventory changes the proposed research ranking. Local **OpenHands is now Agent Canvas**, with core Python execution moved to `software-agent-sdk`; this checkout proves frontend/backend boundaries and control/reconnect requests, not CodeAct internals. **claude-code does not expose its core executor** here. These are explicit evidence limits, not excuses to substitute remembered older implementations. All ten local repositories were triaged; none was downloaded or modified. The detailed register contains **47 evidence groups and 185 source/test/document anchors**.

The recommended model is **PWU as governed production contract and lifecycle → multiple execution Attempts, with reconstructible Session continuity and explicit Steps**. An Attempt denotes an execution grant's continuity, not a prompt, model call, job delivery or process. A Session is a runtime continuity container, not Work identity or Truth. Local planning remains autonomous inside an admitted envelope. Model changes must preserve contract and artifact lineage; they cannot silently inherit inaccessible provider state.

The central recovery rule is: **first establish who can still act, then inspect what actually happened, then continue only unfinished obligations**. UNKNOWN is uncertainty about effects/outcome, not proof of no work and not permission to replay. This extends Watt's existing salvage boundary rather than replacing it.

## B. Watt current Reality and intended direction

The implementation is authoritative for current behavior. The North Star, Work/PWU principles and the Human mission are authoritative for intended direction. Earlier MVP restrictions are dated implementation scope, not permanent product constraints.

| Concern | Current implementation / source | Intended boundary preserved in this study |
|---|---|---|
| Human Collaboration / WIC | Durable interaction records and assessments; admission checks exact current basis. Conversation realization is separate from semantic interpretation. [W01](external-executor-source-evidence.md#w01) | WIC interprets Human input; conversation is provenance, not production authority. |
| Design Intent Framing | Typed frame and framing contracts participate in interaction understanding. | Product/engineering intent cannot be reconstructed solely from repository contents. |
| Guided Design | Versioned agenda, issue/readiness handling and stored semantic results. [W02](external-executor-source-evidence.md#w02) | Design decisions stay outside Executor local technique. |
| Work / Work Reality | Governed Work revisions, scope and attributable assets; repository fields can be absent. | No first-class Project. Existing/new software use the same Work model. |
| Work Assets / multi-repository | EngineeringResource/Scope and repository intake; baselines addressed by repository identity/ref. Work can retain several bindings; current production targets one repository. | One Work and one future PWU may legitimately involve several writable repositories. |
| Repository-optional production | Deterministic managed local Git workspace allocated at production readiness; unobservable remote references remain UNRESOLVED. [W02](external-executor-source-evidence.md#w02) | Repository infrastructure is required by today's Git mechanics, not a required Human input or Work identity. |
| Steering | Admitted decisions against exact Work/plan/Reality fingerprints. | Owns WHAT NEXT: objective, why, admissible scope. Executor owns HOW. |
| PWU / SPG | PWU, Completion Contract, Attempt generation, prepared context/MEI, dispatch, observation, completion and trust chain. | Govern meaningful production envelopes, not each edit/test. PWU must preserve continuity without monolithic execution. |
| Current Executor | Dedicated local process boundary and synchronous Codex SDK adapter. `ephemeral=True`, default three internal provider turns; timeout, repeat-summary and continuation checks; one report. [W03](external-executor-source-evidence.md#w03) | Future native loop owns durable execution. Current adapter is not replaced by this mission. Repeat-summary detection is a weak proxy for progress. |
| Workspace | Detached worktree per Attempt outside authoritative checkout, one exact source revision; clean preparation and dirty-but-same-basis continuation validation differ. [W04](external-executor-source-evidence.md#w04) | Execution Workspace becomes a resource container with plural mounts, not another word for repository. |
| Verification / Candidate | Independent observed proposed snapshot and exact-obligation Verification; separate Candidate sealing and authorization. [W05](external-executor-source-evidence.md#w05) | Executor reports evidence, never its own trust verdict. |
| Human authorization / Trusted Runtime Commit | Exact authorized Candidate, repository integration effect and subsequent Runtime Commit; repository/ref locking and compare-and-set basis. | Local Executor checkpoints cannot advance trusted refs or authorize external effects. |
| Delivery / Human Product Acceptance | Document and software manifest/package lineage; local static-Web runtime capability; acceptance names exact manifest. Delivery requires trusted commit and PASS evidence. [W07](external-executor-source-evidence.md#w07) | Future pre-authorization Candidate preview needs a distinct runtime seam; acceptance stays separate from authorization and Verification. |
| Recovery | Independent re-observation, salvage and new-generation retry already exist. Tests explicitly preserve valid work despite FAILURE/UNKNOWN. Provider resume is unimplemented. [W06](external-executor-source-evidence.md#w06) | Extend recovery for useful partial work and native session continuity; do not rewrite immutable historical outcomes. |
| Runtime / responsiveness | Local Docker composition and host process orchestration; progress/active-work bookkeeping partly process-local. DCP-2 projects existing timestamps, with unavailable fields explicit. [W08](external-executor-source-evidence.md#w08) | UI survival, worker survival and machine survival must become separate guarantees. Instrument before selecting optimizations. |
| ECF / Guardian / Passport | Future directions, not implemented systems. [W09](external-executor-source-evidence.md#w09) | ECF supplies decision-scoped context; Guardian independently assures engineering; Passport connects authoritative lineage without replacing it. |

A key compatibility constraint: the current [Executor autonomy contract](../architecture/executor-autonomy-envelope-attempt-granularity-mvp-contract.md) defines a continuous Attempt under stable workspace, basis, authority, executor binding and budget, and defers precise internal-turn resume. This study recommends evolution of that boundary for the Blueprint; it does **not** claim native durable resume already exists or silently change the existing contract.

### Observed failures and latency baseline

Case A is directly documented: a real software-delivery Attempt reported `Selected model is at capacity`, remained UNKNOWN with no changes, and a separately admitted recheck later succeeded. That recheck is historical evidence, not the desired future recovery model. [W09](external-executor-source-evidence.md#w09)

Cases B (client restart followed by continuation), C (remote compact/capacity failure), and D (quota interruption after substantial implementation) are Human-supplied incidents in this mission. No exact client deployment trace, provider request trace or local machine snapshot was supplied for them. This study can establish plausible source mechanisms and required Watt semantics; it cannot claim a forensic reconstruction of those particular incidents.

Recorded collaboration measurements are mixed: v3.1 median first text improved **23.84 → 18.80 s**, but mean first text regressed **23.48 → 26.28 s**, and mean completion was effectively unchanged **58.38 → 58.85 s**. These are small reported samples, not a stable p95 or a comparison of executor engines. Coalescing removes a serial model call for eligible pre-Work interaction, while active Work/different configuration retains staged calls. Docker startup, SDK startup, persistence, polling and rendering remain separate possible contributors. [W08](external-executor-source-evidence.md#w08)

## C. Repositories, revisions and research method

Every path below is under `/Users/yu/Documents/dev/reference-lab/`. The source register records full paths, exact HEAD, source locations and constructed commit permalinks.

| Repository | Exact revision | Depth and reason |
|---|---|---|
| codex | `94697375cb9d2aa8ae74d61957c6b396819bec94` | Deep: task/turn loop, rollout, compaction, retries, tools, worktrees, reconnect and tests. |
| OpenHands | `725f5584b9411b1e47f1d0c5ebaf640676609940` | Targeted: Agent Canvas architecture, creation/control API, reconnect and tests. Python backend absent by repository boundary. |
| SWE-agent | `3ea751c087f32b16e039a2233dd6eefecef325d5` | Deep: run entrypoint, agent/requery loop, environment adapter, trajectory, salvage/retry, replay and tests. |
| aider | `5dc9490bb35f9729ef2c95d00a19ccd30c26339c` | Deep: coder loop, structured edits, Git, context cache/summary, provider/model switching and tests. |
| LibreChat | `b356c3d87edccd0bde68dc90a5eca66ae2c80e5d` | Promoted: generation ownership, durable publication, steering receipts and Redis regression specifications. |
| claude-code | `e62465d553ecbf1697219ffbb3c11b4fef14d5bf` | Limited: public hooks/settings/plugins and changelog. No core execution proof. |
| open-webui | `0a7c15832fb30b1903753e83f81dc7d27e5b0944` | Targeted: async tasks, response projections, tool loop and cancellation. Relevant backend test coverage not located. |
| lobehub | `08cbe3236bca1ec4ca48d77058636e1f7e69e06a` | Promoted: AgentRuntime and server step host, Redis/DB state split, compaction and retry tests. |
| langgraph | `e539ac122f4126f6dd850581c1494948cf620e31` | Deep for durability: Pregel loop, checkpoint/pending writes, interrupts, retry/timeout and tests. |
| autogen | `027ecf0a379bcc1d09956d46d12d44a3ad9cee14` | Targeted: Assistant/team loop, save/load, cooperative pause, Docker executor and tests. |

Method: read Watt first; inventory references; read architecture/module contracts; trace selected actual source paths; inspect relevant tests and failure branches; compare engineering problems; derive Watt-specific recommendations. **No external application or test suite was executed**. Test references mean inspected regression specifications, not measured PASS results. Some secondary paths are caller-side evidence only. Findings never infer implementation from README alone.

The SWE-agent README says active development has moved to mini-swe-agent. This study retains the requested local SWE-agent revision as a useful research source; it is not a recommendation to adopt that codebase. [S01](external-executor-source-evidence.md#s01)

This is a snapshot study, not a claim about uninspected newer releases, commercial backends, or unseen dependencies. No substitute repository was needed to answer Watt's architecture questions; gaps are covered by other directly inspected implementations and marked explicitly.

## D. Core execution loop findings

### Actual task paths

| Subject | Traced source lifecycle | Model responsibility | Runtime responsibility / limit |
|---|---|---|---|
| Codex | `RegularTask::run → run_turn → capture_step_context → run_sampling_request → ToolRouter/ToolOrchestrator → tool output/history → follow-up or turn end` | Propose tool calls, implementation reasoning, local plan, final response. | Resolve instructions/tool schemas; execute/cancel tools; enforce policy; record history/events; retry eligible transport errors; compact; decide loop continuation from model/tool/pending-input state. [C01](external-executor-source-evidence.md#c01) |
| SWE-agent | `RunSingle → DefaultAgent.run → step → forward_with_handling → model.query → parse_actions → handle_action → SWEEnv → history/trajectory → done` | Select actions and interpret observations. | Parse/check commands, bounded format requery, time/cost stops, submit extraction, trajectory persistence. SWE-ReX internals are external. [S01–S04](external-executor-source-evidence.md#s01) |
| Aider | `Coder.run/run_one → send_message/send → edit parsing/apply_updates → auto-commit → lint/test → reflected_message → next pass` | Produce edits and propose repairs. | File eligibility, edit application, retries, local feedback, summary and Git handling. Default CLI interaction can ask permission for ordinary fixes. [A01](external-executor-source-evidence.md#a01) |
| LobeHub | `AgentRuntimeService.executeStep → persisted cancellation/owned lock → hydrate → AgentRuntime.step → agent.runner → instruction executor → saveStepResult → schedule/finish` | Inference and action selection behind a runtime instruction protocol. | Step accounting, message/state persistence, tool/result events and continuation. Force-finish produces a final response; it does not prove contract satisfaction. [B01](external-executor-source-evidence.md#b01) |
| LangGraph | `Pregel invocation → load checkpoint/pending writes → prepare tasks → runner/retry → apply writes → checkpoint → next superstep/interrupt` | Optional: only graph nodes using a model. | Graph state transitions, scheduling, interruption and persistence. The graph structure is application-authored; it need not become Watt's Steering plan. [G01–G03](external-executor-source-evidence.md#g01) |
| AutoGen | `team.run_stream → manager/participants → AssistantAgent.on_messages_stream → model client → tool iteration/reflection → Response → termination or next speaker` | Content/tool decisions. | Message delivery, bounded tool iterations, cancellation and explicit state serialization. [T01](external-executor-source-evidence.md#t01) |
| LibreChat | `agents/request.js → createJob with generation/predecessor → agent graph execution/callbacks → manager publications/state → terminal persistence or action wait → reconnect/resume` | Agent graph generates output and calls tools. | Local code proves generation/transport/steering coordination; imported `@librechat/agents` owns portions of the agent graph implementation. [L01–L04](external-executor-source-evidence.md#l01) |
| Open WebUI | `main chat handling → create_task → process_chat_payload/response → bounded tool loop → saved output/events → done/cancel` | Model output/tool requests. | Async task and response lifecycle; no durable suspended Python coroutine. [U01–U02](external-executor-source-evidence.md#u01) |
| OpenHands | `createConversation → backend settings/workdir/worktree payload → ConversationClient → REST history + WebSocket events → interrupt/run request` | Core loop is not in this checkout. | Client routing/control is proven; Agent Server implementation is not. [O01–O03](external-executor-source-evidence.md#o01) |
| Claude Code | Public hook input → command validator → hook exit code; Ralph stop hook → transcript read → continue/stop. | Core loop is not exposed. | Only extension mechanism source is visible. Changelog is claim-level evidence. [H01–H02](external-executor-source-evidence.md#h01) |

**ADAPT:** a small native kernel that owns admitted execution, observation/action loops, effect accounting and safe continuation. **REJECT:** treating a model's final message, a team's termination predicate, or an extension's completion promise as Watt completion.

### Local planning and task redefinition

External systems commonly express a local plan in messages, files, graph state or tool updates. They seldom enforce Watt's distinction between product intention and implementation strategy. Runtime schema validation and sandbox roots can constrain actions; they do not prove that the agent is solving the right problem.

Watt should persist a compact **working plan** (hypotheses, completed implementation steps, unfinished checks and reasons for approach changes) as non-authoritative execution context. It can evolve autonomously. Contract identity/version, admitted asset scope, acceptance criteria and prohibited actions remain immutable references at each boundary. A request to alter those returns a typed boundary finding to WIC/Steering/SPG. Ordinary test failure remains inside HOW.

Runaway control requires separate bounds for elapsed time, provider requests, tool/process time, cost where measurable, repeated action signatures and no-progress windows. A repeated summary alone is not enough; changing prose can hide repeated ineffective actions. Progress metrics should observe changed artifacts, resolved hypotheses and completed obligations without requiring every tool action to succeed.

## E. PWU / Session / Attempt / Step findings

### Recommended conceptual relationships (proposals, not schemas)

```text
Work + governed Reality + Steering decision
  └─ PWU: admitted production objective, constraints, scope and obligations
      ├─ Attempt 1: execution grant/generation; terminal history retained
      ├─ Attempt 2: successor grant after recovery or material replacement
      └─ Execution Session lineage: reconstructible continuity used by Attempts
          ├─ provider binding episodes / model calls
          ├─ local plan, observations, open hypotheses
          └─ execution Steps and checkpoint references
```

A PWU can exist before any execution Session. Permit **zero or more Sessions and multiple Attempts**. Default to one continuity lineage for an ongoing PWU; a Session can carry context across successor Attempts, while every continuation names exactly which Attempt currently authorizes effects. A fork/independent implementation may get a separate Session with an explicit parent checkpoint. Do not encode that all Sessions or Attempts execute concurrently.

An **Attempt** is the accountable execution grant against one PWU contract version, source version vector, workspace continuity and resource envelope. A worker process restart or an internal model request retry does not inherently change the production objective. A new worker lease epoch can fence an old process without redefining PWU; whether it can continue the same Attempt depends on a validated execution checkpoint and unchanged admitted grant. This is a proposed native extension beyond today's deferred durable resume.

Create a **new Attempt** when the prior grant is terminal/released/fenced, workspace integrity is lost, the source/admitted contract materially changes, governed recovery authorizes re-execution, or executor/provider replacement changes the admitted execution binding. A materially different objective may require Steering to revise/decompose/replace the PWU, not merely another Attempt.

Default recommendation for model replacement: same PWU and reusable Session context, **new Attempt with explicit predecessor and handoff checkpoint**. The Blueprint may admit compatible model changes within an Attempt as a versioned binding episode only if authority, policy and cost envelope explicitly allow it. Do not assume today's adapter binding already permits that. This conservative default resolves lineage without turning every API retry into an Attempt.

A **Step** is a runtime-accountable boundary: a model request, tool invocation/effect, observation, contract update application, checkpoint or handoff. It is neither an SPG Steering Step nor a unit of product decomposition. Stream chunks and polling calls need not each be domain Steps. Tool-call IDs and semantic operation IDs differ: a provider may regenerate an ID on retry; Watt must retain its own effect identity.

### Persistence split

| Durable before proceeding | Durable at result/checkpoint | May remain ephemeral or regenerable |
|---|---|---|
| PWU/contract/context versions; current Attempt and worker epoch; scope/capability/budget binding; workspace/source vector; admitted intervention receipt; identity and effect classification of a tool about to act | Tool outcome/unknown receipt, mutation/evidence digest, model request/output references, usage, working plan/checkpoint, errors and reconciliation, stop reason, emitted event cursor | UI spinner/text rendering state; raw token deltas after final output is retained; process handle caches; recomputable repo indexes; prewarm connection; temporary parsing state |

The raw input/output needed to explain an action must be retained or content-addressed before relying on it as recovery evidence. Store tools' full bounded evidence separately from model-visible truncation. Do not persist private model chain-of-thought as a dependency; retain conclusions, decisions, evidence and explicit working state. Provider opaque state can be optional auxiliary data, never the only continuity record.

PWU completion remains governed: **Executor result ready → independent observation → Completion Evaluation → Verification → existing produced/satisfied semantics and SPG gates**. Attempt exhaustion does not complete PWU. A satisfied PWU does not automatically complete Work, authorize integration or constitute Human Product Acceptance. Session idle/closed is also independent.

These recommendations adapt Codex reconstruction, LangGraph pending writes and LobeHub step state while preserving Watt's existing multiple-turn Attempt semantics. [W03/W06](external-executor-source-evidence.md#w03), [C02](external-executor-source-evidence.md#c02), [G01](external-executor-source-evidence.md#g01), [B01](external-executor-source-evidence.md#b01)

## F. Workspace and multiple repositories

### Model an execution environment, not a repository

Recommended conceptual inventory:

| Workspace component | Required identity / recovery property |
|---|---|
| Workspace itself | Stable workspace ID, owning Work/PWU/Attempt lineage, host/backend and lifecycle; independent of directory path. |
| Repository mounts | Asset ID, repository identity, exact source commit/tree, mount path, admitted RO/RW paths and integration target; plural. |
| Non-repository inputs | Document/context artifacts and digests; generated assets; explicit provenance and write scopes. |
| Mutable production output | Per-mount changes, generated/untracked files, binaries and mode/link metadata; do not assume `git diff` captures everything. |
| Runtime/test resources | Environment/image digest, dependency locks, toolchains, service endpoints, scoped database fixtures, process receipts. |
| Recovery material | Repository snapshots, execution/event checkpoints, semantic checkpoint and evidence blobs, with retention/pinning. |

Source patterns: Codex worktree manager creates a detached tree at resolved commit and guards cleanup; Aider preserves dirty edits before generated changes; AutoGen can mount several RO/RW volumes; OpenHands requests either a local repo or new worktree. None of these supplies a proven governed cross-repository transaction. [C08](external-executor-source-evidence.md#c08), [A02](external-executor-source-evidence.md#a02), [T03](external-executor-source-evidence.md#t03), [O01](external-executor-source-evidence.md#o01)

For Watt, allocate per-attempt writable overlays/worktrees or another equivalent isolation mechanism, with reusable read-only caches. Preserve pre-existing dirty work as attributable input where admitted; otherwise fail preparation with a precise reason. Never silently commit or discard Human changes. A local Git worktree shares repository metadata/object storage: it is **not an OS security boundary**. Enforce write restrictions and credential isolation at the actual tool host/container boundary.

If no repository is supplied, allocate a Watt-managed local workspace/repository when code production needs it, as current Reality already does. Repository-provider creation and hosted Git are separate future integrations. Read-only repository switches within admitted mounts are ordinary HOW; adding a new writable asset or expanding paths requires governed scope change.

### Multi-repository production and integration

Use an **exact source vector** `{asset A → commit/tree A, asset B → commit/tree B, ...}` and an output vector with changes/evidence per mount. An API/backend plus client-library change may be one coherent PWU when it has shared intent and recoverable verification. Repository count alone is not a decomposition rule.

Concurrent read operations and independent builds can proceed in parallel. Concurrent mutations must use declared conflict domains (path/repository/service) and owned workspace leases. Protect a shared Git index/ref and overlapping write mounts. Unknown shell footprints require conservative serialization inside the relevant writable scope. A model's parallel-tool flag is not sufficient conflict analysis.

Verification must name the entire candidate vector and cross-repository compatibility checks, not just independent unit-test passes. A later ref change invalidates the affected source assumption and potentially aggregate evidence; rebasing cannot silently reuse old authorization.

There is no general atomic transaction across independent Git remotes plus Watt's database. Recommended Blueprint direction:

1. Prepare immutable per-repository candidate snapshots and one aggregate candidate manifest.
2. Verify the exact vector and authorize the named integration scope.
3. Integrate each target under expected-old-ref checks, recording prepared/converged/unknown effects.
4. Record partial convergence honestly; recover forward where authorized, or use explicitly authorized compensation. Do not claim the whole Work result is integrated before all required components converge.
5. Preserve any already valid per-repository trust facts. Do not rewrite history to simulate global rollback.

This is an **ADAPT/R recommendation**, grounded in Watt's existing Git/DB convergence protocol and external isolation/checkpoint limits. It is not a claim that an inspected agent implements distributed Git atomicity. The Blueprint must settle aggregate authorization/integration policy; the lack of physical atomicity is already understood and is not a reason to forbid a multi-repository PWU.

Workspace cleanup is a separate retained-resource operation: deny while active, leased, awaiting reconciliation, pinned by Candidate/Verification/preview, or holding unexported output. Retention expiry should not silently invalidate promised resume. Cache deletion is different from deleting the sole copy of work.

## G. Tool runtime, capabilities and repository authorization

### Tool kernel responsibilities

A model-visible registry should correspond to host-executable, versioned tool contracts. Each invocation needs validated inputs, admitted scope, timeout/cancellation semantics, output limit, streaming mode, effect classification and evidence policy. Codex demonstrates centralized routing and enforcement; SWE-agent separates agent code from a deployment/runtime seam; AutoGen shows a reusable Docker command executor. [C06–C07](external-executor-source-evidence.md#c06), [S03](external-executor-source-evidence.md#s03), [T03](external-executor-source-evidence.md#t03)

| Tool family | Native runtime responsibility / adaptation |
|---|---|
| Shell / processes | Exact cwd/environment/image; process/group identity; streaming output; separate yield time from execution deadline; graceful interrupt and hard kill receipt; descendant cleanup; retained final output. |
| Read/search/filesystem | Canonical path validation, mount scope, symlink traversal policy, bounded output, attributable file digests. Repository instructions are untrusted input unless separately admitted. |
| Edit / patch / Git | Expected file/tree preconditions, before/after identity, multi-file partial-failure report; protect authoritative refs. Tool success does not imply all edits happened atomically. |
| Test / build / package manager | Exact command/toolchain/source subject, admitted network and dependency access, process lifecycle, complete logs; installation is an effect, not pure reasoning. |
| Browser / preview | Isolated runtime/session with explicit target artifact, network and data scope; expose lifecycle and access information. Browser state is not restored by a Git checkpoint. |
| Network / external APIs | Destination/capability allowlists, credential handle injection, request/effect receipt, safe retry or provider reconciliation. Push, PR creation and deployment require distinct capabilities. |
| Async tools | Durable operation ID, owner epoch, start/completion/unknown status, reconnect/query/cancel interface; no automatic re-invocation simply because the caller disconnected. |

The runtime should classify effects as **read-only**, **idempotent with a stable key/precondition**, **reconcilable mutation**, or **non-replayable/unknown**. Retries depend on the classification plus observed execution phase. A tool's error text saying “retry” is insufficient for mutations; LobeHub's generic retry helper requires this Watt adaptation. A failed sandbox invocation can also have partial side effects, so escalation must not presume an empty workspace. [B04](external-executor-source-evidence.md#b04)

### Need-to-act without manual permission administration

Preserve the future chain: **Asset Reference → Discovery → Capability Check → Authorization → Production Binding**. A repository URL is not access. Model repository capability and authorization separately, including READ, WRITE, CREATE_BRANCH, CREATE_PR and PUSH with UNKNOWN/GRANTED/DENIED. A grant must name repository/mount/path/tool/action and relevant destination, not merely “Git allowed”.

An admitted PWU should cause a provisioning service to derive the minimum sufficient grants automatically from its needs and existing Human authority. Executor receives short-lived **credential handles**, not a product-facing pile of tokens or a user's entire environment. The broker/tool host resolves them only at need, applies per-resource scope, redacts secrets from output/evidence and revokes or expires them. Resume reacquires and revalidates authority; it does not replay expired secrets from a checkpoint. Revocation should fence new effects and stop/reconcile already running ones.

External evidence is partial: Codex implements policy/sandbox and approval caching; OpenHands' client separates backend-held/encrypted settings and API session credentials; AutoGen supports mount access modes; Claude Code examples expose managed permission policy. SWE-agent exposes configured environment propagation and warns in source that values can appear in debug logs; Watt should not copy that as credential isolation. None proves the full Work/PWU-scoped credential lifecycle Watt needs. Treat that lifecycle as a **Blueprint seam**, not an externally solved end-to-end feature. [C06](external-executor-source-evidence.md#c06), [O01](external-executor-source-evidence.md#o01), [H01](external-executor-source-evidence.md#h01)

**REJECT** exposing Tool/Skill/MCP/Harness as mandatory first-class Human product concepts, broad host credentials by default, and asking the Human to approve every normal command. Human authorization remains at material scope, risk, cost and external-side-effect boundaries. Routine checks and permitted recovery are autonomous.

## H. Context, compaction and the future ECF seam

Three different sources must remain distinguishable:

1. **Governed context from outside Executor:** Product North Star, Work Intent/Reality, admitted architecture constraints and rationale, PWU contract, deferred/required capabilities, exact asset/baseline references, findings and evidence. Future ECF assembles freshness/provenance-aware projections for a decision.
2. **Executor working context:** local plan, observations, tests run and still missing, tool results, known uncertainty, approach rationale and compacted history. Executor owns recording and reconstructing this working state.
3. **Provider context:** request formatting, cache prefix, tool-use dialect, opaque response/compaction handles and reasoning features. Provider adapter owns translation; these are not Watt execution Truth.

Adopt a versioned **context package reference and integrity manifest** at the kernel boundary. Later ECF replaces the assembler behind that seam. Executor may request additional relevant context and report stale/missing/conflicting facts; it must not become a second ECF or decide that source code overrides Product Intent.

Codex persists rollout/context and reconstructs through compaction. Aider caches repository maps and summarizes older chat. LobeHub preserves the latest user message and rolls back a failed compression group. The portable lesson is immutable source material plus replaceable projections. Preserving only the last user message is insufficient for Watt: authoritative contract, constraints, acceptance obligations and scope must remain explicit and exact even if they originated earlier. [C02/C04](external-executor-source-evidence.md#c02), [A03](external-executor-source-evidence.md#a03), [B03](external-executor-source-evidence.md#b03)

### Safe compaction protocol (recommended)

Capture input frontier/version → assemble a candidate summary with provenance → validate required invariant/obligation references → store summary and source references → atomically make that context projection current. Keep the prior usable projection until replacement commits. Serialize or version concurrent Human correction so a stale summary cannot resurrect superseded intent.

Safe to compact: repetitive observations, obsolete local hypotheses, verbose command output already retained as evidence, dialogue rendering and working-plan history. Never replace with a lossy summary: admitted contract/criteria, exact source/candidate vector, authority/capabilities, unresolved tool effects, interventions and their admission versions, verification results or evidence identity.

Compaction is a separately observable, budgeted operation with a resumable input frontier. It may be recomputed with another compatible model from retained portable material; identical summary text is not promised. If it fails and the current context still fits, continuation can be policy-permitted. If it does not fit, park with an explicit reason and preserve state. Repeatedly attempting the same failing compaction without a budget is not recovery.

Codex stores the installed replacement history, retained context/window metadata and compaction response reference in a `RolloutItem::Compacted`, with related WorldState/TurnContext/settings items. Its method updates in-memory history before calling rollout persistence; this source sequence is not an atomic memory/disk checkpoint guarantee. The previous-to-current-model compaction fallback is conditional and can include overload/usage-limit errors even though those are not generally retryable sampling errors.

Codex V2 failure stops pre-sampling/mid-turn progress; newer local source preserves input and has specific fallback paths. Its remote representation and compatibility logic show why arbitrary provider substitution cannot be assumed. LobeHub's skip-on-error is useful only when enough context capacity remains; Watt must check that condition. [C04](external-executor-source-evidence.md#c04), [B03](external-executor-source-evidence.md#b03)

## I. Pause, resume, stop, retry, recovery and checkpoints

### Distinct operations

| Operation | Recommended Watt semantics | Must not imply |
|---|---|---|
| Graceful Pause | Persist request; stop scheduling new effects; drain or classify active operations; checkpoint repository/context/execution at a named frontier; acknowledge PAUSED only after a recovery-safe barrier. | A UI button or cancelled socket has stopped mutation. |
| Resume | Revalidate contract, source/workspace, grants, budget and ownership; reconcile pending effects; hydrate checkpoint; continue unfinished work. It may reacquire a worker lease. | Re-send the original mission and repeat all actions. |
| Safe internal retry | Repeat one classified transient request inside the same still-valid Attempt, using bounded delay and stable effect identity/precondition where relevant. | Every retry creates a PWU/Attempt; any 429 is safe forever. |
| New-Attempt retry | Preserve predecessor terminal facts; issue new generation/grant after governed reconciliation; attach salvaged state and explicit residual obligations. | Wipe old work, overwrite failure history, or reuse stale authority. |
| User Stop / Cancel | Revoke future action admission, propagate cancellation, collect terminal process/effect facts. Retain work/evidence; classify unresolved effects UNKNOWN. Resume later requires an eligible new grant if the old one terminated. | Automatic rollback or guaranteed termination of every remote process. |
| Hard cancel | Fence owner; request forceful process termination; inspect remaining effects and descendants; preserve uncertainty. | Successful kill request proves effect did not occur. |
| Fork | New lineage from explicit checkpoints with separate authority/workspace ownership; history may be shared read-only. | Concurrent writes to the original writable workspace. |
| Provider interruption / network loss | Keep execution truth local; classify request stage and retryability; retain tools/workspace; wait/reconnect/back off within admitted budget. | Deterministic task failure or automatic loss of all progress. |
| Tool timeout | Record deadline, cancel/kill/query outcome and mutation uncertainty. If continued in background, name its operation handle. | A short output-yield timeout is a tool execution deadline. |
| Process / machine crash | New worker obtains a fenced lease, loads durable checkpoint and reconciles filesystem/remote effects. Machine-loss recovery additionally needs accessible replicated storage or export. | Local disk persistence protects against lost disk/host. |

A pause request can remain **PAUSING** while an effect cannot be safely interrupted. A hard cancel can remain **CANCEL_REQUESTED / EFFECT_UNKNOWN** until the host proves termination or reconciliation. These are proposed execution projections, not edits to current PWU domain enums. Model output and UI projections must name the real waiting reason.

### What external state actually survives

| System | Surviving material / conditions | Missing guarantee |
|---|---|---|
| Codex | Persisted rollout/history/settings, existing working files and loaded server thread when only client disconnects; writer ownership checks on resume. | No source proof that arbitrary OS processes or the Human's exact client incident survive host death; ephemeral threads differ. |
| OpenHands Canvas | Backend conversation IDs, client metadata/history projection; reconnect and run/interrupt request paths. | Backend workspace/checkpoint persistence is outside checkout. Cloud pause versus local interrupt differ. |
| SWE-agent | Written trajectory/config/stats and submitted/last-recorded patch where available. | `write_text` trajectory is not transactional pre-effect journaling; environment reset loses prior process state. |
| Aider | Existing files/Git commits and optionally restored chat/configuration. | Exact active execution checkpoint or durable async process continuation. |
| LibreChat | Generation records, retained chunks/steps and approval state within configured store retention; live graph may be unavailable. | Durable stream recovery is not generic recovery of all tools or a live model request. |
| LobeHub | DB messages, durable operation cancellation and Redis step state within retention; host can hydrate and schedule steps. | Two-hour Redis TTL/default store configuration cannot promise indefinite pause or arbitrary effect exactly-once. |
| Open WebUI | Chat/partial response data, task IDs/control in Redis where configured. | In-process asyncio coroutine/stack is not recoverable from task IDs. |
| LangGraph | Graph channels, pending writes, interrupts and task metadata with durable saver. | Filesystem/process/remote mutations are not rolled back with graph state. Node logic can replay. |
| AutoGen | Explicitly exported agent/team state, files on bind mounts if retained. | Generic cooperative pause may be a no-op; exported agent state is not a durable message queue/process checkpoint. |
| Claude Code | Changelog describes persistence/restart fixes; hook sample reads transcript. | Core checkpoint/restart guarantees cannot be independently established here. |

Evidence: [C02–C03](external-executor-source-evidence.md#c02), [O02–O03](external-executor-source-evidence.md#o02), [S02–S04](external-executor-source-evidence.md#s02), [A02–A04](external-executor-source-evidence.md#a02), [L02–L04](external-executor-source-evidence.md#l02), [B01–B02](external-executor-source-evidence.md#b01), [U01](external-executor-source-evidence.md#u01), [G01–G03](external-executor-source-evidence.md#g01), [T02](external-executor-source-evidence.md#t02), [H02](external-executor-source-evidence.md#h02).

### Three checkpoints, one consistent frontier

| Kind | Protects / representation | Cannot restore | Cost, portability and correctness |
|---|---|---|---|
| Repository checkpoint | Git tree/commit, patch with exact base, or filesystem snapshot; per-mount vector plus untracked/generated inventory. | Tool state, external API effects, rationale, running tests, browser/DB state. | Git is efficient for source and portable with required objects; patches need exact preconditions; full filesystem/container snapshots cost more and can be platform-bound. Capture binary/link/mode/ignored-file policy explicitly. |
| Execution checkpoint | Durable log offset, Attempt/worker epoch, pending/completed effect receipts, next eligible boundary and budget. | Provider-private reasoning, unrecorded remote mutations, missing files. | Small structured writes but latency at safety barriers; external effects still require idempotency/reconciliation. Schema/version and tool versions matter. |
| Semantic/context checkpoint | Versioned contract/context refs, local plan, known findings, completed work, unresolved hypotheses, remaining verification and portable summary. | Exact model cognition or deterministic identical reasoning. | Token/recomputation cost; summary drift risk; original governed facts and evidence stay lossless and referenced. |

A checkpoint **bundle** names all three frontiers and outstanding exceptions. A Git commit alone is not a safe resume checkpoint, and a graph checkpoint without corresponding changed files is not implementation recovery. Warm process handles may be supplemental but must never be required to explain the portable checkpoint.

### UNKNOWN reconciliation algorithm (Blueprint input)

1. Fence the previous owner or prove it has stopped. If remote mutation may continue, quarantine that conflict scope until reconciliation; starting a second writer is unsafe.
2. Load the last durable execution frontier and original grant/context/source vector. Preserve historical UNKNOWN.
3. Inspect each workspace mount and authoritative ref independently; compare base, dirty files, snapshots, artifact digests, completed effect receipts and unconfirmed operations.
4. Query external providers/tools for known operation IDs when possible. A timeout after request acceptance differs from failure before submission. If no proof is available, retain per-effect UNKNOWN.
5. Classify: no effects; valid complete work awaiting verification; useful partial work with residual obligations; invalid/stale work; lost workspace; or unresolved ongoing effects.
6. Salvage attributable work without trusting it. Continue missing checks through normal independent Verification. For partial work, prepare a new working basis/overlay with provenance under the same PWU where valid; do not relabel that basis as Trusted Baseline.
7. Resume a valid retained grant/checkpoint or issue a new Attempt when continuity ended. Escalate only material decisions or irreducible unsafe ambiguity; routine observation/retry should be autonomous.

Current Watt already covers completed-work salvage and tests that UNKNOWN does not destroy valid work. General partial-work continuation, provider-neutral native checkpoints and automatic capacity recovery remain future work. [W06](external-executor-source-evidence.md#w06)

### Four explicit failure-case results

| Case | Source-backed explanation | Required Watt behavior and acceptance observation |
|---|---|---|
| A — capacity | Watt broadly maps provider exceptions to UNKNOWN. Codex retries eligible stream/rate errors but explicitly treats `ServerOverloaded`, quota/usage-limit and several policy errors as non-retryable at its error classification layer; capacity handling cannot be copied as universal automatic retry. [W03/W09](external-executor-source-evidence.md#w03), [C05](external-executor-source-evidence.md#c05) | Separate provider-unavailable from deterministic task failure and unknown effects. Before model submission/no tools: bounded retry or admitted fallback; after possible effects: reconcile. Same objective survives without creating a separate Work/recheck. |
| B — client restart | Loaded server thread/subscriptions and persisted rollout can explain continuation when UI dies; OpenHands shows remote backend separation. Neither establishes the exact Human incident topology. [C03](external-executor-source-evidence.md#c03), [O03](external-executor-source-evidence.md#o03) | UI reconnects by stable identity/cursor and does not submit a new mission. Worker death uses checkpoint recovery; host death requires retained workspace/evidence. Test these separately. |
| C — remote compaction | Codex pre-turn failure records pending input and exits; V2 builds replacement after a successful attempt. LobeHub rolls back failed compression groups. [C04](external-executor-source-evidence.md#c04), [B03](external-executor-source-evidence.md#b03) | Preserve original context and effects; explicit `waiting_for_context_capacity`/compaction failure; recompute/fallback within policy. Do not restart implementation or overwrite admitted constraints with a bad summary. |
| D — quota after implementation | SWE-agent salvages patch despite cost exit; Watt already salvages complete independently observed work despite UNKNOWN. Neither alone is universal partial-work resume. [S02](external-executor-source-evidence.md#s02), [W06](external-executor-source-evidence.md#w06) | Inspect changes and validation receipts; run only missing/stale obligations; retain useful edits with lineage; new Attempt if necessary. Historical attempt failure remains truthful even if recovered PWU later succeeds. |

## J. Human intervention and authority

Human input during execution must pass through WIC/Work governance. It can be a fact, constraint, correction, request, scope change, unrelated Motive or decision. Executor should receive a typed admitted update with `change_id`, expected contract/context version, disposition, effective boundary and receipt. These names describe requirements, not a proposed public API schema.

LibreChat provides a useful queue/drain/receipt pattern: mid-run messages apply after a tool batch and replay after publication gaps. Codex drains pending input between sampling cycles. **ADAPT** these mechanics, but replace direct chat injection with governed changes. [L03](external-executor-source-evidence.md#l03), [C01](external-executor-source-evidence.md#c01)

For non-material factual context updates, admit a context revision and apply it at the next safe boundary. If a correction invalidates current approach or acceptance assumptions, pause new effects immediately, settle in-flight effects, then let governance revise scope/contract and decide Attempt/PWU continuity. Record whether previously produced edits and tests are still valid. A queued correction must never be silently lost because execution finished between enqueue and delivery; return applied/deferred/rejected/superseded with attributable reason.

Stop requests can be immediate control signals while their semantic explanation is handled separately; do not keep executing unsafe effects merely because WIC interpretation is slow. Resume must not widen authority based on a casual message. Material destructive operations require meaningful outcome/risk visibility before authorization.

Human remains Governor of goal, direction, risk, major product/architecture choices and acceptance. The Human should not route transient errors, retry shell calls, relay test failures or administer Git worktrees. External per-file/shell confirmation policies are useful enforcement examples but unsuitable default product interaction for Watt.

## K. Execution evidence, Verification, Guardian and preview

Executor evidence must include:

- Work/PWU/contract/Attempt/session/step identities and exact context basis;
- model/provider/binding/request metadata and usage availability;
- tool schema/version, input digest, cwd/mount, capability receipt, timings, exit/timeout/cancel/unknown classification and full evidence reference;
- before/after source and artifact identity, patches/change manifests, generated-file inventory and dependency/environment fingerprint;
- commands/tests/build outputs, what they actually checked, failures and unresolved obligations;
- checkpoint links, interventions, recovery/retry decisions and preserved historical failures;
- an immutable **result-ready claim** and artifact/evidence manifest, with no self-issued trust status.

Tool-call and trajectory records in Codex/SWE-agent/LobeHub provide mechanisms. Watt adds governed provenance and independent subject binding. Logs are not necessarily complete: tool output truncation, redaction and unavailable provider usage must be explicit. Hashes bind content; they do not certify its quality. [C06–C07](external-executor-source-evidence.md#c06), [S04](external-executor-source-evidence.md#s04), [B01](external-executor-source-evidence.md#b01)

Verification/Guardian consumes immutable artifact vectors and evidence through a read-only interface with independently provisioned validation capabilities. It can rerun checks, assess boundary violations, request missing evidence and issue findings. It must not share Executor's authority to declare success or automatically inherit unrestricted execution credentials. Guardian can eventually qualify the **task before execution**: objective/criteria consistency, relevance to Work intent, feasibility of scope and adequacy of evidence obligations. This reduces “correct execution of the wrong task” without transferring WHAT NEXT from Steering.

Codex's source includes a component named Guardian used in approval/review flows. That name is not Watt's independent Engineering Assurance System and is not evidence that their ownership models match. External self-review or another agent in a team remains Executor-side feedback unless independently bound and governed.

Preview is an Executor/runtime output capability, not a trust shortcut. Future flow: sealed Candidate/artifact vector → isolated preview adapter (where supported) → Human visibility → exact authorization → trusted integration → final Product Acceptance. Pin preview to candidate digests, label its lifecycle/access state, and prevent privileged side effects. Current Watt Delivery is post-trusted-commit; it must not be described as already providing the entire proposed pre-authorization preview path. [W05/W07](external-executor-source-evidence.md#w05)

Web, API/backend, CLI, library, mobile, mini program and automation require different preview/run adapters. Executor outputs a governed artifact manifest; it does not hardcode static-Web serving, deployment ports or a single runtime form. An artifact can be inspectable through logs, package contents, test reports or a simulator even when interactive preview is unavailable.

## L. Model/provider abstraction and resource governance

The native kernel should call an inference adapter with a **capability profile**, not assume every model supports the same tool syntax, structured output, reasoning setting, modalities or continuation protocol. The adapter converts portable messages/tool contracts to provider wire format and normalizes streaming results/errors/usage. Kernel owns the prompt/context policy and action lifecycle. Model/provider identity and effective configuration must be recorded; `sdk-default` is unresolved selection, not an exact model claim.

A portable checkpoint can support model replacement at a safe boundary when contract/context/artifacts/tool receipts survive. It cannot export hidden provider cognition. Provider-specific encrypted compaction items, thought signatures, response chaining and cache formats may be incompatible. On replacement, use a fresh provider session from the portable checkpoint and re-read current workspace Reality; do not blindly copy opaque provider objects into another model API. Aider/AutoGen demonstrate separable model clients; Codex compatibility-specific compaction shows the limit. [A04](external-executor-source-evidence.md#a04), [T01](external-executor-source-evidence.md#t01), [C04](external-executor-source-evidence.md#c04)

### Failure/resource policy requirements

| Classification | Recommended action |
|---|---|
| Transient connection/service capacity, known no-effect request | Capped jittered backoff, honor retry advice, preserve wait reason; fallback only to pre-admitted compatible bindings. |
| Provider quota or exhausted admitted budget | Checkpoint/park or end grant truthfully; preserve work; notify once if policy/action required. No silent switch to paid or more expensive usage. |
| Authentication / permission / invalid model/request | Stop affected resource path; route configuration/capability resolution. Repeating unchanged request is not engineering recovery. |
| Context overflow/compaction failure | Use explicit context recovery procedure, not mission replay. |
| Deterministic test/implementation failure | Feed observation into autonomous local repair within scope and budget; independent final Verification remains separate. |
| Timeout/disconnect after effect may have started | Reconcile effect/workspace before retry; retain UNKNOWN if unresolvable. |

Record input/output/cached/reasoning tokens **only when reported**, request/compaction/retry counts, provider/model identity, elapsed model/tool/workspace time, resource class and cost estimate with rate/version/currency basis. Mark unknown usage and uncertain spend; never use missing measurements as zero. SWE-agent's checks and LobeHub counters are useful, but after-the-fact cost checks permit overshoot. Future governance needs an admitted reservation/upper-bound policy before expensive work where feasible. [S04](external-executor-source-evidence.md#s04), [B04](external-executor-source-evidence.md#b04)

Differentiate configured ceilings, measured consumption, estimated remaining work and scheduler decisions. Executor enforces the granted envelope; future capacity/scheduling owns when resources are allocated. Ordinary bounded retries can be automatic. Crossing provider/data residency, cost ceiling, risk class or expensive reasoning policy requires pre-admitted authority or a material Human decision. This is not a billing architecture.

## M. Performance and execution visibility

### Instrument the lifecycle from day one

| Latency class | Required spans / observations | Supported optimization hypotheses |
|---|---|---|
| Model/provider | Request queued/sent/accepted, first token, first actionable output, stream completion, retries/backoff, compaction, model configuration/usage. | Connection/session reuse, compatible prompt prefix caching, bounded context, fit-for-purpose model/effort. |
| Runtime/orchestration | Admission/dispatch wait, durable write barriers, worker claim, scheduling, checkpoint/rehydration, event publication, lock contention. | Persistent workers, avoid serial independent work, separate live stream delivery from execution ownership, smaller recoverable state. |
| Tool/workspace | Checkout, dependency prep, repo scan/context assembly, tool start, first output, actual process completion, snapshot creation. | Warm environments, shared read-only caches, incremental repo indexing, process reuse and conflict-safe parallel reads/tests. |
| Infrastructure | Docker/container/VM cold start, filesystem/mount IO, DB connection/query/lock latency, network/proxy time, CPU/memory pressure. | Pool connections, improve filesystem locality, reuse runtime resources under isolation/retention policy. |
| Perceived | Durable request acknowledgment, event arrival, first meaningful action, progress freshness, waiting reason, UI render and reconnect gap. | Early truthful phase events, stable ordered streams, batched rendering/deltas and resumable subscriptions. |

Codex emits TurnStarted before prewarm resolution and tracks TTFT/first meaningful item plus sampling/tool/compaction phases. Aider caches parsed tags/context and runs summary work in a thread, although joining can block later. LibreChat bounds/coalesces publication buffers and supports replay. LobeHub omits reconstructible DB messages from Redis state. These are source-backed mechanisms, **not measured speedup promises for Watt**. [C09](external-executor-source-evidence.md#c09), [A03](external-executor-source-evidence.md#a03), [L02](external-executor-source-evidence.md#l02), [B02](external-executor-source-evidence.md#b02)

Instrument monotonic durations per process and wall-clock correlation timestamps with IDs across boundaries; do not subtract unsynchronized clocks as precise durations. Report cold/warm and cache hit/miss, output truncation and unknown timings. Separate Human wait from machine latency. Avoid counting overlapping spans twice. Extend DCP-2 evidence semantics rather than replacing its unavailable fields with estimates.

### Required execution events, not a UX design

A durable lifecycle/event spine should support: admitted/queued; workspace preparing/ready; running/observing/planning/implementing/validating; tool started/progress/finished/unknown; model waiting/backoff; compaction started/failed/completed; intervention received/admitted/applied; pause requested/paused; resume/reconciliation; stop requested/stopped; result ready; resource/budget blocked. Every event names producer, subject, sequence, timestamp and applicable basis/epoch.

High-volume progress may be transient/coalesced if a reconnect snapshot preserves the current state and durable milestones. Command/test/artifact evidence referenced by milestones remains durable. A subscriber reconnects with a cursor, gets missing retained events or an explicit snapshot/reset response when retention expired, and deduplicates by event ID. Subscriber loss or backpressure must not silently cancel production or cause unbounded memory growth. Do not expose private reasoning as a substitute for operational visibility.

“Next likely action” can be an explicitly tentative local-plan projection. A waiting reason must distinguish provider, tool, capacity, Human decision, capability, checkpoint and infrastructure delay. No invented percentage/ETA. Future Control Room consumes these facts after lifecycle semantics stabilize.

## N. Production Passport, replay and continuity benchmark

Passport should join existing authoritative records by exact identity: Work/Intent revision → Steering/PWU/contract → context package → Attempt/session/binding/steps → workspace and checkpoint vectors → evidence → Verification → Candidate/authorization/integration/Runtime Commit → Delivery/acceptance. It records **why trust was granted**, not merely “the agent said done”. The Passport is a manifest over owners, not a new owner of those facts. [W09](external-executor-source-evidence.md#w09)

SWE-agent trajectories are strong explanatory/replay inputs; Codex rollouts reconstruct model context; LangGraph checkpoints replay graph work. None alone reproduces toolchains, external resources, Human authority and verification truth. [S04](external-executor-source-evidence.md#s04), [C02](external-executor-source-evidence.md#c02), [G01](external-executor-source-evidence.md#g01)

Distinguish three replay modes:

- **Audit replay:** read historical facts and render what occurred; never rerun effects.
- **Controlled engineering replay:** re-execute selected steps against isolated exact inputs with external effects disabled or simulated; compare output/evidence.
- **Production continuation:** execute only unfinished work under a current valid grant and reconciled Reality.

Record environment/image/tool versions, dependency locks, provider profile, context/source/evidence digests, seeds where relevant, availability gaps and a secret-free capability manifest. Do not promise bit-for-bit multi-model reproduction. Retention, redaction and export policy must keep the minimum proof needed without embedding reusable credentials.

### Required future benchmark (specification only)

Use equivalent admitted objectives and baselines for **A: one long execution** and **B: segmented PWU execution**, with repeated trials and independently evaluated outputs. Keep the same PWU objective across segmentation; do not manufacture tiny tasks just to make restart easy.

| Injection | Required B behavior / measurement |
|---|---|
| Graceful pause after planning, after edits and during validation | Restore intent/local plan; no lost constraints; continue remaining work; measure recovery overhead and repeated work. |
| Kill UI while worker runs | Reattach without mission resend or duplicate dispatch. |
| Kill worker before tool start, during tool, after effect before receipt, after receipt before checkpoint | Distinguish known-no-effect from unknown-effect; fence old worker; reconcile; no blind mutation replay. |
| Provider capacity before inference / quota after edits | Preserve objective and useful artifacts; autonomous bounded handling; no new unrelated Work. |
| Compaction failure and model replacement | Preserve exact criteria, open findings and source vector; portable context hydration; record quality/cost change. |
| Two repositories with coordinated API change | Verify coherent output vector; recover partial mutation/integration without falsely claiming atomic success. |
| Human correction during a long tool or compaction | Admit/apply by version; reject stale summary/update; expose receipt; re-evaluate affected work. |
| Late result from fenced owner; duplicate event/tool delivery; expired grant/checkpoint | Reject stale publication/effect admission; show truthful recovery gap; no second writer. |

Compare independent contract satisfaction and engineering quality, requirement drift, lost useful work, duplicated mutations, missing/stale verification, Human technical interventions, wall time by latency class and provider/tool cost. Require zero unauthorized effects and zero falsely trusted outcomes. Set quantitative quality/overhead tolerances before implementation qualification; this study does not invent empirical thresholds or claim the benchmark passed.

## O. Adopt / Adapt / Reject decisions

The [pattern matrix](external-executor-pattern-matrix.md) gives external mechanism → purpose → evidence → limitation → Watt fit → disposition → Blueprint consequence, organized by engineering problem. The governing decisions are:

- **ADOPT as principles:** independent lifecycle/effect identity, exact source/evidence references, preserving useful work after failure, bounded output, observable phase timing and explicit error classes.
- **ADAPT:** rollout/session reconstruction, pending-write checkpoints, worktrees, generation fences, Human input receipts, cached context, safe model fallback and runtime reuse.
- **REJECT as Watt defaults:** session=Work; chat=Truth; one repository=PWU; graph node/model turn=production unit; automatic reset/replay on UNKNOWN; automatic trusted commits; provider state as the sole checkpoint; self-review as Guardian; unlimited retry; universal per-command Human approval; chat-cache TTL as long-term recovery; static-Web-specific kernel.

## P. Explicit answers to all 40 Blueprint questions

These are evidence-backed recommendations for the next phase. “Recommended” does not mean this mission has admitted a new architecture contract.

| # | Blueprint question | Answer / evidence |
|---|---|---|
| 1 | Native kernel boundary? | Own admitted execution binding, local model/tool loop, workspace/effect access, durable steps/checkpoints, recovery, evidence, cancellation, resource enforcement and events. Keep context/capability/provider implementations behind seams. D–I; C01/C06/G01/B01. |
| 2 | Outside kernel? | Work/Intent/WIC; Steering WHAT NEXT; PWU contract/lifecycle and SPG grants/trust; independent Verification/Guardian; Human authorization/acceptance; integration and delivery adapters. B/K; W01–W09. |
| 3 | PWU versus Session? | PWU is governed contract plus production lifecycle. Session is reconstructible runtime continuity, 0..N per PWU, reusable across successor Attempts with exact active grant. E; C02/B01. |
| 4 | Multiple Attempts? | Yes; keep immutable history and predecessor/recovery links without replacing Work/PWU for every failure. E/I; W06/S02. |
| 5 | New Attempt trigger? | Grant continuity ended, fenced/lost workspace, changed source/material contract, recovery re-execution or materially changed executor/provider binding. Worker lease change alone need not be an Attempt if safe continuity is proven. E. |
| 6 | Durable state? | Contract/context/source/capabilities/epoch, effect intent/receipts, working checkpoint, model/action references, evidence, budget/usage and admitted interventions. E/I; C02/G01/L01. |
| 7 | Ephemeral state? | Transport handles, token-delta rendering, recomputable indexes, prewarm/parser/cache state; retain any unique information needed for recovery first. E/M; B02/C07. |
| 8 | Pause? | Stop new effects, settle/classify in-flight work, persist a consistent checkpoint and acknowledge only at a recovery-safe barrier. I; G02/T02. |
| 9 | Resume? | Revalidate grant/scope/basis/workspace/budget; reconcile pending effects; hydrate portable checkpoint; continue residual work. I. |
| 10 | Retry? | Separate bounded request retry inside valid grant from new-Attempt re-execution after reconciliation. I/L; C05/S02/B04. |
| 11 | Stop/Cancel? | End future effect authority; propagate interrupt/kill; preserve output and unresolved effects; no implied rollback. I; U01/T03. |
| 12 | Client/process death? | UI reconnect if worker lives; worker reconstructs from durable state if host/storage survive; machine-loss recovery requires external retained state. I; C03/O03/G01. |
| 13 | UNKNOWN? | Fence → observe workspace/refs/effect receipts → salvage/reverify → continue or new grant; keep historical UNKNOWN and per-effect uncertainty. I; W06/S02/L01. |
| 14 | Checkpoint definition? | Named consistent recovery frontier with repository, execution and semantic references, not merely saved conversation. I. |
| 15 | Separate checkpoints? | Tree/snapshot protects artifacts; journal protects execution position/effects; context protects intent/knowledge. Bundle them explicitly. I; C02/G01/S04. |
| 16 | Workspace? | Stable resource container with plural mounts, generated output, context/evidence/checkpoint stores and runtime/test services. F; C08/T03. |
| 17 | Multiple repositories? | Exact source/output vectors, per-mount scope and coherent verification; explicit partial integration/recovery without distributed atomicity claims. F; W02/W05. |
| 18 | RO/RW scope? | Enforce per asset/mount/path/action at tool host; reads do not imply writes and writes do not imply push/PR/deploy. G; C06/T03. |
| 19 | Local-plan autonomy? | High autonomy for inspection/edit/debug/test/refinement within admitted contract; material direction/scope/criteria changes return to governance. D; W03/S01/A01. |
| 20 | Tool provisioning? | Derive required tool contracts from admitted production needs; registry exposes only executable authorized capabilities; host validates at invocation. G; C06. |
| 21 | Least-privilege grants? | Temporary scoped handles, broker injection, expiration/revocation and revalidation on resume; automated ordinary provisioning. G; external coverage partial, Watt seam required. |
| 22 | Native evidence? | Exact actions/effects, changed artifacts, test/build results, errors/timing/model/resource/checkpoint/contract lineage, plus unavailable/truncated markers. K; S04/C07/B01. |
| 23 | Guardian consumption? | Read-only immutable manifest/evidence interface and separately provisioned independent assessment; not an Executor subroutine. K; W05/W09. |
| 24 | Running-PWU steering? | WIC interprets, Work/SPG admits, versioned change delivered at safe boundary with durable receipt. J; L03/C01. |
| 25 | Active correction safety? | Pause effects if needed, settle in-flight work, reject stale updates, version contract/context, invalidate affected evidence and preserve provenance. J/H. |
| 26 | Provider abstraction? | Capability-negotiated inference adapters; Watt owns context/action truth, adapters own wire protocols; capture effective binding. L; A04/T01/C04. |
| 27 | Survive model replacement? | Yes at a reconciled boundary using portable context/workspace, with same PWU; default new Attempt/binding lineage. No hidden-cognition portability promise. E/L/N. |
| 28 | Context persistence/compaction? | Retain governed facts and evidence; compact replaceable projections with input frontier, validated replacement and rollback; explicit context-capacity recovery. H; C04/B03/A03. |
| 29 | ECF seam? | External versioned context package with provenance/freshness/invariants and additional-context requests. Executor persists working knowledge, does not become ECF. H; W09. |
| 30 | UX/Control Room state? | Lifecycle, meaningful action, tests, waiting reason, progress freshness, interventions, budget and recovery events with ordered reconnect semantics. M; L02/O03/C09. |
| 31 | Passport/replay? | Connect exact authoritative lineage; versioned artifacts/environment/tool/context; separate audit replay, isolated engineering replay and continuation. N; S04/C02/G01. |
| 32 | Day-one instrumentation? | Cross-boundary correlation, monotonic phase timing, first action/output, cold/warm initialization, provider/tool/persistence/retry/compaction/verification intervals and unavailable fields. M; W08/C09. |
| 33 | Latency mechanisms? | Warm isolated workers, connections/processes, incremental indexes/context, conflict-safe concurrency, smaller state, event streaming/batching; validate bottleneck before optimization. M; A03/B02/L02/C07. |
| 34 | Capacity/quota handling? | Classify by phase/effect certainty; bounded backoff/admitted fallback; park with preserved work for quota; never switch spend/provider authority silently. I/L; W09/C05/S04. |
| 35 | Resource/cost telemetry? | Attributable tokens/cache/reasoning where available, request/retry/compaction counts, timing/resource class, estimated/actual cost basis, reservation/ceiling and unknowns. L; W08/S04/B04. |
| 36 | What not to copy from Codex? | Session authority, proprietary-only context, approval/reviewer ownership as Guardian, CLI assumptions, any unbounded-retry default, model completion as production trust. O; C01–C06. |
| 37 | OpenHands/SWE-agent/Aider improvements? | OpenHands backend/client/workspace-mode separation and reconnect; SWE salvage/trajectory/deployment seam; Aider dirty-work protection, structured feedback and incremental repo map. F/I/M; O01–O03/S01–S04/A01–A03. |
| 38 | Conflicting external approaches? | Aider single-repo/auto-commit; SWE reset retry; LangGraph arbitrary-node replay; AutoGen no-op pause; chat-native steering; TTL-only checkpoint; extension promise-as-done. Matrix gives precise adaptations/rejections. |
| 39 | Human decisions still needed? | Recovery/retention guarantee, permitted fallback/cost/privacy envelope, cross-repo integration risk policy, benchmark acceptance tolerance. Q; decisions are explicit defaults/requirements for Blueprint, not hidden blockers. |
| 40 | Enough evidence for Blueprint? | Yes. Main mechanisms and failure limits are established; no missing external feature is essential to design the boundaries. Implementation/qualification remains unperformed. T. |

## Q. Open architecture decisions

The Blueprint should resolve these explicitly. Human decisions concern product/risk policy; technical choices can be proposed concretely without requiring the Human to operate recovery.

| Decision | Recommended starting position | Owner / when |
|---|---|---|
| Recovery service promise | Guarantee UI disconnect and worker restart with retained host storage first; do not claim machine/disk-loss recovery until durable remote storage and workspace export exist. Define paused-work retention separately from cache TTL. | Human confirms promised availability/retention; Blueprint chooses storage topology. |
| Fallback/resource authority | Pre-admit compatible provider/model classes, data boundaries and maximum spend; default no unexpected paid usage or privacy-boundary change. | Human Governor sets risk/cost policy; Executor enforces it. |
| Cross-repository integration policy | Govern coherent vector; support honest partial convergence and forward recovery. Compensation only where specifically authorized. | Human risk tolerance plus SPG Blueprint; not an Executor unilateral policy. |
| Continuity benchmark tolerance | Zero unauthorized effects/false trust; independently judge retained intent and quality. Set acceptable recovery overhead and stochastic quality tolerance before qualification. | Human product/engineering acceptance criteria, informed by benchmark design. |
| Session/Attempt model switching detail | Default new Attempt for materially changed binding; allow same-Attempt compatible episodes only by explicit contract policy. | Architecture decision during Blueprint; no research blocker. |
| Durability technology and checkpoint frequency | Reuse existing Watt persistence patterns; durable barriers before unsafe effects, bounded asynchronous progress afterward; choose log/DB/object-store implementation by recovery and latency requirements. | Architecture/implementation decision; no need to choose a framework in this study. |

No Human response is required to complete this research mission. These are inputs for the next Blueprint phase, not permission questions to start implementation now.

## R. Architecture risks

| Risk | Required design response |
|---|---|
| Provider-specific summary becomes sole memory | Retain portable context/evidence and binding versions; replacement benchmark. |
| Acknowledged pause still permits effects | Safe barrier, owned process/effect receipts and explicit PAUSING/UNKNOWN. |
| Lease expiration creates two writers | Fencing at execution and publication boundaries; quarantine unkillable old effects. DB fence alone cannot stop an already executing remote shell. |
| Replaying a node duplicates mutation | Separate effect journal; preconditions/idempotency/query-before-replay. |
| Partial changes lost on retry/reset/cleanup | Snapshot/inventory before teardown, provenance-preserving salvage and retention pins. |
| Multi-repository partial integration misreported as atomic | Exact vectors and per-target convergence, aggregate trust barrier. |
| Chat correction silently changes contract | WIC admission/version checks and durable application receipts. |
| Self-test treated as assurance | Independent exact-subject Verification/Guardian; separate Human acceptance. |
| Warm runtime leaks state/secrets between grants | Scope-aware reuse, reset/attestation and credential expiration; warm does not mean shared unrestricted filesystem. |
| Short TTL expires active/paused execution | Product retention contract; renew/pin durable checkpoint state; explicit expiry behavior. |
| Too much durability destroys responsiveness | Small pre-effect facts and boundary checkpoints; coalesce cosmetic progress, retain evidence by reference. Measure actual overhead. |
| Cost checks happen only after spend | Admission ceilings/reservations where possible, expose measurement gaps/overshoot; no unbounded retry. |
| Over-decomposition destroys engineering continuity | Benchmark meaningful PWUs with local plans and residual obligations; Steering evaluates scope, not repo count. |
| Similar vocabulary imports incompatible authority | Treat external task/session/attempt/Work/Guardian names as local definitions only. |

## S. License and code reuse constraints

This mission copied no external implementation into Watt. The [license inventory](external-executor-source-evidence.md#license-inventory-file-statements-not-a-reuse-clearance) records license-file statements at the studied SHAs, not a legal clearance or a claim about all dependencies.

Codex and Aider declare Apache-2.0; Codex also has NOTICE/third-party attribution. OpenHands, SWE-agent, LibreChat and LangGraph declare MIT in their inspected root files. AutoGen explicitly distinguishes MIT code from CC-BY-4.0 documentation. Claude Code's root license reserves rights and refers to commercial terms. Open WebUI has a custom license with branding conditions plus historical per-origin licensing. LobeHub's community license adds commercial-derivative conditions to an Apache-based form.

For a future reuse proposal, identify the exact file/version, applicable subdirectory and dependency licenses, notices, modification/distribution obligations, and any separate model/API/service terms before admitting that reuse. A permissive root file is not evidence that every bundled asset or remote SDK shares the same terms. Conceptual adoption here means an original Watt design informed by the mechanism; it does not authorize vendoring code, prompts, tests or assets. No legal interpretation beyond the inspected license text is needed to begin the Blueprint.

## T. Blueprint readiness gate

**READY_FOR_WATT_EXECUTOR_BLUEPRINT**

| Gate | Result |
|---|---|
| Watt current Reality and future intent inspected separately | Met; B and W01–W09. |
| All ten local repositories inventoried at exact revision | Met; C and source register; clean reference checkouts. |
| High-value actual execution, persistence/tool/context/failure paths traced | Met; Codex, SWE-agent, Aider, LangGraph, promoted LibreChat/LobeHub; secondary boundaries explicit. |
| Source/tests support conclusions; inference is identifiable | Met at research level; source register and explicit caller-only/test-not-run qualifications. |
| Major concerns and 40 Blueprint questions accounted for | Met; D–P plus coverage matrix. |
| Adopt / Adapt / Reject with Watt implications | Met; companion problem-oriented matrix. |
| Four real failure cases translated to acceptance scenarios | Met; I and N; incident forensics limits explicit. |
| Work/PWU/Human/Guardian/ECF/multi-repo invariants preserved | Met; no Project, one-repo freeze or transferred trust authority. |
| Unknowns are explicit without manufacturing blockers | Met; Q/R. Exact commercial/absent core internals remain outside proven behavior, but do not prevent native architecture design. |

The next phase may design the Watt Executor Blueprint from these inputs. Native Executor, lifecycle changes, ECF, Guardian, UX, Git hosting, OAuth and runtime/deployment implementation remain outside this completed research mission.
