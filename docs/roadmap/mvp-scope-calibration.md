# MVP Scope Calibration and Phase-2 Hardening Backlog

## 1. Status and Authority

This document is the authoritative MVP delivery calibration under Architecture Baseline v0.1.

It changes roadmap priority, not the confirmed Runtime semantics or ownership boundaries. Existing R4-A and R4-B implementation remains intact. No product feature, Provider execution, production migration, Runtime mutation, or deployment is introduced by this document.

The immediate priority is:

> Complete a usable SPG / TNGA MVP with a functional Web UI, integrate and debug it in the local Docker development environment, deploy the completed MVP to a stable Linux development server, and only then begin systematic self-dogfooding.

The MVP development workflow remains Human Governor + ChatGPT Architecture Lead + Codex repo-grounded Executor.

## 2. MVP Product Definition

The MVP is usable when a user can:

1. Run the product locally in the intended Docker development environment.
2. Open a functional Web UI.
3. View all Works or select an optional Goal navigation context.
4. Submit a real software-development requirement.
5. Observe the admitted Production Intent, Run, PWU, Attempt, and governed status.
6. Respond to required Human Attention and Authority actions.
7. Observe execution, independent production observation, Completion, and Verification outcomes.
8. Obtain the resulting repository development outcome.
9. Continue with another task.

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
| Web UI | Same-origin FastAPI-served Goal / Work Control Room implements intake, refinement/admission, one-step advance, Attention, and truthful Work Result views | MVP CORE / IMPLEMENTED; focused validation pass; Architecture Lead review pending |
| Goal / Work / Engineering Scope product model | Work is the user-facing organization unit; Goal is an optional weak aggregation; Engineering Resources bind through explicit Engineering Scope | MVP PRODUCT MODEL / IMPLEMENTED |
| Production Planner | Architecture and contracts exist; no complete product-facing Planner workflow | PARTIAL / MVP GAP |
| Production state view | Work, Goal, Attention, and Work Result projections derive from authoritative Runtime facts | PARTIAL / HTTP API AND UI GAP |
| Docker integration | PostgreSQL Compose service exists; application, API, UI, and host-side Executor integration are not composed as one development product | PARTIAL / MVP GAP |
| Local persistent Runtime database | Logical spg_runtime / spg_test separation exists | MVP CORE / GUARDRAIL |
| Linux deployment | Candidate checkpoint exists; server bootstrap and promotion validation have not started | POST-LOCAL-MVP |
| Full Guardian / ECF | Extension boundaries and Context Assembly Lite exist; full systems are not integrated | DEFERRED_BY_MVP |

## 4. A. MVP CORE

Only capabilities needed for the product definition are MVP CORE.

| Capability | Narrow MVP Boundary |
|---|---|
| Goal / Work / Engineering Resource representation | Optional Goal aggregation; Work as the primary product object; explicit Engineering Scope binding to the configured repository identity, path/ref, and Baseline |
| Requirement intake | Admit one real task/requirement through the product interface |
| Production Intent / PWU formation | Create one governed Production Intent, one Run, and one-PWU-first plan; explicit Human confirmation is allowed |
| Context Package Lite | Assemble only admitted Source of Truth, exact Baseline, requirement, constraints, and necessary repository context |
| Production Planner Lite | Simple AI or deterministic/rule-assisted formation of a plan/PWU; no advanced autonomous replanning |
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

Allowed MVP simplifications are one Engineering Resource per Work, one active Run, serial execution, one-PWU-first workflow, static Provider profile, basic Verification, simple Planner logic, and manual Human intervention for uncommon recovery. These are delivery choices, not permanent architecture constraints.

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
| Host capacity leasing / heavy-job scheduler | Not implemented | One active Run and serial execution are sufficient | Human coordinates heavy jobs | Capability/Attempt identity does not assume one scheduler | Concurrent heavy workloads appear |
| Automatic model / capability routing | Not implemented; static binding exists | One Provider path is enough | Manual Provider selection and no optimization | Capability contracts and Runtime Profile remain provider-neutral | Multiple proven Providers require governed selection |
| Token / quota / capacity governance | Not implemented | Not required for first usable product | Operator monitors limits manually | Usage may later attach to Provider/Attempt evidence | Material cost, quota, or starvation incidents |
| Full Continuous Managed Production | Architecture direction only | MVP is user-initiated and Human-governed | No unattended continuous production | Production loop and state contracts remain durable | Stable self-dogfood demonstrates bounded autonomy need |
| Advanced autonomous replanning / supersession | Semantics partly exist; automated intelligence is not complete | One-PWU-first and Human redirection are enough | Complex replans are manual | Plan revisions, supersession, and Authority boundaries remain | Frequent multi-step divergence or replanning |
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
- **Systematic TNGA self-dogfood:** begins only after the usable MVP is deployed and promotion-validated on the stable Linux server.
- **Provider placement:** a host-side Executor is temporarily acceptable if the product boundary stays clean and the Docker-integrated MVP is reliable. Complete containerization of every Provider component is not required.

## 10. MVP Web UI Boundary

The functional Web UI supports:

- view all Works or select an optional Goal context;
- enter a natural-language Work with optional Goal and tags;
- view the Work draft, Engineering Scope summary, product state, and blocking reason;
- refine, approve, reject, or request refinement through governed API actions;
- advance exactly one bounded production action per explicit interaction;
- view and resolve API-provided Human Attention actions;
- view truthful artifact, Verification, trusted-result, and remaining-risk projections;
- continue with another independent Work.

Work remains the primary user-facing product object. The UI does not introduce a Project aggregate root, Project selector, Chat Thread authority, browser-side production state machine, or automatic run-until-done behavior.

A conversational interaction style is acceptable and preferred where it keeps the workflow simple.

The MVP does not require visual polish, complex dashboards, drag-and-drop workflow editing, agent animation, advanced analytics, or multi-user collaboration.

## 11. Reordered MVP Roadmap

1. **MVP Scope Calibration** — CLOSED / PASS; this document.
2. **Goal-centric governed Work application flow** — CLOSED / PASS; connects requirement intake, Engineering Scope/resource identity, Production Intent/PWU formation, existing Runtime operations, status projection, and Human Attention/Authority actions.
3. **Minimal HTTP API** — CLOSED / PASS; exposes only the application commands and queries needed by the product.
4. **Functional Web UI** — implemented with focused validation pass; Architecture Lead Reality Review pending.
5. **Local Docker integration** — compose API/UI/Runtime DB; integrate the temporary host-side Executor cleanly.
6. **Real local end-to-end MVP task** — submit, govern, execute, observe, verify, authorize, and obtain a repository result.
7. **MVP closure and promotion validation** — risk-based affected evidence plus full deterministic regression at the justified release gate.
8. **Linux server deployment** — bootstrap from an exact accepted candidate.
9. **Linux promotion validation** — run the server promotion gate and operational checks.
10. **Begin systematic self-dogfood** — only after a usable promoted MVP exists.
11. **Phase-2 hardening** — activate deferred items from evidence and triggers, not architectural interest alone.

Detailed implementation slices after Step 1 require separate Architecture Lead admission.

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

Architecture Lead selects each concrete slice separately. The first eligible implementation slice should create the narrow application-level workflow for one project and one governed task. It should reuse existing Runtime services rather than introduce UI, deployment, advanced Planner intelligence, or Phase-2 hardening in the same slice.
