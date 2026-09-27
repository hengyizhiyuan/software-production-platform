# Lifecycle and Action Admission Semantics

Lifecycle/authority contract, version `lifecycle-action-admission-v1`, 2026-09-27.
Human-language compilation, positive action binding and Search routing are now
owned by the [Intent Realization Kernel](intent-realization-kernel/README.md).
Historical raw-text routes in this document are non-canonical; the lifecycle and
authority validators below remain the qualified downstream owners.

Lifecycle state is evidence about one subject; it does not grant or prohibit every action. An existing owner admits each proposed action using explicit intent, current resource authority, capability, required credential, side-effect class, and observed Reality. Work admission is required for production planning and mutation; independently authorized repository acquisition and inspection do not manufacture production Work. Incomplete future Product Intent must not erase a present explicit command.

## Owners, persisted states, transitions and projections

The exhaustive enum census is [lifecycle-state-census-20260927.json](../evidence/lifecycle/lifecycle-state-census-20260927.json). The following map uses actual persistence names, including non-enum states; arrows describe owner-controlled transitions, not permissions.

| Subject / owner | Persisted state and transitions | Human-facing projection |
| --- | --- | --- |
| Interaction / WorkInteractionService | Interaction OPEN → ARCHIVED; turn RECEIVED → PROCESSING → COMPLETED or FAILED | Conversation, current turn and durable response/SSE events |
| Prospective Work / WorkApplicationService + production admission | WorkCondition PRE_WORK → DRAFT / NEEDS_REFINEMENT → AWAITING_APPROVAL → READY, or REJECTED / DISCARDED | Understanding and admitted revision remain separate from repository facts |
| Repository / RepositoryAssetService + GitRepositoryAcquirer | repository_intakes.observation REQUESTED → RUNNING → READY, FAILED_RETRYABLE, FAILED_TERMINAL or WAITING_FOR_AUTHORIZATION | Source, local ref, exact revision/tree, resource and Product identity; no claim of Work admission |
| Product / ProductAssetService | Long-lived Product asset attachments and current baseline; successive independent Work bindings | Product continuity survives individual Work completion |
| Work planning / Steering owner | Persisted Steering steps REFINE / HUMAN_DECISION / DESIGN → PRODUCE → VERIFY_ACCEPT → COMPLETE, with legitimate refinement / stop paths | Current governed step and evidence, separate Human attention |
| PWU / Native Executor and Production Environment | Queue QUEUED / WAITING_RESOURCE → EXECUTING; attempt runtime RUNNING / PAUSING → RECONCILING / RESUME_REQUESTED or terminal outcome | Queue, lease, attempt, environment and checkpoint facts |
| Candidate / Production owner | baseline_candidates.sealed_at records seal after production and Join | Exact Candidate identity; sealing alone does not establish review readiness |
| Preview / CandidatePreviewService | PreviewRuntimeStatus CREATED → PREPARING → READY or FAILED / STOPPED; provider probe and served verification independently required | PREVIEW_PREPARING while owner is preparing; no review-ready claim before required verification |
| Human review / existing attention + governance owners | Pending exact Candidate authorization → authorized / rejected / corrected; delivery acceptance persisted independently | Human action only for a real decision, authority, target ambiguity or unavailable credential |
| Remote delivery / GitHubDeliveryService | remote_delivery_authorizations + remote_delivery_receipts; accepted manifest and authorization precede actual push receipt | Authorization, execution and observed remote success are distinct |
| Work convergence / existing SelfConverge and SelfRefine owners | Boundary recovery evidence and lifetime budgets; WorkStatus RUNNING / NEEDS_ATTENTION / BLOCKED / COMPLETED | Local recovery cannot erase missing downstream obligations; completed history remains inspectable |

No new coordinator, action manager or refinement engine owns these transitions. Domain `action_admission.py` supplies policy values to existing owners. Existing Task Contract, Candidate, Preview, Work convergence and delivery checks remain authoritative. A policy decision is not an execution receipt.

## Action families and side effects

Reuse existing `SideEffectLevel` and Connector capabilities. `READ` means read/query/research; `WORKSPACE_MUTATION` covers local effects and requires **additional production intent and Work/Task authority** when the action is production modification. It never collapses reversible clone and production mutation into the same permission. `EXTERNAL_WRITE` requires explicit remote governance. `DESTRUCTIVE` requires release/destructive governance. No merge, deployment or destructive executor is introduced by this task.

| Family | Real actions / owning boundary | Side effect and additional obligation |
| --- | --- | --- |
| INSPECT / RESEARCH | Repository file/ref/tree, Product/Work history, GitHub/Web source research | READ; explicit scope and resource authority; Search does not imply clone |
| ACQUIRE_REPOSITORY / LOCAL_BRANCH | Existing repository intake and isolated local branch materialization | WORKSPACE_MUTATION; exact persisted Human command, current actor authority, capability, source Reality; no remote mutation |
| PREPARE / PLAN / PRODUCE | Isolated dependency/runtime preparation for Work, Task Contracts, PWU and Join | WORKSPACE_MUTATION / READ planning; sufficient production intent, admitted Work and Task authority |
| VERIFY | Build/test/lint/probe/assurance through existing verification owners | Local execution authority and exact target; testing alone does not grant acceptance or served-runtime readiness |
| PREVIEW | Candidate environment and served verification | Local reversible environment; exact Candidate and preview obligation; automatic owner action before Human review |
| HUMAN_ACCEPTANCE | Clarification, exact Candidate decision, correction, credential provision | Human decision; required Preview must be verified; acceptance grants no remote effect |
| DELIVERY / RELEASE | Governed push / PR and sensitive release interfaces | EXTERNAL_WRITE / DESTRUCTIVE; exact accepted Candidate, current resource write authority, credential and separate explicit Delivery Authorization |
| NEW_WORK | New production intent against the same Product/current baseline | New admission process; old Work COMPLETED does not freeze Product |

## Versioned lifecycle × action matrix

[Executable matrix](../../benchmarks/golden/lifecycle-action-matrix-v1.json) contains all 13 families across 16 real state slices. Rows assume explicit intent, authority, capability and any required credential are independently satisfied. Removing authority blocks every cell, regardless of lifecycle. A terminal acquisition only stops that acquisition; it does not stop unrelated history reads or a new Work. The executable policy test verifies every cell and authority negation.

Classification vocabulary: AUTO_ALLOWED, ALLOWED_IF_EXPLICIT, ALLOWED_IF_AUTHORIZED, REQUIRES_HUMAN, REQUIRES_WORK_ADMISSION, REQUIRES_CANDIDATE, REQUIRES_ACCEPTANCE, REQUIRES_DELIVERY_AUTHORIZATION, BLOCKED, SELF_REFINE_FIRST. ALLOWED_IF_AUTHORIZED describes remote governance; existing delivery owners still verify the persisted authorization rather than accepting a caller-supplied boolean. AUTO_ALLOWED does not create authority; it identifies an existing system obligation.

| Observed state | Inspect / acquire | Local branch | Produce | Preview | Delivery |
| --- | --- | --- | --- | --- | --- |
| WorkCondition.PRE_WORK | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | SELF_REFINE_FIRST | REQUIRES_WORK_ADMISSION | REQUIRES_CANDIDATE | REQUIRES_CANDIDATE |
| RepositoryAcquisitionState.RUNNING | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | SELF_REFINE_FIRST | REQUIRES_WORK_ADMISSION | REQUIRES_CANDIDATE | REQUIRES_CANDIDATE |
| RepositoryAcquisitionState.READY | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | REQUIRES_WORK_ADMISSION | REQUIRES_CANDIDATE | REQUIRES_CANDIDATE |
| WorkStatus.READY | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | REQUIRES_CANDIDATE | REQUIRES_CANDIDATE |
| SteeringStepType.DESIGN | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | REQUIRES_CANDIDATE | REQUIRES_CANDIDATE |
| QueueCondition.EXECUTING | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | REQUIRES_CANDIDATE | REQUIRES_CANDIDATE |
| baseline_candidates.sealed_at | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | SELF_REFINE_FIRST | ALLOWED_IF_EXPLICIT | REQUIRES_ACCEPTANCE |
| PreviewRuntimeStatus.PREPARING | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | SELF_REFINE_FIRST | ALLOWED_IF_EXPLICIT | REQUIRES_ACCEPTANCE |
| PreviewRuntimeStatus.READY + served verification | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | SELF_REFINE_FIRST | ALLOWED_IF_EXPLICIT | REQUIRES_ACCEPTANCE |
| ProductionDeliveryState.ACCEPTED | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | REQUIRES_WORK_ADMISSION | ALLOWED_IF_EXPLICIT | REQUIRES_DELIVERY_AUTHORIZATION |
| ProductionDeliveryState.AUTHORIZED_FOR_DELIVERY | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | REQUIRES_WORK_ADMISSION | ALLOWED_IF_EXPLICIT | ALLOWED_IF_AUTHORIZED |
| WorkStatus.COMPLETED | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | ALLOWED_IF_EXPLICIT | REQUIRES_WORK_ADMISSION | ALLOWED_IF_EXPLICIT | REQUIRES_DELIVERY_AUTHORIZATION |
| RepositoryAcquisitionState.FAILED_RETRYABLE | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | SELF_REFINE_FIRST | REQUIRES_WORK_ADMISSION | REQUIRES_CANDIDATE | REQUIRES_CANDIDATE |
| RepositoryAcquisitionState.FAILED_TERMINAL | ALLOWED_IF_EXPLICIT / BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| WorkCondition.NEEDS_REFINEMENT | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | SELF_REFINE_FIRST | REQUIRES_WORK_ADMISSION | REQUIRES_CANDIDATE | REQUIRES_CANDIDATE |
| SteeringAutomaticProgressionState.STOPPED | ALLOWED_IF_EXPLICIT / ALLOWED_IF_EXPLICIT | SELF_REFINE_FIRST | REQUIRES_WORK_ADMISSION | REQUIRES_CANDIDATE | REQUIRES_CANDIDATE |

## Explicit action, authority and persistence

Repository command witnesses are extracted from the persisted Human record, not a model promise. Negation, vague future intent, search for alternatives, instructions explaining an operation, branch-status questions and ambiguous multiple targets do not become local execution authority. Clone and later undefined modification are separate clauses. Current actor membership/resource ownership are checked again at execution in authenticated runtime; credential presence and Connector capability cannot replace these checks. A branch base must be a READY resource from the same Interaction. Idempotent identities derive from the exact source record, operation, branch and bounded attempt number. Product/repository continuity can exist without admitted Work. An initial PRE_WORK placeholder, if present, remains unadmitted.

## Human attention, refinement and convergence

A known target with an explicit preparatory command needs no production-start button. A genuinely ambiguous target needs one clarification. Missing non-recoverable authorization/credential remains a real Human dependency. Deterministic preview preparation, PWU progression and ordinary repair belong to existing owners.

Repository network failure retries automatically at most three attempts, each Git clone bounded at 90 seconds, backoff 1/2/4 seconds, and a 300-second per-invocation budget. Persisted attempt count survives restore; terminal/auth failures never automatically retry. Exhausted retryable attempts remain honestly failed/resumable under a new legitimate request, rather than successful. Existing WIC RESPONSE_REFINEMENT records scope INTERACTION_ACTION_ONLY, actual attempt count, evidence reference, final condition and work_converged=false. Repeated restore is idempotent. No fake Work or duplicate refinement framework is created.

Policy signals include ACTION_NOT_EXPLICIT, ACTION_AUTHORITY_MISSING, ACTION_REQUIRES_WORK_ADMISSION, ACTION_REQUIRES_CANDIDATE, ACTION_REQUIRES_HUMAN_ACCEPTANCE, ACTION_REQUIRES_DELIVERY_AUTHORIZATION, ACTION_SIDE_EFFECT_CLASS_MISMATCH, ACTION_ALREADY_COMPLETED, ACTION_RETRYABLE and ACTION_TERMINAL. Authority failure independently covers capability-present and credential-present cases. REPOSITORY_REALITY_REQUIRED and PREVIEW_NOT_VERIFIED represent bounded owner refinement. Incorrect gate and projection defects are protected through contract/Reality mismatch tests; they do not require duplicate global event enums. No diagnostic signal is itself authority.

Work-level SelfConverge continues to evaluate every current boundary, exact Candidate, served runtime and downstream obligations. A repository or Executor recovery cannot establish global Work completion. Lifetime/no-progress budgets cannot be reset by a different candidate or boundary.

## Projection and delivery invariants

Conversation PRE_WORK, repository READY, known Product and production NOT STARTED can coexist. API/SSE shared understanding carries repository_observation independently of production evidence. UI shows exact source/ref/revision/tree, Product continuity and an inspectable source tree; no global understanding label erases repository readiness. Candidate SEALED plus Preview PREPARING projects owner preparation before Human review. READY still requires provider health and served verification. Historical Work/Evidence remains readable after completion.

Work admission never authorizes push. Human Acceptance never authorizes push. Delivery Authorization never proves a successful remote effect: the existing delivery owner rechecks exact accepted manifest, actor, current write grant, required credential and compare-and-swap remote baseline, then retains the actual execution receipt.

## Semantic gate audit

| Boundary | Decision |
| --- | --- |
| response_contract production_request | Corrected clone/pull lexical conflation: preparatory command is independent of actual production-effect verbs. Compound explicit production modification remains production intent. |
| WorkInteractionService / repository assets | Corrected no governed Work → no repository action; independent command receipt path remains in existing owner. |
| Shared understanding / app / Product readiness | Corrected admitted revision-only source projection and action-request-as-production UI shortcut. Repository source/Product facts now persist independently. |
| ControlRoom diagnosis | Corrected sealed manifest pending acceptance → waiting Human while required Preview prepares; preparation precedes Human attention. |
| Native execution / production admission / Task Contract | Retained Work-required guards: they govern production mutation, planning or Work-scoped evidence. |
| CandidatePreviewService review readiness | Retained exact Candidate, verification and served runtime prerequisites; automated prepare_review remains independent of Human Acceptance. |
| GitHubDeliveryService | Retained credential/read grant/write grant/current actor/accepted manifest/separate authorization/remote CAS; domain policy supplements these checks. |
| ProductAssetService / Work history | Retained Product continuity and fresh Work admission; no COMPLETED-product freeze. |
| SelfRefine / SelfConverge | Retained local outcome versus global boundary/lifetime convergence distinction. |

Qualification uses frozen baseline evidence, unchanged original Tier-0 requirements, new GC-LC-01…15, actual authenticated `/app` journeys, PostgreSQL/Git/container boundaries, and full regression. Real Web Search and GC-EX-12 remain BLOCKED_EXTERNAL until SPG_WEB_SEARCH_API_KEY is supplied; [live qualification entry and evidence](../operations/web-search-live-qualification.md) remain mandatory. Historical FSI attempts and volume evidence are immutable.

### Expression-only structured repair

The existing DeepSeek Governed Response Realizer reuses the same one-attempt structural repair helper as other structured Provider boundaries. It keeps the admitted envelope and existing Human-facing meaning, emits no second provisional stream, and rejects exhausted repairs. A valid repaired realization records existing WIC RESPONSE_REFINEMENT with scope EXPRESSION_ONLY and work_converged=false. A successfully running Work and a failed expression are independent facts; repairing expression cannot replay production or grant authority.

### Qualification fault frontier

A Worker-loss trial must freeze the declared process before verifying a settled checkpoint and a running inference. Read-then-kill can race into the next write. Such an uncertain-effect cut is retained as unqualified fault evidence; it must remain fenced. Qualification never clears uncertainty or manually resumes an unknown write. Independent Golden trials use isolated source identities or run sequentially before accepting a shared Product baseline.

Historical Work questions reuse the existing read-only Work Reality query owner. Persisted repository observations, verification results and exact local Trusted Runtime Commit are the answer basis; completed lifecycle state neither removes these receipts nor causes a model to treat absent conversation prose as absent production. The query creates no Work, revision, production cycle or remote authorization.
