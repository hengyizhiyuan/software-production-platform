# External Executor Study — Source Evidence Register

Study basis: 2026-09-10 local snapshots; completed 2026-09-11 (Asia/Shanghai). Research only; no external code imported.

## Evidence method

**S** = implementation inspected; **T** = relevant test body inspected or located as an explicit regression specification; **D** = repository documentation claim; **I** = research inference; **R** = proposed Watt architecture input. Tests are cited as specifications, not as tests run by this mission. Each entry states its confidence boundary. Repository absence means “not established in this snapshot”, not a claim about every released product.

All ten references were clean at inventory. No checkout was changed, installed, launched, or fetched. Commit permalinks below are constructed from local Git metadata, not claims of web verification. Local path anchors were mechanically checked.

## Exact revisions

| Repository | Local path | Exact HEAD | Scope |
|---|---|---|---|
| codex | `/Users/yu/Documents/dev/reference-lab/codex` | `94697375cb9d2aa8ae74d61957c6b396819bec94` | Primary loop, tools, persistence, compaction, worktree, connection handling |
| OpenHands | `/Users/yu/Documents/dev/reference-lab/OpenHands` | `725f5584b9411b1e47f1d0c5ebaf640676609940` | Agent Canvas client/backend orchestration; SDK outside checkout |
| SWE-agent | `/Users/yu/Documents/dev/reference-lab/SWE-agent` | `3ea751c087f32b16e039a2233dd6eefecef325d5` | Primary coding loop, environment seam, salvage, replay |
| aider | `/Users/yu/Documents/dev/reference-lab/aider` | `5dc9490bb35f9729ef2c95d00a19ccd30c26339c` | Primary editing loop, Git, context, provider seam |
| LibreChat | `/Users/yu/Documents/dev/reference-lab/LibreChat` | `b356c3d87edccd0bde68dc90a5eca66ae2c80e5d` | Promoted: durable generation, fences, steering/reconnect |
| claude-code | `/Users/yu/Documents/dev/reference-lab/claude-code` | `e62465d553ecbf1697219ffbb3c11b4fef14d5bf` | Public examples/plugins/changelog only |
| open-webui | `/Users/yu/Documents/dev/reference-lab/open-webui` | `0a7c15832fb30b1903753e83f81dc7d27e5b0944` | Targeted chat/tool lifecycle and cancellation |
| lobehub | `/Users/yu/Documents/dev/reference-lab/lobehub` | `08cbe3236bca1ec4ca48d77058636e1f7e69e06a` | Promoted: step runtime, persistence, compression, retry |
| langgraph | `/Users/yu/Documents/dev/reference-lab/langgraph` | `e539ac122f4126f6dd850581c1494948cf620e31` | Primary durability/checkpoint/orchestration reference |
| autogen | `/Users/yu/Documents/dev/reference-lab/autogen` | `027ecf0a379bcc1d09956d46d12d44a3ad9cee14` | Targeted team/assistant state and tool executor |
| Watt | `/Users/yu/Documents/dev/software-production-platform` | `a0394daaa59351f7e92a3f4f2482e675e751a64e` | Current implementation plus historical product intent |

## Source anchors

<a id="w01"></a>
### W01 — Interaction and intent admission

WIC persists interaction processing separately from assessment admission. Admission recomputes the exact basis and rejects stale interpretation; dialogue is not automatically Work authority.

- [S: src/spg/application/interaction.py:652](/Users/yu/Documents/dev/software-production-platform/src/spg/application/interaction.py:652)
- [S: src/spg/application/interaction.py:819](/Users/yu/Documents/dev/software-production-platform/src/spg/application/interaction.py:819)
- [S: src/spg/domain/design_intent.py:10](/Users/yu/Documents/dev/software-production-platform/src/spg/domain/design_intent.py:10)
- [T: tests/test_design_intent_framing_contracts.py:27](/Users/yu/Documents/dev/software-production-platform/tests/test_design_intent_framing_contracts.py:27)

<a id="w02"></a>
### W02 — Work, design, assets and Steering

Guided Design has its own revisions; Steering admits decisions against current Reality. Managed Git allocation is deferred until production readiness. Current multi-repository addressing does not implement a multi-write-repository PWU.

- [S: src/spg/application/guided_design.py:362](/Users/yu/Documents/dev/software-production-platform/src/spg/application/guided_design.py:362)
- [S: src/spg/application/steering.py:129](/Users/yu/Documents/dev/software-production-platform/src/spg/application/steering.py:129)
- [S: src/spg/application/assets.py:171](/Users/yu/Documents/dev/software-production-platform/src/spg/application/assets.py:171)
- [D: docs/architecture/work-to-delivery-multi-repository-spg-proposal.md:29](/Users/yu/Documents/dev/software-production-platform/docs/architecture/work-to-delivery-multi-repository-spg-proposal.md:29)
- [T: tests/integration/test_software_delivery.py:140](/Users/yu/Documents/dev/software-production-platform/tests/integration/test_software_delivery.py:140)

<a id="w03"></a>
### W03 — Current Codex adapter

One synchronous outer dispatch creates an ephemeral SDK thread, runs bounded internal turns and returns one untrusted aggregate report. Exceptions become UNKNOWN; exact internal-turn restart is absent.

- [S: src/spg/providers/codex_sdk_executor.py:113](/Users/yu/Documents/dev/software-production-platform/src/spg/providers/codex_sdk_executor.py:113)
- [S: src/spg/providers/codex_sdk_executor.py:350](/Users/yu/Documents/dev/software-production-platform/src/spg/providers/codex_sdk_executor.py:350)
- [S: src/spg/infrastructure/executor_boundary.py:31](/Users/yu/Documents/dev/software-production-platform/src/spg/infrastructure/executor_boundary.py:31)
- [T: tests/test_mvp_spg_granularity.py:165](/Users/yu/Documents/dev/software-production-platform/tests/test_mvp_spg_granularity.py:165)

<a id="w04"></a>
### W04 — Workspace and independent observation

Detached Attempt worktree binds one exact source revision. Clean preparation validation differs from basis validation that allows produced changes. Observation is independently persisted and cannot silently change after its authoritative observation.

- [S: src/spg/infrastructure/git_workspace.py:93](/Users/yu/Documents/dev/software-production-platform/src/spg/infrastructure/git_workspace.py:93)
- [S: src/spg/application/execution.py:47](/Users/yu/Documents/dev/software-production-platform/src/spg/application/execution.py:47)
- [S: src/spg/application/execution.py:89](/Users/yu/Documents/dev/software-production-platform/src/spg/application/execution.py:89)

<a id="w05"></a>
### W05 — Assurance and trusted integration

Verification binds exact proposed snapshot and obligations. Candidate sealing, Human authorization and Runtime Commit are separate owners. Provider success is insufficient.

- [S: src/spg/application/verification.py:156](/Users/yu/Documents/dev/software-production-platform/src/spg/application/verification.py:156)
- [S: src/spg/application/governance.py:77](/Users/yu/Documents/dev/software-production-platform/src/spg/application/governance.py:77)
- [S: src/spg/application/governance.py:154](/Users/yu/Documents/dev/software-production-platform/src/spg/application/governance.py:154)
- [S: src/spg/application/runtime_commit.py:69](/Users/yu/Documents/dev/software-production-platform/src/spg/application/runtime_commit.py:69)
- [S: src/spg/infrastructure/git_integration.py:9](/Users/yu/Documents/dev/software-production-platform/src/spg/infrastructure/git_integration.py:9)

<a id="w06"></a>
### W06 — Salvage and retry lineage

Recovery already independently observes surviving work. Tests distinguish SUCCESS without work from UNKNOWN with valid work; new retries get new generations, and provider resume remains unimplemented.

- [S: src/spg/application/attempt_recovery.py:66](/Users/yu/Documents/dev/software-production-platform/src/spg/application/attempt_recovery.py:66)
- [S: src/spg/application/attempt_recovery.py:152](/Users/yu/Documents/dev/software-production-platform/src/spg/application/attempt_recovery.py:152)
- [T: tests/integration/test_s5c_attempt_recovery.py:194](/Users/yu/Documents/dev/software-production-platform/tests/integration/test_s5c_attempt_recovery.py:194)
- [T: tests/integration/test_s5c_attempt_recovery.py:419](/Users/yu/Documents/dev/software-production-platform/tests/integration/test_s5c_attempt_recovery.py:419)

<a id="w07"></a>
### W07 — Delivery and acceptance

Delivery requires passing Verification and a trusted Runtime Commit. Human acceptance identifies the exact manifest. Existing software runtime support is a local static-Web slice, not a general deployment runtime.

- [S: src/spg/application/delivery.py:128](/Users/yu/Documents/dev/software-production-platform/src/spg/application/delivery.py:128)
- [S: src/spg/application/delivery.py:287](/Users/yu/Documents/dev/software-production-platform/src/spg/application/delivery.py:287)
- [D: docs/validation/software-artifact-delivery-slice.md:7](/Users/yu/Documents/dev/software-production-platform/docs/validation/software-artifact-delivery-slice.md:7)
- [T: tests/integration/test_software_delivery.py:96](/Users/yu/Documents/dev/software-production-platform/tests/integration/test_software_delivery.py:96)

<a id="w08"></a>
### W08 — Latency and process lifetime

Orchestration progress is process-local. DCP-2 derives only available intervals; missing measurements remain unavailable. Collaboration trials do not prove model latency is the only bottleneck.

- [S: src/spg/application/orchestration.py:227](/Users/yu/Documents/dev/software-production-platform/src/spg/application/orchestration.py:227)
- [D: docs/architecture/production-measurement-v0.md:49](/Users/yu/Documents/dev/software-production-platform/docs/architecture/production-measurement-v0.md:49)
- [D: docs/evidence/human-collaboration-pipeline-v31.md:36](/Users/yu/Documents/dev/software-production-platform/docs/evidence/human-collaboration-pipeline-v31.md:36)
- [D: docs/evidence/human-collaboration-experience-v32.md:5](/Users/yu/Documents/dev/software-production-platform/docs/evidence/human-collaboration-experience-v32.md:5)

<a id="w09"></a>
### W09 — Failure A and product directions

Capacity failure and a separately admitted recheck are recorded evidence. ECF, independent Guardian and Passport are future directions; PWU continuity is explicit product intent.

- [D: docs/validation/software-artifact-delivery-slice.md:36](/Users/yu/Documents/dev/software-production-platform/docs/validation/software-artifact-delivery-slice.md:36)
- [D: docs/architecture/work-centric-production-and-responsibility-principles.md:160](/Users/yu/Documents/dev/software-production-platform/docs/architecture/work-centric-production-and-responsibility-principles.md:160)
- [D: docs/context/ecf-integration.md:30](/Users/yu/Documents/dev/software-production-platform/docs/context/ecf-integration.md:30)
- [D: docs/assurance/guardian-integration.md:9](/Users/yu/Documents/dev/software-production-platform/docs/assurance/guardian-integration.md:9)
- [D: docs/architecture/production-execution-package-direction.md:42](/Users/yu/Documents/dev/software-production-platform/docs/architecture/production-execution-package-direction.md:42)

<a id="c01"></a>
### C01 — Task to model/tool loop

RegularTask emits lifecycle before prewarm resolution, then run_turn captures a consistent step context, samples, consumes tool results and pending input, and decides follow-up. Completion is runtime/model control, not independent assurance.

- [S: codex-rs/core/src/tasks/regular.rs:40](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/tasks/regular.rs:40) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/tasks/regular.rs#L40)
- [S: codex-rs/core/src/session/turn.rs:163](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/session/turn.rs:163) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/session/turn.rs#L163)
- [S: codex-rs/core/src/session/turn.rs:409](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/session/turn.rs:409) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/session/turn.rs#L409)
- [S: codex-rs/core/src/session/turn.rs:1520](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/session/turn.rs:1520) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/session/turn.rs#L1520)

<a id="c02"></a>
### C02 — Rollout persistence and reconstruction

Canonical items are buffered and serialized through a writer; explicit persist/flush exists. Reconstruction restores history and settings through compaction and rollback. Flush is not a filesystem/process snapshot or a proven power-loss fsync guarantee.

- [S: codex-rs/rollout/src/recorder.rs:1013](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/rollout/src/recorder.rs:1013) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/rollout/src/recorder.rs#L1013)
- [S: codex-rs/rollout/src/recorder.rs:1031](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/rollout/src/recorder.rs:1031) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/rollout/src/recorder.rs#L1031)
- [S: codex-rs/core/src/session/rollout_reconstruction.rs:103](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/session/rollout_reconstruction.rs:103) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/session/rollout_reconstruction.rs#L103)
- [T: codex-rs/core/src/session/rollout_reconstruction_tests.rs:530](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/session/rollout_reconstruction_tests.rs:530) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/session/rollout_reconstruction_tests.rs#L530)

<a id="c03"></a>
### C03 — Client disconnect versus server death

Connection cleanup removes subscriptions without directly aborting a loaded core thread. WebSocket test covers retention until idle unload; resume tests cover persisted ownership/settings. This does not identify the actual deployment topology of the Human incident.

- [S: codex-rs/app-server/src/request_processors/thread_processor.rs:3588](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/app-server/src/request_processors/thread_processor.rs:3588) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/app-server/src/request_processors/thread_processor.rs#L3588)
- [T: codex-rs/app-server/tests/suite/v2/connection_handling_websocket.rs:453](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/app-server/tests/suite/v2/connection_handling_websocket.rs:453) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/app-server/tests/suite/v2/connection_handling_websocket.rs#L453)
- [T: codex-rs/app-server/tests/suite/v2/thread_resume.rs:314](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/app-server/tests/suite/v2/thread_resume.rs:314) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/app-server/tests/suite/v2/thread_resume.rs#L314)
- [T: codex-rs/app-server/tests/suite/v2/thread_resume.rs:624](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/app-server/tests/suite/v2/thread_resume.rs:624) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/app-server/tests/suite/v2/thread_resume.rs#L624)

<a id="c04"></a>
### C04 — Remote compaction and failure

Pre-sampling compaction failure preserves new input and returns with an error; mid-turn failure also stops the turn. V2 computes a candidate history, installs it in memory and records a Compacted rollout item containing replacement history and metadata; no memory/disk atomicity claim is made. Request retries and narrowly eligible previous-to-current-model compaction fallback exist. Do not infer arbitrary-provider portability.

- [S: codex-rs/core/src/session/turn.rs:183](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/session/turn.rs:183) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/session/turn.rs#L183)
- [S: codex-rs/core/src/compact_remote_v2_attempt.rs:31](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/compact_remote_v2_attempt.rs:31) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/compact_remote_v2_attempt.rs#L31)
- [S: codex-rs/core/src/compact_remote_v2.rs:346](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/compact_remote_v2.rs:346) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/compact_remote_v2.rs#L346)
- [S: codex-rs/core/src/compact_model_fallback.rs:9](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/compact_model_fallback.rs:9) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/compact_model_fallback.rs#L9)
- [S: codex-rs/core/src/session/mod.rs:3899](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/session/mod.rs:3899) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/session/mod.rs#L3899)
- [S: codex-rs/core/src/compact_remote_v2.rs:836](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/compact_remote_v2.rs:836) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/compact_remote_v2.rs#L836)

<a id="c05"></a>
### C05 — Transport retries and error classification

Sampling and compaction share retry decisions, retry advice/backoff and WebSocket-to-HTTPS transport fallback. Feature-gated unbounded network retries exist for a restricted sampling path; transport fallback is not provider/model fallback.

- [S: codex-rs/core/src/responses_retry.rs:51](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/responses_retry.rs:51) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/responses_retry.rs#L51)
- [S: codex-rs/protocol/src/error.rs:372](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/protocol/src/error.rs:372) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/protocol/src/error.rs#L372)
- [T: codex-rs/core/src/responses_retry_tests.rs:9](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/responses_retry_tests.rs:9) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/responses_retry_tests.rs#L9)

<a id="c06"></a>
### C06 — Tool contracts and capabilities

ToolRouter binds model-visible schemas to executable runtimes. ToolOrchestrator centralizes approval, sandbox and controlled escalation; permission roots can be plural. Policy checks do not make all shell effects idempotent.

- [S: codex-rs/core/src/tools/router.rs:74](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/tools/router.rs:74) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/tools/router.rs#L74)
- [S: codex-rs/core/src/tools/orchestrator.rs:121](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/tools/orchestrator.rs:121) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/tools/orchestrator.rs#L121)
- [S: codex-rs/core/src/tools/registry.rs:48](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/tools/registry.rs:48) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/tools/registry.rs#L48)
- [T: codex-rs/app-server/tests/suite/v2/thread_resume.rs:1624](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/app-server/tests/suite/v2/thread_resume.rs:1624) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/app-server/tests/suite/v2/thread_resume.rs#L1624)

<a id="c07"></a>
### C07 — Persistent interactive processes

Unified Exec manages handles, capped output and streaming across calls; completion-only calls terminate on timeout/cancel. A live handle is runtime state, not a restartable process image.

- [S: codex-rs/core/src/unified_exec/mod.rs:1](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/unified_exec/mod.rs:1) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/unified_exec/mod.rs#L1)
- [S: codex-rs/core/src/unified_exec/process_manager.rs:260](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/unified_exec/process_manager.rs:260) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/unified_exec/process_manager.rs#L260)
- [S: codex-rs/core/src/unified_exec/head_tail_buffer.rs:11](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/unified_exec/head_tail_buffer.rs:11) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/unified_exec/head_tail_buffer.rs#L11)
- [T: codex-rs/core/src/unified_exec/process_manager_tests.rs:41](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/unified_exec/process_manager_tests.rs:41) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/unified_exec/process_manager_tests.rs#L41)

<a id="c08"></a>
### C08 — Managed worktree lifecycle

Manager resolves an exact commit, creates a detached worktree without checkout, populates it, records ownership and rolls back failed creation. Deletion refuses current checkout and ignored local files, and uses non-force Git removal. One manager operation concerns one repository.

- [S: codex-rs/worktree/src/lib.rs:61](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/worktree/src/lib.rs:61) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/worktree/src/lib.rs#L61)
- [S: codex-rs/worktree/src/lib.rs:284](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/worktree/src/lib.rs:284) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/worktree/src/lib.rs#L284)
- [T: codex-rs/worktree/tests/worktree.rs:24](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/worktree/tests/worktree.rs:24) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/worktree/tests/worktree.rs#L24)

<a id="c09"></a>
### C09 — Context and latency seams

Repository instructions, step context and retained context are separate runtime inputs. Timing distinguishes first token, first meaningful item, sampling, compaction and tool blocking; startup can prewarm a client session.

- [S: codex-rs/core/src/agents_md.rs:18](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/agents_md.rs:18) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/agents_md.rs#L18)
- [S: codex-rs/core/src/session/step_context.rs:3](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/session/step_context.rs:3) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/session/step_context.rs#L3)
- [S: codex-rs/core/src/turn_timing.rs:19](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/turn_timing.rs:19) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/turn_timing.rs#L19)
- [S: codex-rs/core/src/tasks/regular.rs:60](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/tasks/regular.rs:60) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/tasks/regular.rs#L60)
- [T: codex-rs/core/src/turn_timing_tests.rs:20](/Users/yu/Documents/dev/reference-lab/codex/codex-rs/core/src/turn_timing_tests.rs:20) · [pinned source](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/codex-rs/core/src/turn_timing_tests.rs#L20)

<a id="o01"></a>
### O01 — Repository boundary and creation adapter

This revision is Agent Canvas. README explicitly places Python agents/tools/workspaces in software-agent-sdk. The local adapter submits encrypted settings and working_dir/worktree intent to ConversationClient; backend execution is not present here.

- [D: README.md:139](/Users/yu/Documents/dev/reference-lab/OpenHands/README.md:139) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/README.md#L139)
- [D: docs/architecture.md:5](/Users/yu/Documents/dev/reference-lab/OpenHands/docs/architecture.md:5) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/docs/architecture.md#L5)
- [S: src/api/conversation-service/agent-server-conversation-service.api.ts:425](/Users/yu/Documents/dev/reference-lab/OpenHands/src/api/conversation-service/agent-server-conversation-service.api.ts:425) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/src/api/conversation-service/agent-server-conversation-service.api.ts#L425)
- [S: src/api/conversation-service/agent-server-conversation-service.api.ts:514](/Users/yu/Documents/dev/reference-lab/OpenHands/src/api/conversation-service/agent-server-conversation-service.api.ts:514) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/src/api/conversation-service/agent-server-conversation-service.api.ts#L514)

<a id="o02"></a>
### O02 — Pause semantics differ by backend

Local pause action calls interruptConversation; cloud branch calls pauseCloudSandbox; resume calls runConversation. These prove client requests, not backend cancellation or checkpoint guarantees.

- [S: src/hooks/mutation/conversation-mutation-utils.ts:41](/Users/yu/Documents/dev/reference-lab/OpenHands/src/hooks/mutation/conversation-mutation-utils.ts:41) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/src/hooks/mutation/conversation-mutation-utils.ts#L41)
- [S: src/hooks/mutation/conversation-mutation-utils.ts:117](/Users/yu/Documents/dev/reference-lab/OpenHands/src/hooks/mutation/conversation-mutation-utils.ts:117) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/src/hooks/mutation/conversation-mutation-utils.ts#L117)
- [T: __tests__/hooks/mutation/pause-conversation-local.test.ts:69](/Users/yu/Documents/dev/reference-lab/OpenHands/__tests__/hooks/mutation/pause-conversation-local.test.ts:69) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/__tests__/hooks/mutation/pause-conversation-local.test.ts#L69)

<a id="o03"></a>
### O03 — History reconnect and sandbox wake

REST history seeds the event store, a timestamp anchors live replay, and overlapping events are deduplicated. Wrapper suppresses stale cloud URLs while sandbox is PAUSED. Backend event retention remains outside this checkout.

- [S: src/contexts/conversation-websocket-context.tsx:281](/Users/yu/Documents/dev/reference-lab/OpenHands/src/contexts/conversation-websocket-context.tsx:281) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/src/contexts/conversation-websocket-context.tsx#L281)
- [S: src/contexts/conversation-websocket-context.tsx:363](/Users/yu/Documents/dev/reference-lab/OpenHands/src/contexts/conversation-websocket-context.tsx:363) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/src/contexts/conversation-websocket-context.tsx#L363)
- [T: __tests__/contexts/websocket-provider-wrapper.test.tsx:124](/Users/yu/Documents/dev/reference-lab/OpenHands/__tests__/contexts/websocket-provider-wrapper.test.tsx:124) · [pinned source](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/__tests__/contexts/websocket-provider-wrapper.test.tsx#L124)

<a id="s01"></a>
### S01 — Observe, act, repair and completion

RunSingle binds problem/environment/agent. DefaultAgent calls model, parses actions, executes through environment, adds history/trajectory and repeats until done. Format, blocklist and shell syntax errors have bounded requery paths.

- [S: sweagent/run/run_single.py:188](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/run/run_single.py:188) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/run/run_single.py#L188)
- [D: README.md:20](/Users/yu/Documents/dev/reference-lab/SWE-agent/README.md:20) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/README.md#L20)
- [S: sweagent/agent/agents.py:1062](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/agent/agents.py:1062) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/agents.py#L1062)
- [S: sweagent/agent/agents.py:1220](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/agent/agents.py:1220) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/agents.py#L1220)
- [S: sweagent/agent/agents.py:408](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/agent/agents.py:408) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/agents.py#L408)
- [T: tests/test_agent.py:110](/Users/yu/Documents/dev/reference-lab/SWE-agent/tests/test_agent.py:110) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/tests/test_agent.py#L110)

<a id="s02"></a>
### S02 — Failure salvage and retry reset

Errors can trigger patch extraction even after a cost stop; last recorded diff is a fallback if environment died. RetryAgent resets the environment before another attempt. Extraction is not proof the patch passes tests.

- [S: sweagent/agent/agents.py:823](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/agent/agents.py:823) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/agents.py#L823)
- [S: sweagent/agent/agents.py:321](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/agent/agents.py:321) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/agents.py#L321)
- [T: tests/test_agent.py:191](/Users/yu/Documents/dev/reference-lab/SWE-agent/tests/test_agent.py:191) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/tests/test_agent.py#L191)

<a id="s03"></a>
### S03 — Environment and tool process seam

SWEEnv delegates to external SWE-ReX deployment/runtime, initializes a Bash session and supports timeout/interrupt. Repo is optional but one configured repo is the built-in abstraction. Deployment internals are not local source evidence. Tool configuration can propagate environment variables and explicitly notes exposure in debug logs; this is not a secret-isolation mechanism.

- [S: sweagent/environment/swe_env.py:24](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/environment/swe_env.py:24) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/environment/swe_env.py#L24)
- [S: sweagent/environment/swe_env.py:135](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/environment/swe_env.py:135) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/environment/swe_env.py#L135)
- [S: sweagent/environment/swe_env.py:192](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/environment/swe_env.py:192) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/environment/swe_env.py#L192)
- [S: sweagent/environment/swe_env.py:197](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/environment/swe_env.py:197) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/environment/swe_env.py#L197)
- [S: sweagent/environment/repo.py:20](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/environment/repo.py:20) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/environment/repo.py#L20)
- [S: sweagent/tools/tools.py:86](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/tools/tools.py:86) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/tools/tools.py#L86)

<a id="s04"></a>
### S04 — Trajectory, replay and model cost

Trajectory JSON includes query/action/observation/state/timing and replay configuration. Replay actually executes recorded actions. LiteLLM supports model adapters and measured cost checks; checks can occur after spend.

- [S: sweagent/agent/agents.py:385](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/agent/agents.py:385) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/agents.py#L385)
- [S: sweagent/run/run_replay.py:66](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/run/run_replay.py:66) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/run/run_replay.py#L66)
- [S: sweagent/agent/models.py:634](/Users/yu/Documents/dev/reference-lab/SWE-agent/sweagent/agent/models.py:634) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/models.py#L634)
- [T: tests/test_run_replay.py:20](/Users/yu/Documents/dev/reference-lab/SWE-agent/tests/test_run_replay.py:20) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/tests/test_run_replay.py#L20)
- [T: tests/test_agent.py:80](/Users/yu/Documents/dev/reference-lab/SWE-agent/tests/test_agent.py:80) · [pinned source](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/tests/test_agent.py#L80)

<a id="a01"></a>
### A01 — Editing and reflection loop

Coder run/send applies structured edits, then local lint/test output can drive bounded reflection. Confirmation around ordinary repair is CLI interaction policy, not a necessary Watt Human gate.

- [S: aider/coders/base_coder.py:924](/Users/yu/Documents/dev/reference-lab/aider/aider/coders/base_coder.py:924) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L924)
- [S: aider/coders/base_coder.py:1419](/Users/yu/Documents/dev/reference-lab/aider/aider/coders/base_coder.py:1419) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L1419)
- [S: aider/coders/base_coder.py:1585](/Users/yu/Documents/dev/reference-lab/aider/aider/coders/base_coder.py:1585) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L1585)
- [T: tests/basic/test_coder.py:1149](/Users/yu/Documents/dev/reference-lab/aider/tests/basic/test_coder.py:1149) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/tests/basic/test_coder.py#L1149)

<a id="a02"></a>
### A02 — Dirty edit preservation and one-repo assumption

Selected dirty files can be committed before generated edits. GitRepo rejects files belonging to different repositories. Auto-commit/undo is local editing machinery, not Watt trusted integration.

- [S: aider/coders/base_coder.py:2175](/Users/yu/Documents/dev/reference-lab/aider/aider/coders/base_coder.py:2175) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L2175)
- [S: aider/repo.py:120](/Users/yu/Documents/dev/reference-lab/aider/aider/repo.py:120) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/repo.py#L120)
- [S: aider/commands.py:560](/Users/yu/Documents/dev/reference-lab/aider/aider/commands.py:560) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/commands.py#L560)
- [T: tests/basic/test_coder.py:667](/Users/yu/Documents/dev/reference-lab/aider/tests/basic/test_coder.py:667) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/tests/basic/test_coder.py#L667)

<a id="a03"></a>
### A03 — Incremental context and summary

RepoMap caches tags by mtime and ranks repository structure into a token budget. ChatSummary summarizes older dialogue and keeps recent messages; Coder runs summarization in a thread and joins it. These are useful context optimizations, not ECF.

- [S: aider/repomap.py:103](/Users/yu/Documents/dev/reference-lab/aider/aider/repomap.py:103) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/repomap.py#L103)
- [S: aider/repomap.py:246](/Users/yu/Documents/dev/reference-lab/aider/aider/repomap.py:246) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/repomap.py#L246)
- [S: aider/history.py:7](/Users/yu/Documents/dev/reference-lab/aider/aider/history.py:7) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/history.py#L7)
- [S: aider/coders/base_coder.py:1002](/Users/yu/Documents/dev/reference-lab/aider/aider/coders/base_coder.py:1002) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L1002)
- [T: tests/basic/test_repomap.py:49](/Users/yu/Documents/dev/reference-lab/aider/tests/basic/test_repomap.py:49) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/tests/basic/test_repomap.py#L49)

<a id="a04"></a>
### A04 — Provider and session portability limits

Model command changes the model/coder; retry uses error categories and exponential delays. Saved chat/restored configuration does not preserve an active process or an in-flight tool effect.

- [S: aider/commands.py:87](/Users/yu/Documents/dev/reference-lab/aider/aider/commands.py:87) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/commands.py#L87)
- [S: aider/commands.py:1497](/Users/yu/Documents/dev/reference-lab/aider/aider/commands.py:1497) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/commands.py#L1497)
- [S: aider/coders/base_coder.py:1449](/Users/yu/Documents/dev/reference-lab/aider/aider/coders/base_coder.py:1449) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L1449)
- [S: aider/models.py:128](/Users/yu/Documents/dev/reference-lab/aider/aider/models.py:128) · [pinned source](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/models.py#L128)

<a id="l01"></a>
### L01 — Generation identity and fences

Request allocates a generation with expected predecessor and idempotency claim. Manager/store separate live generation ownership, durable state and publication. Redis integration tests reject stale writes/replacement; Redis deployment durability is still a dependency.

- [S: api/server/controllers/agents/request.js:1564](/Users/yu/Documents/dev/reference-lab/LibreChat/api/server/controllers/agents/request.js:1564) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/api/server/controllers/agents/request.js#L1564)
- [S: packages/api/src/stream/GenerationJobManager.ts:755](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/GenerationJobManager.ts:755) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/GenerationJobManager.ts#L755)
- [S: packages/api/src/stream/implementations/RedisJobStore.ts:1836](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/implementations/RedisJobStore.ts:1836) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/implementations/RedisJobStore.ts#L1836)
- [T: packages/api/src/stream/__tests__/predecessorFence.stream_integration.spec.ts:72](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/__tests__/predecessorFence.stream_integration.spec.ts:72) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/__tests__/predecessorFence.stream_integration.spec.ts#L72)

<a id="l02"></a>
### L02 — Reconnect is not rerun

Resume snapshots reconstruct retained steps and content with generation checks; chunk replay is separate from the live graph. Buffers are bounded and late/stale publications fenced. This supports UI reconnection, not generic external-side-effect replay.

- [S: packages/api/src/stream/GenerationJobManager.ts:164](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/GenerationJobManager.ts:164) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/GenerationJobManager.ts#L164)
- [T: packages/api/src/stream/__tests__/GenerationJobManager.resumeReplay.spec.ts:177](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/__tests__/GenerationJobManager.resumeReplay.spec.ts:177) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/__tests__/GenerationJobManager.resumeReplay.spec.ts#L177)
- [T: packages/api/src/stream/__tests__/GenerationJobManager.resumeReplay.spec.ts:410](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/__tests__/GenerationJobManager.resumeReplay.spec.ts:410) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/__tests__/GenerationJobManager.resumeReplay.spec.ts#L410)

<a id="l03"></a>
### L03 — Steering queue and receipt integrity

Mid-run input drains at PostToolBatch into graph HumanMessages; receipts and owner leases survive publication failure. Watt can adapt delivery mechanics but must place WIC/Work admission before injection.

- [S: packages/api/src/stream/SteeringLifecycle.ts:115](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/SteeringLifecycle.ts:115) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/SteeringLifecycle.ts#L115)
- [S: packages/api/src/agents/steering/runtime.ts:14](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/agents/steering/runtime.ts:14) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/agents/steering/runtime.ts#L14)
- [T: packages/api/src/stream/__tests__/steerReceiptIntegrity.spec.ts:237](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/__tests__/steerReceiptIntegrity.spec.ts:237) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/__tests__/steerReceiptIntegrity.spec.ts#L237)

<a id="l04"></a>
### L04 — Approval/checkpoint namespaces

Checkpoint namespaces bind authenticated owner/tenant; approval lifecycle has persistence/expiration handling. Checkpoints default to bounded TTL rather than permanent engineering records.

- [S: packages/api/src/stream/checkpoints.ts:3](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/checkpoints.ts:3) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/checkpoints.ts#L3)
- [S: packages/api/src/stream/ApprovalLifecycle.ts:94](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/ApprovalLifecycle.ts:94) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/ApprovalLifecycle.ts#L94)
- [T: packages/api/src/stream/__tests__/hitlResumeRedis.stream_integration.spec.ts:13](/Users/yu/Documents/dev/reference-lab/LibreChat/packages/api/src/stream/__tests__/hitlResumeRedis.stream_integration.spec.ts:13) · [pinned source](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/packages/api/src/stream/__tests__/hitlResumeRedis.stream_integration.spec.ts#L13)

<a id="b01"></a>
### B01 — Agent instruction runtime and step host

Runtime step plans instructions and dispatches executors. Server executeStep checks durable cancellation, claims an owned step lock, hydrates messages, runs and saves step results. maxSteps uses forceFinish to ask for final output rather than treating text as assurance.

- [S: packages/agent-runtime/src/core/runtime.ts:82](/Users/yu/Documents/dev/reference-lab/lobehub/packages/agent-runtime/src/core/runtime.ts:82) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/packages/agent-runtime/src/core/runtime.ts#L82)
- [S: apps/server/src/services/agentRuntime/AgentRuntimeService.ts:1256](/Users/yu/Documents/dev/reference-lab/lobehub/apps/server/src/services/agentRuntime/AgentRuntimeService.ts:1256) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/apps/server/src/services/agentRuntime/AgentRuntimeService.ts#L1256)
- [S: apps/server/src/services/agentRuntime/AgentRuntimeService.ts:2022](/Users/yu/Documents/dev/reference-lab/lobehub/apps/server/src/services/agentRuntime/AgentRuntimeService.ts:2022) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/apps/server/src/services/agentRuntime/AgentRuntimeService.ts#L2022)
- [T: apps/server/src/services/agentRuntime/__tests__/executeStep.test.ts:79](/Users/yu/Documents/dev/reference-lab/lobehub/apps/server/src/services/agentRuntime/__tests__/executeStep.test.ts:79) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/apps/server/src/services/agentRuntime/__tests__/executeStep.test.ts#L79)

<a id="b02"></a>
### B02 — Split state and short retention

Redis state omits reconstructible DB messages, retains ephemeral messages and uses a two-hour default TTL. Owned lock refresh/release and interruption sentinel exist. Database message survival alone does not restore expired execution state.

- [S: apps/server/src/modules/AgentRuntime/AgentStateManager.ts:68](/Users/yu/Documents/dev/reference-lab/lobehub/apps/server/src/modules/AgentRuntime/AgentStateManager.ts:68) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/apps/server/src/modules/AgentRuntime/AgentStateManager.ts#L68)
- [T: apps/server/src/modules/AgentRuntime/__tests__/AgentStateManager.test.ts:81](/Users/yu/Documents/dev/reference-lab/lobehub/apps/server/src/modules/AgentRuntime/__tests__/AgentStateManager.test.ts:81) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/apps/server/src/modules/AgentRuntime/__tests__/AgentStateManager.test.ts#L81)
- [T: apps/server/src/modules/AgentRuntime/__tests__/AgentStateManager.test.ts:97](/Users/yu/Documents/dev/reference-lab/lobehub/apps/server/src/modules/AgentRuntime/__tests__/AgentStateManager.test.ts:97) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/apps/server/src/modules/AgentRuntime/__tests__/AgentStateManager.test.ts#L97)
- [T: apps/server/src/modules/AgentRuntime/__tests__/AgentStateManager.test.ts:202](/Users/yu/Documents/dev/reference-lab/lobehub/apps/server/src/modules/AgentRuntime/__tests__/AgentStateManager.test.ts:202) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/apps/server/src/modules/AgentRuntime/__tests__/AgentStateManager.test.ts#L202)

<a id="b03"></a>
### B03 — Compaction preserves current user message

Compression uses host transports, preserves latest user message and rolls back a created group if summarization fails. Good replacement discipline; latest chat message is not an acceptable substitute for Watt versioned contract.

- [S: packages/agent-runtime/src/executors/compressContext.ts:41](/Users/yu/Documents/dev/reference-lab/lobehub/packages/agent-runtime/src/executors/compressContext.ts:41) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/packages/agent-runtime/src/executors/compressContext.ts#L41)
- [T: packages/agent-runtime/src/executors/compressContext.test.ts:242](/Users/yu/Documents/dev/reference-lab/lobehub/packages/agent-runtime/src/executors/compressContext.test.ts:242) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/packages/agent-runtime/src/executors/compressContext.test.ts#L242)
- [T: packages/agent-runtime/src/executors/compressContext.test.ts:454](/Users/yu/Documents/dev/reference-lab/lobehub/packages/agent-runtime/src/executors/compressContext.test.ts:454) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/packages/agent-runtime/src/executors/compressContext.test.ts#L454)

<a id="b04"></a>
### B04 — Typed retry and resource visibility

Runtime distinguishes retry/stop model errors and retry/replan/stop tool results, with capped backoff and interrupt checks. Generic retryable tool labels do not establish safe repetition of mutations.

- [S: packages/agent-runtime/src/utils/runtimeRetry.ts:57](/Users/yu/Documents/dev/reference-lab/lobehub/packages/agent-runtime/src/utils/runtimeRetry.ts:57) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/packages/agent-runtime/src/utils/runtimeRetry.ts#L57)
- [S: packages/agent-runtime/src/utils/llmErrorClassifier.ts:47](/Users/yu/Documents/dev/reference-lab/lobehub/packages/agent-runtime/src/utils/llmErrorClassifier.ts:47) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/packages/agent-runtime/src/utils/llmErrorClassifier.ts#L47)
- [S: packages/agent-runtime/src/core/UsageCounter.ts:10](/Users/yu/Documents/dev/reference-lab/lobehub/packages/agent-runtime/src/core/UsageCounter.ts:10) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/packages/agent-runtime/src/core/UsageCounter.ts#L10)
- [T: packages/agent-runtime/src/utils/runtimeRetry.test.ts:11](/Users/yu/Documents/dev/reference-lab/lobehub/packages/agent-runtime/src/utils/runtimeRetry.test.ts:11) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/packages/agent-runtime/src/utils/runtimeRetry.test.ts#L11)
- [S: packages/agent-runtime/src/utils/toolCallRepeatGuard.ts:11](/Users/yu/Documents/dev/reference-lab/lobehub/packages/agent-runtime/src/utils/toolCallRepeatGuard.ts:11) · [pinned source](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/packages/agent-runtime/src/utils/toolCallRepeatGuard.ts#L11)

<a id="u01"></a>
### U01 — Async task lifetime and partial results

Asyncio tasks run in-process; Redis stores IDs/control and response projections. Cancellation closes upstream iterator and shields partial-output saving. Redis task registration is not serialized coroutine execution.

- [S: backend/open_webui/main.py:1824](/Users/yu/Documents/dev/reference-lab/open-webui/backend/open_webui/main.py:1824) · [pinned source](https://github.com/open-webui/open-webui/blob/0a7c15832fb30b1903753e83f81dc7d27e5b0944/backend/open_webui/main.py#L1824)
- [S: backend/open_webui/tasks.py:131](/Users/yu/Documents/dev/reference-lab/open-webui/backend/open_webui/tasks.py:131) · [pinned source](https://github.com/open-webui/open-webui/blob/0a7c15832fb30b1903753e83f81dc7d27e5b0944/backend/open_webui/tasks.py#L131)
- [S: backend/open_webui/tasks.py:172](/Users/yu/Documents/dev/reference-lab/open-webui/backend/open_webui/tasks.py:172) · [pinned source](https://github.com/open-webui/open-webui/blob/0a7c15832fb30b1903753e83f81dc7d27e5b0944/backend/open_webui/tasks.py#L172)
- [S: backend/open_webui/utils/middleware.py:6293](/Users/yu/Documents/dev/reference-lab/open-webui/backend/open_webui/utils/middleware.py:6293) · [pinned source](https://github.com/open-webui/open-webui/blob/0a7c15832fb30b1903753e83f81dc7d27e5b0944/backend/open_webui/utils/middleware.py#L6293)

<a id="u02"></a>
### U02 — Chat tool loop and boundaries

Middleware assembles chat/tool context and iterates model tool calls up to configured limits, including Human question staging. No targeted backend restart/tool-effect tests were located in the inspected checkout; this is source-only evidence.

- [S: backend/open_webui/utils/middleware.py:5576](/Users/yu/Documents/dev/reference-lab/open-webui/backend/open_webui/utils/middleware.py:5576) · [pinned source](https://github.com/open-webui/open-webui/blob/0a7c15832fb30b1903753e83f81dc7d27e5b0944/backend/open_webui/utils/middleware.py#L5576)
- [S: backend/open_webui/routers/tools.py:48](/Users/yu/Documents/dev/reference-lab/open-webui/backend/open_webui/routers/tools.py:48) · [pinned source](https://github.com/open-webui/open-webui/blob/0a7c15832fb30b1903753e83f81dc7d27e5b0944/backend/open_webui/routers/tools.py#L48)
- [S: backend/open_webui/socket/main.py:200](/Users/yu/Documents/dev/reference-lab/open-webui/backend/open_webui/socket/main.py:200) · [pinned source](https://github.com/open-webui/open-webui/blob/0a7c15832fb30b1903753e83f81dc7d27e5b0944/backend/open_webui/socket/main.py#L200)

<a id="g01"></a>
### G01 — Durable graph state and pending writes

Pregel loads checkpoints and pending writes, schedules tasks, then applies writes/checkpoints after a superstep. A successful sibling result can survive another node failure; external effects are outside channel transactions.

- [S: libs/langgraph/langgraph/pregel/_loop.py:661](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/langgraph/pregel/_loop.py:661) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/langgraph/pregel/_loop.py#L661)
- [S: libs/langgraph/langgraph/pregel/_loop.py:683](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/langgraph/pregel/_loop.py:683) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/langgraph/pregel/_loop.py#L683)
- [S: libs/checkpoint/langgraph/checkpoint/base/__init__.py:177](/Users/yu/Documents/dev/reference-lab/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py:177) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L177)
- [T: libs/langgraph/tests/test_pregel.py:891](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/tests/test_pregel.py:891) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/tests/test_pregel.py#L891)

<a id="g02"></a>
### G02 — Interrupt and durability modes

interrupt raises resumable control flow; Command(resume) restarts node logic and matches interrupt values. sync/async/exit persistence modes have different crash windows; a durable saver must be supplied.

- [S: libs/langgraph/langgraph/types.py:622](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/langgraph/types.py:622) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/langgraph/types.py#L622)
- [S: libs/langgraph/langgraph/pregel/main.py:2705](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/langgraph/pregel/main.py:2705) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/langgraph/pregel/main.py#L2705)
- [T: libs/langgraph/tests/test_pregel.py:5818](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/tests/test_pregel.py:5818) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/tests/test_pregel.py#L5818)

<a id="g03"></a>
### G03 — Retry and timeout boundaries

Retry runtime tracks per-node attempt metadata, run/idle timeouts and guards writes after timeout. These are orchestration attempts, not Watt execution grants; guarded state writes cannot undo an already executed shell/API action.

- [S: libs/langgraph/langgraph/pregel/_retry.py:87](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/langgraph/pregel/_retry.py:87) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/langgraph/pregel/_retry.py#L87)
- [S: libs/langgraph/langgraph/pregel/_retry.py:128](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/langgraph/pregel/_retry.py:128) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/langgraph/pregel/_retry.py#L128)
- [S: libs/langgraph/langgraph/types.py:418](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/langgraph/types.py:418) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/langgraph/types.py#L418)
- [S: libs/langgraph/langgraph/pregel/_runner.py:135](/Users/yu/Documents/dev/reference-lab/langgraph/libs/langgraph/langgraph/pregel/_runner.py:135) · [pinned source](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/libs/langgraph/langgraph/pregel/_runner.py#L135)

<a id="t01"></a>
### T01 — Assistant and team loops

Assistant separates model client, tools, context and bounded tool iterations. Team supplies scheduling/termination. Concurrent tool calls require host safety policy; group completion is not engineering assurance.

- [S: python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py:901](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py:901) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py#L901)
- [S: python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py:351](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py:351) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py#L351)
- [T: python/packages/autogen-agentchat/tests/test_assistant_agent.py:189](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-agentchat/tests/test_assistant_agent.py:189) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-agentchat/tests/test_assistant_agent.py#L189)

<a id="t02"></a>
### T02 — Pause and save-state limitations

Team pause/resume calls agent hooks; default hooks can do nothing. Test uses a custom cooperative agent. Save/load exports agent state, not the runtime message queue or an active OS process.

- [S: python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py:657](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py:657) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py#L657)
- [T: python/packages/autogen-agentchat/tests/test_group_chat_pause_resume.py:90](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-agentchat/tests/test_group_chat_pause_resume.py:90) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-agentchat/tests/test_group_chat_pause_resume.py#L90)
- [S: python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py:431](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py:431) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py#L431)
- [T: python/packages/autogen-core/tests/test_state.py:43](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-core/tests/test_state.py:43) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-core/tests/test_state.py#L43)

<a id="t03"></a>
### T03 — Docker tool execution

Docker executor reuses a container, binds working directory and optional RO/RW volumes, writes code files, uses command timeout and attempts process kill after cancellation. Extra mounts do not supply multi-repository baseline/transaction semantics.

- [S: python/packages/autogen-ext/src/autogen_ext/code_executors/docker/_docker_code_executor.py:292](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-ext/src/autogen_ext/code_executors/docker/_docker_code_executor.py:292) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-ext/src/autogen_ext/code_executors/docker/_docker_code_executor.py#L292)
- [S: python/packages/autogen-ext/src/autogen_ext/code_executors/docker/_docker_code_executor.py:495](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-ext/src/autogen_ext/code_executors/docker/_docker_code_executor.py:495) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-ext/src/autogen_ext/code_executors/docker/_docker_code_executor.py#L495)
- [T: python/packages/autogen-ext/tests/code_executors/test_docker_commandline_code_executor.py:64](/Users/yu/Documents/dev/reference-lab/autogen/python/packages/autogen-ext/tests/code_executors/test_docker_commandline_code_executor.py:64) · [pinned source](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-ext/tests/code_executors/test_docker_commandline_code_executor.py#L64)

<a id="h01"></a>
### H01 — Public boundary and hook sample

Checkout contains distribution docs/examples/plugins, not core executor source. PreToolUse sample parses JSON and uses exit status to block a command; strict settings illustrate managed permissions. These do not prove sandbox implementation.

- [D: README.md:48](/Users/yu/Documents/dev/reference-lab/claude-code/README.md:48) · [pinned source](https://github.com/anthropics/claude-code/blob/e62465d553ecbf1697219ffbb3c11b4fef14d5bf/README.md#L48)
- [S: examples/hooks/bash_command_validator_example.py:56](/Users/yu/Documents/dev/reference-lab/claude-code/examples/hooks/bash_command_validator_example.py:56) · [pinned source](https://github.com/anthropics/claude-code/blob/e62465d553ecbf1697219ffbb3c11b4fef14d5bf/examples/hooks/bash_command_validator_example.py#L56)
- [S: examples/settings/settings-strict.json:2](/Users/yu/Documents/dev/reference-lab/claude-code/examples/settings/settings-strict.json:2) · [pinned source](https://github.com/anthropics/claude-code/blob/e62465d553ecbf1697219ffbb3c11b4fef14d5bf/examples/settings/settings-strict.json#L2)

<a id="h02"></a>
### H02 — Changelog and plugin loop limitations

Changelog reports restart/compaction fixes but is not implementation proof. Ralph stop hook reads a transcript and repeats a prompt until a promise/limit. This is public extension code, not core runtime recovery, and self-declared completion is unsuitable assurance.

- [D: CHANGELOG.md:70](/Users/yu/Documents/dev/reference-lab/claude-code/CHANGELOG.md:70) · [pinned source](https://github.com/anthropics/claude-code/blob/e62465d553ecbf1697219ffbb3c11b4fef14d5bf/CHANGELOG.md#L70)
- [S: plugins/ralph-wiggum/hooks/stop-hook.sh:50](/Users/yu/Documents/dev/reference-lab/claude-code/plugins/ralph-wiggum/hooks/stop-hook.sh:50) · [pinned source](https://github.com/anthropics/claude-code/blob/e62465d553ecbf1697219ffbb3c11b4fef14d5bf/plugins/ralph-wiggum/hooks/stop-hook.sh#L50)
- [S: plugins/ralph-wiggum/hooks/stop-hook.sh:130](/Users/yu/Documents/dev/reference-lab/claude-code/plugins/ralph-wiggum/hooks/stop-hook.sh:130) · [pinned source](https://github.com/anthropics/claude-code/blob/e62465d553ecbf1697219ffbb3c11b4fef14d5bf/plugins/ralph-wiggum/hooks/stop-hook.sh#L130)

## License inventory (file statements, not a reuse clearance)

| Repository | Inspected file and declared license |
|---|---|
| codex | [LICENSE](https://github.com/openai/codex/blob/94697375cb9d2aa8ae74d61957c6b396819bec94/LICENSE) — Apache-2.0; also NOTICE with third-party attribution |
| OpenHands | [LICENSE](https://github.com/All-Hands-AI/OpenHands/blob/725f5584b9411b1e47f1d0c5ebaf640676609940/LICENSE) — MIT |
| SWE-agent | [LICENSE](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/LICENSE) — MIT |
| aider | [LICENSE.txt](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/LICENSE.txt) — Apache-2.0 |
| LibreChat | [LICENSE](https://github.com/danny-avila/LibreChat/blob/b356c3d87edccd0bde68dc90a5eca66ae2c80e5d/LICENSE) — MIT |
| claude-code | [LICENSE.md](https://github.com/anthropics/claude-code/blob/e62465d553ecbf1697219ffbb3c11b4fef14d5bf/LICENSE.md) — All rights reserved; commercial terms referenced |
| open-webui | [LICENSE](https://github.com/open-webui/open-webui/blob/0a7c15832fb30b1903753e83f81dc7d27e5b0944/LICENSE) — Open WebUI License; branding conditions; historical per-origin licenses in LICENSE_HISTORY / LICENSE_NOTICE |
| lobehub | [LICENSE](https://github.com/lobehub/lobehub/blob/08cbe3236bca1ec4ca48d77058636e1f7e69e06a/LICENSE) — LobeHub Community License; additional commercial derivative conditions |
| langgraph | [LICENSE](https://github.com/langchain-ai/langgraph/blob/e539ac122f4126f6dd850581c1494948cf620e31/LICENSE) — MIT |
| autogen | [LICENSE-CODE](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/LICENSE-CODE) — MIT for code; LICENSE / README distinguish CC-BY-4.0 documentation |
