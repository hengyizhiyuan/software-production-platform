# MVP Scope Calibration and Phase-2 Hardening Backlog

## 1. Status and Authority

This document is the authoritative MVP delivery calibration under Architecture Baseline v0.1.

It changes roadmap priority, not the confirmed Runtime semantics or ownership boundaries. Existing R4-A and R4-B implementation remains intact. No product feature, Provider execution, production migration, Runtime mutation, or deployment is introduced by this document.

The current Product-MVP priority is:

> Preserve the closed Governed Production + Reality-driven Plan Steering and
> Work Interaction & Closed-loop Refinement Cores, then complete the separately
> governed Human WIC evidence and reassess Product-MVP closure before Product
> Experience and deployment work.

The MVP development workflow remains Human Governor + ChatGPT Architecture
Lead + Codex repo-grounded Executor, governed by the
[AI-native Development Execution Principles](../architecture/ai-native-development-execution-principles.md).

## 2. MVP Product Definition

The MVP is usable when a user can:

1. Run the product locally in the intended Docker development environment.
2. Open a functional Web UI.
3. View all Works or select an optional Goal navigation context.
4. Begin a natural-language Interaction without automatically creating Work.
5. Progressively refine an incomplete Motive and calibrate Watt's Shared Understanding.
6. Admit a sufficiently clear governed Work through the applicable Human boundary.
7. Continue natural-language interaction inside the active Work and govern material changes.
8. Observe the admitted Production Intent, Run, PWU, Attempt, and governed status.
9. Respond to required Human Attention and Authority actions.
10. Observe execution, independent production observation, Completion, and Verification outcomes.
11. Admit relevant Human/Runtime/Verification feedback into Work and Plan reassessment.
12. Obtain the resulting repository outcome and continue the same Work or transition truthfully to a new Work.

The UI may be visually simple. It must be functional, not a static demonstration. A CLI-only system is not the MVP product.

## 3. Current Implementation Reality

| Area | Current Reality | MVP Classification |
|---|---|---|
| Runtime domain and persistence | Run, Plan, PWU, Attempt, governed transitions, PostgreSQL, SQLAlchemy, Alembic, and Unit of Work are implemented | MVP CORE / GUARDRAIL |
| Production Source Baseline | Exact clean repository revision, pointer, and source bindings are implemented | MVP GUARDRAIL |
| Context Package Lite | Governed Context Package and Materialized Execution Input path are implemented | MVP CORE |
| Executor boundary | Provider-neutral Executor contract, Dedicated Executor boundary, Codex binding, workspace isolation, and deterministic evidence exist | MVP CORE; product integration/debugging remains |
| Execution and observation | Dispatch, Provider Report, independent repository observation, and Work Product lineage are implemented | MVP CORE / GUARDRAIL |
| Completion and Verification | Basic Completion Evaluation, Verification, and production-admissibility semantics are implemented | MVP CORE |
| Human Authority | Candidate authorization, governance records, and product-facing Attention query/action delegation exist | MVP CORE; HTTP/UI experience remains |
| Repository result handling | Candidate, authorized integration, and Runtime Commit semantics are implemented | MVP CORE / GUARDRAIL |
| Recovery | S5 recovery foundations are implemented; R4-B maintenance-lineage recovery capability is implemented and focused/affected validation passed | Stronger existing guarantee; complete R4 closure is deferred |
| API / product application facade | Goal-centric governed Work Python application flow and minimal Goal/Work FastAPI surface are closed with focused validation pass | MVP CORE / CLOSED / PASS |
| Web UI | Same-origin FastAPI-served Goal / Work Control Room implements intake, refinement/admission, one-step advance, Attention, and truthful Work Result views | MVP CORE / CLOSED / PASS |
| Motive / Work / Engineering Scope product model | Motive is the product-facing concept; Work is the current internal governed representation; Goal is an optional weak aggregation; Engineering Resources bind through explicit Engineering Scope | MVP PRODUCT MODEL / CONCEPT CALIBRATION CLOSED / PASS; IMPLEMENTATION REMAINS WORK-NAMED |
| Production Planner | Structured provider-neutral single-PWU Production Plan is durable, Human-visible before approval, and carried into the sole PWU/MEI; it is a narrow production-step plan, not full lifecycle steering | MVP CORE / PLAN-1B CLOSED / PASS |
| [Reality-driven Plan Steering](../architecture/reality-driven-plan-steering-mvp-contract.md) | 1C through 1L are CLOSED / PASS. Dogfood #9 proves the complete machine-side long-lived loop; Dogfood #10 proves Human-operated acceptance and exact Runtime activation. The remaining observability gap is explicit and non-blocking. | MATERIAL MVP CORE PRODUCT CAPABILITY / MVP CLOSED / PASS |
| [Work Interaction & Closed-loop Refinement](../architecture/work-interaction-closed-loop-refinement.md) | Slices 1–4 implement pre-Work formation, explicit Human Work admission, bounded active-Work evolution, exact satisfaction reconstruction, same-Motive continuation, and Human-governed new-Work formation transitions with preserved history and no inherited Authority | PRODUCT-SHAPE ESSENTIAL / SLICES 1–4 IMPLEMENTED / PASS / CORE CLOSED / PASS |
| [Guided Design Core](../architecture/guided-design-core.md) | General product/system design agenda, Steering-owned current focus, governed result continuity, explicit readiness, production-proposal review, restart reconstruction and real Provider proof are implemented | PRODUCT-SHAPE ESSENTIAL / IMPLEMENTED / FOCUSED VALIDATION PASS / HUMAN PRODUCT ACCEPTANCE PENDING |
| [Human–Watt Conversation Intelligence](../architecture/human-watt-conversation-intelligence.md) | Structured collaboration semantics, bounded Conversation Context Assembly, a dedicated configurable Human-facing Provider, preserved streaming, 30-case benchmark and six-mode real Provider proof are implemented without changing domain Truth ownership | PRODUCT-SHAPE ESSENTIAL / IMPLEMENTED / FOCUSED VALIDATION PASS / REAL PROVIDER PROOF PASS / HUMAN PRODUCT ACCEPTANCE PENDING |
| [Interpretation Externalization / Multimodal Alignment](../architecture/interpretation-externalization-and-multimodal-alignment.md) | Externalize Watt's reconstructed Motive interpretation at the lowest sufficient representation cost so material semantic mismatch can be calibrated | FUTURE CORE DIFFERENTIATION CAPABILITY / NOT CURRENT MVP SCOPE / NOT YET DESIGNED FOR IMPLEMENTATION |
| Production state view | Work, Goal, Attention, Steering, progress, and Work Result projections derive from authoritative Runtime facts | MVP CORE / CLOSED / PASS; real Provider loop and Human acceptance proven |
| Docker integration | PostgreSQL, migration, FastAPI/Uvicorn, API, and Web UI run as one local Compose product; no Provider credential is required | MVP CORE / CLOSED / PASS |
| Trusted Baseline / Active Runtime convergence | Local Docker startup safely synchronizes the exact Trusted checkout, activates Python and static assets from one revision, and exposes explicit activation state/fingerprints | MVP GUARDRAIL / CLOSED / PASS |
| Real local governed Codex E2E | The first real Attempt is preserved as BLOCKED / RECOVERABLE with UNKNOWN Provider Outcome, NONE Production Reality, and 0 / 0 Thread/Turn; container-native Codex state and truthful blocked projection are CLOSED / PASS | MVP CORE / BLOCKED HISTORY PRESERVED; E2E-1B CLOSED / PASS |
| Local persistent Runtime database | Logical spg_dev / spg_test / historical spg_runtime separation exists; the product composition uses only spg_dev | MVP CORE / GUARDRAIL |
| Linux deployment | Candidate checkpoint exists; server bootstrap and promotion validation have not started | POST-LOCAL-MVP |
| Full Guardian / ECF | Extension boundaries and Context Assembly Lite exist; full systems are not integrated | DEFERRED_BY_MVP |

## 4. A. MVP CORE

Only capabilities needed for the product definition are MVP CORE.

| Capability | Narrow MVP Boundary |
|---|---|
| Motive / Work / Engineering Resource representation | Motive as product-facing language; Work as the current internal governed representation; optional Goal aggregation; explicit Engineering Scope binding to repository identity, path/ref, and Baseline |
| Requirement intake | Admit one real task/requirement through the product interface |
| Production Intent / PWU formation | Create one governed Production Intent, one Run, and one-PWU-first plan; explicit Human confirmation is allowed |
| Context Package Lite | Assemble only admitted Source of Truth, exact Baseline, requirement, constraints, and necessary repository context |
| Production Planner Lite | Current narrow AI or deterministic/rule-assisted formation of one admitted production-step plan/PWU; it does not define the full conceptual Plan |
| Reality-driven Plan Steering | Reconstruct and preserve a long-lived Plan from governed Reality, select the next appropriate step, request Human decisions when needed, and create traceable revisions only when Reality justifies change |
| Work Interaction & Closed-loop Refinement | Support continuing natural-language interaction before and during Work; distinguish candidate interpretation from governed truth; admit versioned Work changes; connect feedback to existing Plan reassessment without mutating active production contracts |
| Guided Design Core | Structure applicable design issues, preserve governed results and agenda history, expose one Steering-selected focus and truthful readiness, and form a reviewable proposal without owning production |
| Codex Executor integration | One static Provider profile and one reliable real execution path |
| Run / Attempt execution | Serial execution with one active Run and one current Attempt generation |
| Production State progression | Expose the current governed state and blocking reason |
| Independent Production Observation | Observe repository/artifact Reality independently from Provider claims |
| Basic Completion / Verification | Evaluate explicit Completion obligations and basic repository/test checks |
| Human Attention / Authority | List pending attention; approve, reject, or redirect admitted authority points |
| Repository result handling | Present the resulting change and use governed, non-force repository integration |
| Minimal application/API layer | Cohesive application workflow plus the narrow HTTP surface needed by the UI |
| Functional Web UI | Requirement intake, state view, attention/authority actions, outcome view, and next-task continuation |
| Local Docker integration | API/UI/Runtime database operate as one documented local development product; host-side Executor is temporarily acceptable |
| Local persistent Runtime database | Durable local state with strict Runtime/Test database separation |
| Runtime Activation Lite | Distinguish repository trust from the active process; support an explicit safe local restart for source-only changes and require image rebuild for image/dependency boundaries |

Allowed MVP simplifications are one Engineering Resource per Work, one active Run, serial execution, one-PWU-first workflow, static Provider profile, basic Verification, simple Planner logic, and manual Human intervention for uncommon recovery. These are delivery choices, not permanent architecture constraints. In particular, one-PWU-first constrains current execution; it does not make Work inherently atomic or short-lived.

## 5. B. MVP GUARDRAILS

The following guarantees remain mandatory even when invisible to the user:

1. Exact Production Source Baseline binds every governed execution.
2. Every Attempt uses an isolated workspace.
3. Provider Report is not Production Truth.
4. Production Reality is independently observed.
5. Runtime database and test database remain distinct.
6. Human Authority decisions pass through governed boundaries.
7. Identity, Evidence, and lineage remain traceable across Run, PWU, Attempt, observation, Verification, and result.
8. Git integration never uses blind force, destructive reset, or unobserved ref mutation.
9. Historical Attempts, Provider Reports, observations, and Authority facts remain immutable.
10. Stale Attempt generations cannot regain current authority.
11. Trusted Baseline advancement remains governed and exact.
12. Credentials remain outside domain contracts, transport payloads, and persistence.

Existing stronger guarantees may remain implemented. They do not require exhaustive extension to every edge case before MVP delivery.

## 6. C. DEFERRED_BY_MVP / Phase-2 Hardening Backlog

DEFERRED_BY_MVP means preserved and intentionally removed from the immediate critical path. It does not mean failed, abandoned, or deleted.

| Capability | Current Reality | Why Deferred | MVP Risk Accepted | Architecture Reservation | Phase-2 Trigger |
|---|---|---|---|---|---|
| Complete Verified Maintenance / Production-Lineage Recovery closure | R4-A closed; R4-B implemented with focused/affected evidence; no full-system qualification | Ordinary MVP tasks do not require self-hosted maintenance-lineage promotion | Exceptional baseline drift requires manual governance | Typed recovery capability, migration, evidence, CAS, and supersession semantics remain | Stable Linux host plus repeated self-dogfood baseline drift |
| Real R4-D maintenance recovery execution | Not executed | Historical Windows lineage is archived rather than continued | Old Runtime remains blocked historical evidence | No lineage mutation; later explicit Authority can bind a qualified target | Linux promotion PASS and specific recovery value |
| Cross-host active Runtime handoff | Not implemented | New Linux MVP Runtime can start cleanly | Historical Windows Runtime is not continued on Linux | Runtime identity and export/import boundaries remain separable | Need to continue active work across hosts |
| Execution supervision, heartbeat, and stall handling | Recovery/observation semantics exist; no complete supervisor | Serial MVP can use Human monitoring | Stalls require manual inspection and intervention | Attempt identity, state, fencing, observation, and issue boundaries remain | Repeated unattended long-running executions |
| Semantic execution and post-completion history observability | Current-stage and stopped/blocked projection is implemented; durable post-completion execution history remains limited | Human accepted the bounded development-stage experience | Completed Work history is less legible than live progress | Persisted Steering and production facts remain authoritative | Product Experience work is separately admitted |
| Verification Runtime coverage | Source-level Verification, Runtime activation, and Human acceptance are distinct; browser-served coverage is incomplete | Dogfood #10 supplied bounded Human acceptance | Some served-Runtime behavior remains outside automated Verification | Activation fingerprints and acceptance evidence remain separate | Release/promotion coverage requires it |
| Host capacity leasing / heavy-job scheduler | Not implemented | One active Run and serial execution are sufficient | Human coordinates heavy jobs | Capability/Attempt identity does not assume one scheduler | Concurrent heavy workloads appear |
| Automatic model / capability routing | Not implemented; static binding exists | One Provider path is enough | Manual Provider selection and no optimization | Capability contracts and Runtime Profile remain provider-neutral | Multiple proven Providers require governed selection |
| Token / quota / capacity governance | Not implemented | Not required for first usable product | Operator monitors limits manually | Usage may later attach to Provider/Attempt evidence | Material cost, quota, or starvation incidents |
| Full Continuous Managed Production | Architecture direction only | MVP is user-initiated and Human-governed | No unattended continuous production | Production loop and state contracts remain durable | Stable self-dogfood demonstrates bounded autonomy need |
| Advanced autonomous replanning / supersession | Advanced automation is not implemented; bounded Reality-driven Plan Steering MVP is closed | Optimization and autonomous supersession are not required for the closed Core | Complex autonomous replans remain Human-governed | Plan revisions, supersession, and Authority boundaries remain | Repeated Reality requires advanced automation and a separate contract is admitted |
| Multi-PWU sequential production | PLAN-1A not implemented; Authority review confirmed exact per-PWU Candidate authority and successor Baseline rebinding gap | Structured single-PWU planning closes the current execution need | Independently governed production steps must be narrowed or deferred; the encompassing Work need not be redefined as atomic | Fit classification preserves `MULTI_PWU_REQUIRED`; no successor authority is fabricated | Repeated real Work cannot safely progress through independently governed PWUs and architecture is separately admitted |
| [Duration-aware PWU sizing / capacity-aware production planning](../architecture/duration-capacity-semantic-foundation.md) | DCP-1 CLOSED / PASS; [DCP-2 Production Measurement v0](../architecture/production-measurement-v0.md) IMPLEMENTED / FOCUSED VALIDATION PASS; estimation/scheduling not implemented | Current bounded PWU/Attempt loop is proven | Human and Planner use present fit judgment; measurement has no decision influence | Normalized measurement and TaskShapeSnapshot now exist; estimation, sizing advisory, and capacity ownership remain separated from Authority | Separately admitted estimation/design/implementation slice |
| Multi-project concurrent production | Not implemented | Single/limited project is enough | No portfolio concurrency | Project/repository identity remains explicit | More than one active project is operationally required |
| Executor fleet / remote workers | Not implemented | One host-side Executor is acceptable | No failover or workload distribution | Executor contract remains remote-capable and provider-neutral | Throughput or isolation requires multiple workers |
| Full Guardian integration | Basic Verification and extension point exist | Basic Verification satisfies MVP | Human accepts reduced assurance depth | Assurance contract and ownership remain independent | Regulated/high-risk work or insufficient verification |
| Full ECF | Context Assembly Lite exists | Narrow governed Context is enough | Manual/document-based context curation | Context Provider contract and provenance remain | Context scale/freshness exceeds Lite capability |
| OS/container-level credential isolation | Child allow-list and credential-free SPG transport exist; OS-level isolation is not proven | Product boundary can remain clean with host-side Executor | Host compromise is outside MVP guarantee | Executor infrastructure owns credential resolution | Shared/hostile execution, enterprise security, or remote workers |
| Database role / physical isolation | spg_runtime and spg_test are logically separate in one service | Logical isolation supports local MVP | Shared server/role blast radius accepted locally | Database URLs and lifecycle remain independently configured | Multi-user server, security review, or production promotion |
| HA / disaster recovery | Not implemented | Development server is not an HA production service | Downtime and manual restore accepted | Durable DB and backup format remain standard | Availability objective or production service commitment |
| General backup / restore automation | One verified Windows bootstrap archive exists; no automation | Manual server backup is sufficient initially | Operator error and recovery time accepted | Standard PostgreSQL backup/restore remains available | Repeated backups, server promotion, or recovery exercise |
| Advanced incremental regression selection | Manual focused/affected strategy only | Risk-based validation is sufficient | Selection can miss unforeseen coupling | Test markers and verification basis remain explicit | Suite cost or repeated escapes justify automation |
| Comprehensive audit / Evidence UI | Durable facts exist; no product Evidence UI | Basic status/outcome view comes first | Deep audit requires CLI/DB inspection | Evidence identities and lineage remain queryable | Human governance becomes slow or regulated |
| Advanced multi-user / organization governance | Basic Human Authority model exists; no complete organization model | Initial product can be single-user | No delegated/segregated organizational workflow | Authority identity and role contracts remain explicit | Multiple users or enterprise access requirements |
| Semantic conflict, Production Branch, and merge intelligence | Architecture direction only | Serial one-project flow avoids the need | Semantic conflicts are handled manually | Change/Baseline/Artifact semantics remain compatible | Parallel production paths become real |
| Provider Registry, residency, and enterprise-private profiles | Configuration boundary exists; registry/policy automation does not | Static local profile is sufficient | Provider configuration is manual | Runtime Profile and adapter boundaries remain | Multiple deployments or enterprise residency requirements |

## 7. R4 Reclassification

The accepted state is:

    S6-C2-R4-A
        CLOSED / PASS

    S6-C2-R4-B
        IMPLEMENTED
        FOCUSED / AFFECTED VALIDATION PASS
        ARCHITECTURE LEAD REVIEW PASS

    Full-system R4 regression
        DEFERRED_BY_MVP

    S6-C2-R4-C / S6-C2-R4-D
        DEFERRED_BY_MVP

    Real maintenance recovery
        NOT EXECUTED

The implementation remains available for Phase-2 continuation. The historical Windows Runtime, Attempt generation 1, Recovery Assessment, and Recovery Barrier are not mutated or rewritten.

## 8. Risk-Based Verification Strategy

Verification depth follows change risk rather than a rule that every meaningful change requires a full regression.

| Level | Typical Change | Required Evidence |
|---|---|---|
| L0 | Source of Truth / documentation only | Documentation consistency and Git diff check |
| L1 | Local feature | New/focused tests plus local static/compile checks |
| L2 | Affected subsystem | Focused tests plus affected regression |
| L3 | Shared Runtime invariants or promotion | Affected regression and full deterministic regression where the risk/basis requires it |

Full regression is normally reserved for:

- a core Runtime invariant change where local evidence is insufficient;
- an MVP Release Candidate gate;
- a major local Docker integration promotion;
- Linux server promotion/deployment;
- a later Trusted Release or Trusted Baseline promotion.

Windows full regression is not required to close every intermediate development checkpoint.

## 9. Development Environment Policy

- **ChatGPT + Codex:** remains the MVP development workflow.
- **Local Docker environment:** primary MVP integration and debugging target.
- **Windows workstation:** temporary development host only.
- **Windows-specific hardening:** an MVP blocker only when it affects Docker-integrated MVP use.
- **Linux development server:** deployment target after local MVP completion.
- **Self-dogfood:** Dogfood #9/#10 already prove machine and Human-operated Core loops; systematic post-Core use remains governed separately from Linux promotion.
- **Provider placement:** a host-side Executor is temporarily acceptable if the product boundary stays clean and the Docker-integrated MVP is reliable. Complete containerization of every Provider component is not required.

## 10. MVP Web UI Boundary

The functional Web UI supports:

- view all Works or select an optional Goal context;
- enter a natural-language Work with optional Goal and tags;
- view the Work draft, Engineering Scope summary, product state, and blocking reason;
- refine, approve, reject, or request refinement through governed API actions;
- automatically progress legal non-Human production transitions after approval;
- view and resolve API-provided Human Attention actions;
- view truthful artifact, Verification, trusted-result, and remaining-risk projections;
- continue with another independent Work.

Motive is the product-facing concept; the current UI/API still uses the
internal name Work. This documentation calibration does not rename routes,
identifiers, domain types, or screens. UI polling observes server-side progress
and never causes production transitions. The UI does not
introduce a Project aggregate root, Project selector, Chat Thread authority, or
browser-side production state machine. Manual single-step Advance remains a
non-primary technical/operator fallback.

The MVP server uses one bounded in-process Production Orchestrator. Human Work
Draft Approval and exact Candidate Authorization remain mandatory. Distributed
scheduling, Worker Fleet, durable recovery, Provider retry/Resume, and
policy/risk-driven automatic Candidate integration are DEFERRED_BY_MVP.

A conversational interaction style is acceptable and preferred where it keeps the workflow simple.

The MVP does not require visual polish, complex dashboards, drag-and-drop workflow editing, agent animation, advanced analytics, or multi-user collaboration.

Trusted repository completion must not be presented as active product behavior
until Runtime activation evidence converges. Human Product Acceptance remains a
separate fact. Browser/runtime-served acceptance automation is not added by
Runtime Activation Lite; the current `VERIFICATION_RUNTIME_COVERAGE_GAP` remains
an evidence-backed follow-up rather than hidden success.

## 11. Reordered MVP Roadmap

1. **MVP Scope Calibration** — CLOSED / PASS; this document.
2. **Goal-centric governed Work application flow** — CLOSED / PASS; connects requirement intake, Engineering Scope/resource identity, Production Intent/PWU formation, existing Runtime operations, status projection, and Human Attention/Authority actions.
3. **Minimal HTTP API** — CLOSED / PASS; exposes only the application commands and queries needed by the product.
4. **Functional Web UI** — CLOSED / PASS.
5. **Local Docker integration** — CLOSED / PASS. PostgreSQL, migration, API, and UI are composed without requiring a Provider credential.
6. **Real local end-to-end MVP task** — CLOSED / PASS for the admitted MVP proof. MVP-E2E-1A and MVP-E2E-1D remain immutable blocked historical evidence. MVP-E2E-1B and MVP-E2E-1E closed the container state and sandbox blockers. MVP-E2E-1G/1H proved the first complete governed Watt production loop; MVP-E2E-1I proved restart readiness; a second Work proved continuous production from the prior Trusted Baseline. Later Intake Dogfood reached same-intent trusted completion, while ORCH Dogfood #1 truthfully exposed a Verification Contract mismatch rather than manufacturing success.
7. **Production Orchestration Lite** — CLOSED / PASS; server-side bounded automatic progression stops at Human Attention, BLOCKED, or COMPLETED.
8. **Single-PWU Production Planner Intelligence Lite** — CLOSED / PASS; multi-PWU production remains deferred.
9. **Bounded Single-PWU Code Work** — CLOSED / PASS; adds Human-visible bounded change authority and typed contract-driven code Verification without changing the one-PWU model.
10. **Trusted Baseline / Active Runtime Convergence Lite** — CLOSED / PASS; Architecture Lead Reality Review and Human Composer acceptance passed. The first trusted Watt code self-dogfood loop is proven.
11. **Reality-driven Plan Steering** — MVP CLOSED / PASS. Slices 1C through 1L close the reconstructable truth spine, governed decisions and semantic execution, automatic progression, exact SPG production bridge, strict real-Provider contract, and long-lived completion semantics. Dogfood #9 proves the machine-side production loop through Runtime Commit and COMPLETE; Dogfood #10 proves Human-operated acceptance and exact activation. Extended Human Attention and Product Experience remain separately gated.
12. **Historical Watt MVP Core Closure** — CLOSED / PASS for the proved Governed Production + Reality-driven Plan Steering Core; see [closure evidence](../evidence/mvp-core-closure.md). This does not close Watt Product MVP.
13. **Product North Star / WIC-1 Architecture** — CLOSED / PASS for architecture definition.
14. **WIC Slice 1 — Interaction Truth Spine & Pre-Work Understanding** — IMPLEMENTED / PASS. Multi-turn real Provider evidence advances `NOT_READY -> READY` while Work and production facts remain zero.
15. **WIC Slice 2 — Governed Work Admission & Interaction Continuity** — IMPLEMENTED / PASS. Exact current `READY` assessment plus explicit Human Authority creates one Work Reality revision #1, admitted scope/governance, same-Interaction focus, and existing long-lived Steering bootstrap with zero production facts.
16. **WIC Slice 3 — Active Work Evolution, Focus Preservation, Feedback & Plan Reassessment** — IMPLEMENTED / PASS. Active input is classified against exact governed Reality; only Human approval appends revision N+1; old production bindings remain immutable; the latest revision enters existing Plan Steering through `PlanFrame`.
17. **WIC Slice 4 — Work Satisfaction, Continuation & New Work Transition** — IMPLEMENTED / PASS. Exact trusted completion projects `CURRENTLY_SATISFIED + OPEN`; same-Motive continuation uses existing revision/Steering; new demand creates a persisted Human-governed formation transition without automatic Work, Authority, or production facts. WIC Core is CLOSED / PASS.
18. **Duration/capacity semantic foundation** — DCP-1 CLOSED / PASS and DCP-2
    Production Measurement v0 IMPLEMENTED / FOCUSED VALIDATION PASS; estimation,
    queue, scheduling, and runtime capacity behavior require separate admission
    and do not reopen Core.
19. **Human–Watt Collaboration and Guided Design Facilitation** — IMPLEMENTED / FOCUSED VALIDATION PASS / REAL PROVIDER V2.2 PROOF PASS / HUMAN PRODUCT ACCEPTANCE PENDING. Adds persisted conversation/Turn experience, bounded asynchronous processing, SSE delivery, a three-schema seed registry, schema matching, design-stage/focus guidance, restart reconstruction, and direct-answer-first progressive Human-facing responses without changing WIC/Plan/SPG truth ownership. Four representative response-quality scenarios passed with `gpt-5.6-sol`; deterministic evidence remains distinct from that real proof and from Human Product Acceptance.
20. **Human–Watt Conversation Intelligence** — IMPLEMENTED / FOCUSED VALIDATION PASS / REAL PROVIDER PROOF PASS / HUMAN PRODUCT ACCEPTANCE PENDING. Separates WIC/domain collaboration semantics from bounded context assembly and a dedicated configurable Human-facing Provider; preserves streaming/persistence and truth ownership; establishes a reusable 30-case benchmark and passes six mandatory real scenarios.
21. **Human WIC Product Dogfood** — separately admit and exercise the full formation/admission/evolution/satisfaction/new-direction journey.
22. **Watt Product MVP closure reassessment** — only after real Human WIC evidence.
23. **Necessary UI / Product Experience work** — improve observability and history within an admitted boundary.
24. **Deployment readiness and promotion validation** — risk-based gates for the accepted checkpoint.
25. **Linux server deployment and promotion** — bootstrap and validate from an exact accepted candidate.
26. **Phase-2 hardening and systematic post-Core dogfood** — activate from evidence and triggers, not architectural interest alone.

Detailed implementation slices after Step 1 require separate Architecture Lead admission.

MVP-DOCKER-1 Attempt #1 is preserved as **BLOCKED — HOST_DOCKER_UNAVAILABLE / IMPLEMENTATION NOT STARTED / FILE CHANGES 0**. Attempt #2 started after Human confirmation that Docker Desktop / Linux Engine was available and does not rewrite that historical blocker.

## 12. MVP Scope Firewall

Task admission follows:

    Does this directly advance the usable MVP?
        YES -> eligible

    NO
        Is it a hard MVP blocker or required MVP Guardrail?
            YES -> eligible

    NO
        DEFERRED_BY_MVP

Robustness, recovery, scale, optimization, and security work does not enter the MVP critical path merely because it is architecturally valuable. Existing implementations are preserved; new work requires direct MVP value, blocker evidence, or a Phase-2 trigger.

## 13. Next Slice Selection Boundary

Architecture Lead selects each concrete slice separately. Governed Production,
Reality-driven Plan Steering, and Work Interaction & Closed-loop Refinement
Cores remain **CLOSED / PASS**. Human WIC Product Dogfood and Product-MVP closure
reassessment require separate authorization. Watt Product MVP remains **NOT
CLOSED**. This calibration introduces no Project
Governor, Initiative, Multi-PWU execution, or Phase-2 automation.
