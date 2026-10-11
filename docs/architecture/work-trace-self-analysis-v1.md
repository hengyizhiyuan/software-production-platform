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

### General evidence scope repair (report v2)

Every catalog record now carries producer-derived source semantics. Guardian HTTP
observations, delivery download/server-transfer audits and Native identifier links
are different evidence families. These labels come from existing producer
contracts, never keywords or model text. A Guardian PASS without an actual HTTP
receipt cannot support a PREVIEW_HTTP fact. Typed facts cannot cite a different
producer surface. This is an evidence rule, not a Work/domain-specific rule.

The initial context contains deterministic `evidence_reality` checks across these
families, including exact original evidence IDs/pointers and bounded examples.
Session `pwu_id` and attempt `work_unit_id` are the existing PWU identifier aliases;
other actual execution reference fields are exposed without inferring lifecycle
completion. Missing an initial example is not interpreted as absent: the model can
read originals or perform a scoped `evidence.check` against a captured group and
JSON Pointer (`*` enumerates). The query scans all selected exported rows; returned
examples are capped and labelled. No database/query/write capability is added.

Report v2 requires exact reconciliation of the seeded family checks. Every
`missing_evidence` entry is now a structured gap with a check ID, family and
availability. PRESENT evidence cannot be labelled missing. No-match is at most
NOT_OBSERVED_IN_CAPTURE; redaction, truncation or an uncaptured producer preserves
INCOMPLETE_CAPTURE. It never proves global or historical absence. Unknown groups
are rejected instead of silently treated as zero records. Derived checks can
substantiate lookup scope, but cannot replace original Owner fact citations.

All checks are saved in the immutable investigation catalog for independent review.
This still cannot validate arbitrary free-form prose or causal entailment; Human
review is required. Existing saved v1 reports remain readable, including legacy
string gaps; no original report or Owner record is migrated or rewritten.

### Owner association and conclusion boundaries (report v3)

New reports bind every finding to an observed original `subject_evidence_id`.
The fact must cite that subject; additional fact citations require an explicit
Owner reference, the same Owner identity, or the same capture metadata. Shared
Work, attempt, component, error text or timestamp alone does not establish a link.
Related-record hints do not mark their bodies read or establish causality.

Captured-field gaps must copy the exact bounded check conclusion and link to an
UNKNOWN finding with the same scope. Owner refinement diagnoses and expected or
rejected behaviors are distinguished from execution receipts. Causal hypotheses
must be explicitly labelled and conditional; missing rejected candidate contents
remain UNKNOWN. Regression criteria require governed recovery or termination;
specific scenarios are recorded separately, without requiring zero future model
failures. These gates do not prove arbitrary free-form semantic entailment.

Saved v1/v2 reports remain readable. See the [association repair qualification](work-trace-self-analysis-association-repair-20261011.md)
for original Owner reconciliation, live historical analysis and remaining limits.

### Timeline and recommendation qualification

Dated timeline entries also require `timestamp_evidence_id` and `timestamp_field`.
The cited, read original Owner must contain the same timezone-aware instant.
Events are ordered by observed time; an unrelated incident cannot share a dated
entry merely because it belongs to the same Work. Undated composite summaries
remain possible, without invented timestamp anchors. Creation time does not
automatically establish recovery completion time; prose still needs Human review.

Producer field descriptions distinguish refinement budgets and synthetic counters
from observed regeneration. Exact repository source is comparison evidence until
historical Worker identity is established. A final diff describes net changes;
it cannot independently establish intermediate behavior or rollback safety.
Recommendations must preserve governed recovery/termination, source uncertainty,
and the separate meanings of transfer audit, preview evidence and Human acceptance.
These checks do not prove semantic entailment for arbitrary recommendation prose.

### Original linked fields and bounded uncertainty (report v4)

The Native registry's read-only `evidence.inspect` follows explicit Owner
references up to two hops and returns original field fragments. The actual
`execution_effects` producer is mapped to `native-effect` alongside the legacy
alias; a receipt's `effect_id` now resolves its original semantic input. Shared
Work/attempt/error text still does not establish incident identity. Traversal is
retrieval coverage, not transitive fact association.

Every finding requires a subject-specific inspection receipt. PRESENT, READ,
REDACTED, EMPTY, NOT_EXPORTED and capacity-unread observations are distinguished;
only actually returned fragments acquire citation authority. Unread critical
linked fields or omitted associated records require further original reading or
UNKNOWN. Large fields remain pageable through the existing `evidence.read`.

Uncertainty is the exact inspection boundary plus performed field-check boundaries,
not arbitrary generated absence prose. Check groups must belong to the finding's
inspected Owner scope. Unrelated gaps require separate subjects. A general prose
guard also rejects common absence assertions outside those checked fields; it
complements typed lookup/reading and does not claim complete linguistic entailment.
The gate is independent of any Work identity, command name or scenario wording.

Dated entries copy the exact producer-time boundary into `time_interpretation`,
also shown in Admin. Refinement creation time cannot timestamp later VERIFIED or
recovered state; use its original update record or an undated snapshot summary.
Existing saved v1/v2/v3/v4/v5 reports remain readable without migration or rewriting.

### Recommendation subjects and conditional mechanisms (report v5)

Recommendations now declare their evidence family; every referenced finding's
original subject must belong to that producer surface. A download recommendation
cannot borrow a Guardian authorization finding. General Owner proposals remain
separate from specific transfer, preview and identity topics. Free prose still
requires semantic review; this gate does not claim complete linguistic entailment.
Causal hypotheses must begin with a conditional mechanism (`假设：若`). A recovery
outcome or proposed repair does not establish which replacement command ran;
that requires original execution observations. Both `recovery` and
`self_refine_events` are verified projections of the same producer rows and use
the same identity, diagnosis and timestamp boundaries. Initial context selection
reserves space within the existing ECF budget; omitted excerpts are not marked read.

### Checked boundary presentation (report v6)

The Native model can use `INSPECTED_OWNER_BOUNDARY`, `CHECKED_FIELD_SCOPE` and
`ORIGINAL_OWNER_TIME_BOUNDARY` for derived scope/timestamp presentation. The
verifier resolves these only after validating original read receipts, exact
subjects, field checks, availability, event times and associations. Original
model drafts remain immutable. Facts, causal hypotheses, classifications,
recommendations, timestamps and identifiers are never automatically repaired.
The output presents canonical text from the performed checks, reducing repeated
machine-text copying without admitting arbitrary absence claims. PRESENT still
cannot become missing; unread critical fields still require UNKNOWN. Classifier
labels/proposal references in a refinement diagnosis alone cannot establish a
system capability defect or reproducibility. Budgets and permissions are unchanged.

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
