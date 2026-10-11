# Human-triggered Watt Work Trace investigation v1

## Baseline and purpose

Independent branch `codex/watt-trace-self-analysis`, starting at stable Admin
export/deployment baseline `5de657f3cb65780adf50f6557b54171a6c3cfae5`. No C3 source,
temporary fix, qualification environment, canonical main or production container
is changed. This feature produces advisory engineering reports. It cannot create
an Evolution Work, modify code, authorize a Candidate, deploy or self-upgrade.

## Capability inventory before implementation

| Existing component | Reuse | Missing capability / limit |
| --- | --- | --- |
| WorkRegistryService / original Work Owners | Exact Work ownership, state, objective and lineage | Productless historical ownership cannot be invented |
| ProductionTraceService / diagnostic exporter | Bounded, redacted, source-referenced historical snapshot | Nonatomic cross-owner capture; raw failed model text and some historic receipts may be absent |
| ContextOrchestrator / TaskContractBuilder | INVESTIGATION activity, source basis, scope, expectations and provenance | No registered self-analysis READY ECF policy; this is not a new production admission |
| NativeContextAssembler | Contract, SourceVector, envelope, working plan, receipts and repair feedback | Existing context byte limits may prevent a complete investigation |
| NativeExecutorKernel / configured inference adapter | Actual Watt inference/tool/checkpoint loop and bounded rejection retry | No report artifact verification or historical evidence adapters |
| NativeToolRegistry / GitExactReality | Explicit grants and exact committed source reads | Non-built-in definitions hit an uninitialized connector reference; fixed with a null guard |
| Native evidence / ContentAddressedStorage | Typed tool results, digests, checkpoints and immutable artifacts | Admin needed request/report retrieval and authorization |
| Original Verification / Guardian / Self-Refine Owners | Evidence consumed as original Owner records | Their historical outcomes do not verify the new report's causal claims |

## Minimal implementation boundary

Human selects a completed, failed, blocked or stopped Work and submits a purpose.
The service authorizes the exact Work before capture or inference, fixes one full
export snapshot, resolves committed repository evidence, assembles cognitive
context and an INVESTIGATION Task Contract, then invokes the existing Native
Kernel. The model reconstructs Work understanding, investigates evidence and
implementation, classifies problems, plans recommendations and submits a typed
report. These phases occur in the existing working-plan/inference/tool loop;
there is no second chat-model client or independent reasoning engine.

This deliberately does not create a production Work. Ephemeral binding/PWU/session
identifiers scope the investigation kernel and its evidence; they are never
inserted into Work, Steering, production Runtime, queue or admission Owners.
The writable Native mount represents the adapter's private artifact store. No
filesystem/process/write/deployment capability is granted to the model.

The original Work/IRK/ECF/context/contract/verification/refinement records are read
as evidence, rather than replayed as current production authority. The standard
Task Contract builder receives the actual source-snapshot fingerprint as its
source basis. A registered READY ECF package, production IRK admission and Guardian
qualification are explicitly **not** claimed. Reuse of local context assembly
does not qualify a new governed ECF surface. Future production/evolution admission
must use the existing Work/Steering/ECF owners and would require separate review.

## Evidence and tools

`evidence.index/read` reference immutable snapshot records by deterministic UUID,
JSON pointer, content digest and original source reference. Projection counts
are labelled as projections, not unique tool/model totals. Paging retains unknown
timestamps and exporter truncation/redaction/nonatomic warnings.

`repository.read/search/diff` use fixed service-admitted Git object identities,
never model-supplied revisions or local dirty files. Runtime source uses configured
active source root/revision or repository root/exact HEAD; unavailable Git evidence
stays unavailable. Runtime source is labelled with its actual revision and cannot
prove that a historical Worker used that revision. Work source paths resolve from
authorized `work_source_bases -> engineering_resources`; matching Candidate object
identities permit read-only change inspection. No fetch, checkout or repository
mutation is performed. Read scopes exclude hidden, credential/secret and Holdout
paths, with blob/search/diff caps and existing credential text redaction. Missing
objects become explicit limitations. A server must supply readable exact Git
objects for useful implementation-level grounding; an installed Python package
alone is insufficient.

`analysis.submit` checks report schema, Work identity, unique findings, recommendation
lineage, class/handling consistency, observed evidence UUIDs, exact quotes in
actually returned excerpts (including bounded index snippets, never unread body)
and repository provenance for root cause hypotheses.
Rejected report drafts are retained by digest and can be read through
`evidence.read(draft_id)`. They are labelled MODEL_PROPOSAL_NOT_OWNER_EVIDENCE and
cannot be cited as historical observations. Bounded explicit remove/replace edits
through `analysis.revise` rerun every gate. Citation verification returns up to
12 failures together; exact decoded JSON string fragments are accepted only when
their exact encoded fragment was actually returned. Original failed step/receipt
or Self-Refine records require at least one finding citing an original incident
Owner. This coverage check does not prove incident completeness or semantic truth.
Public tool schemas declare the report structure and actual paging limits.
Failure is a no-external-effect receipt returned through Native Kernel's existing
bounded refinement mechanism. Final RESULT_READY must name the successfully
verified report digest. An arbitrary model terminal claim cannot publish a report.

The verifier proves citation and structure integrity only. It does not prove that
the natural language assertion follows from its quotation. Facts are model-written
summaries of cited observations; causal analyses remain ROOT_CAUSE_HYPOTHESIS or
UNKNOWN. Human review remains required even when the investigation completes.
No new Guardian PASS or original Work PASS is inferred from a valid report.

## Admin and storage

- POST `/api/admin/works/{id}/analyses`: explicit Human request UUID and rationale.
- GET `/api/admin/works/{id}/analyses`: bounded latest 20 investigation records.
- GET `/api/admin/works/{id}/analyses/{request_id}?detail=true`: report, execution
  records, checkpoints and resolved evidence catalog for review/download.
- Existing authenticated Admin ownership and cookie Origin/CSRF checks apply.
  Wrong-owner requests are rejected before model calls and evidence retrieval.
- Same request UUID/purpose returns its saved result without recapture/inference;
  changed purpose with reused identity is rejected. Failures are also idempotent.
- One investigation per API storage root is allowed across processes. Default
  limits are 12 inference submissions, 48 tools and 600 seconds; configuration
  ceilings are 24, 96 and 900. Native envelope and outer timeout both apply.
- Requests, frozen snapshots, catalog, audit events and checkpoints use existing
  immutable ContentAddressedStorage under `native_executor_storage_root/trace-analysis`.
  Atomic pointers persist progress. Crash/cancel/provider/verification failures
  retain available evidence. No DB migration or original Owner state write exists.
- A stale RUNNING observation is labelled STALE_OR_INTERRUPTED. Crash locks are
  not automatically stolen and production work is not automatically resumed.
  An operator must preserve evidence and establish that the analysis process is
  gone before removing a leftover analysis-only lock. Retention/backup are
  operational decisions; the bounded list is not an automatic deletion policy.

## Risks and qualification meaning

1. Incomplete/redacted historical evidence limits diagnosis; UNKNOWN must survive.
2. Runtime source and historical Worker identity can differ. Exact current source
   is comparison evidence, not proof of the historical implementation revision.
3. Quotation integrity does not prevent unsupported semantic deductions. Reports
   need independent Human evaluation against original owners and source.
4. Source, logs and model output may contain embedded instructions. They remain
   untrusted data; the tool registry grants only read/evidence capabilities.
5. Large histories can exceed context/time budgets. Failure evidence is valuable,
   but a failed investigation is not a successful self-understanding qualification.
6. Model calls use API credentials/configured Native provider. This phase does not
   qualify distributed scheduling, process-crash continuation or autonomous recovery.
   The existing adapter runs blocking provider HTTP in a thread; an outer timeout
   records interruption but does not prove the in-flight provider thread stopped.
7. Existing model adapters persist normalized decisions and transport metadata;
   this feature cannot reconstruct raw response bodies that they never saved.

Regression covers Native reuse/refinement, citation integrity, unknown/source limits,
exact revision reads despite dirty worktree, grants, cancellation, failures, replay,
cross-owner access, CSRF, original PostgreSQL owner counts and escaped Admin rendering.
A real historical export + live configured model + exact Work Git objects provides
an offline historical capability check; it is distinct from deployed ECS UI/runtime
qualification. Production deployment requires separate authorization and exact
source/storage/configuration checks. C3 closure is neither changed nor qualified.
