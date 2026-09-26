# Watt Public External Search Qualification — 2026-09-25

## Scope and baseline

Branch: `feature/production-environment-foundation`; implementation began at
`3953f0cb0240559bd2d6b92a216f9becfbb54253`. The working tree already
contained uncommitted Self-Refine calibration changes; this qualification does
not treat those changes as a new Search subsystem or claim they were committed.
The complete local live-Turn observations, including early narrow-query and
rate-limit probes, are recorded in
[`watt-external-search-live-qualification-20260925.json`](watt-external-search-live-qualification-20260925.json).

Before this task, the Connector inventory named some GitHub operations but had
no executable GitHub repository/issue/code Search or public Web Search path.
WIC could discuss external implementations from model knowledge, but could not
produce attributable current search Evidence. Generic `http.request` and
browser automation were not installed search providers.

## Implemented execution reality

- A Human's explicit Search/Fetch request or a model-produced structured
  information gap becomes a canonical `SearchRequest`. A bounded DISCOVERY
  Task Contract records Human/Turn lineage and any current Steering step.
  `ConnectorResolver` checks each read-only capability before provider calls.
- Public GitHub REST repository and issue search, repository metadata/README/
  root paths/package manifest inspection, and exact public-file fetch are
  executable without a credential. Code search needs a configured read token.
- Brave Web Search is implemented behind `SPG_WEB_SEARCH_API_KEY`. Selected
  public HTTPS text pages can be fetched separately; a search snippet is not
  represented as inspected page content.
- Search and Fetch observations are append-preserving Interaction events with
  source type, URL, query, provider, time, rank, content/completeness, and
  stable Evidence ID. The final answer retains source links and references.
  They remain observations, not Engineering Semantic Truth.
- One weak query may broaden once. Query identity, distinct-result novelty,
  fetch count, elapsed time, bounded Evidence packet, and model output profile
  limit the refinement path. Ordinary reformulation is not an Incident.

## Live external observations

These are actual network retrievals, distinct from deterministic adapter tests:

| Probe | Observed result |
| --- | --- |
| GitHub repository search `python asyncio task queue` | [taskiq-python/taskiq](https://github.com/taskiq-python/taskiq), [janbjorge/pgqueuer](https://github.com/janbjorge/pgqueuer), and [quantmind/pulsar-queue](https://github.com/quantmind/pulsar-queue) returned as distinct repository results. |
| GitHub repository inspection | The Taskiq repository returned 6,503 characters of inspected metadata, README, root paths, and `pyproject.toml`; observed root paths included `docs`, `taskiq`, and `tests`. |
| GitHub issue search/inspection | [taskiq issue 650](https://github.com/taskiq-python/taskiq/issues/650) and [issue 480](https://github.com/taskiq-python/taskiq/issues/480) returned; issue 650 supplied 521 characters of inspected source text. |
| Direct GitHub file Fetch | [Taskiq README](https://github.com/taskiq-python/taskiq/blob/master/README.md) was fetched as inspected text in an earlier live probe. |
| Direct public Web Fetch | [Example Domain](https://example.com/) returned 142 characters of inspected page text. This proves Fetch, not Web Search. |

An earlier controlled, real-model Interaction Turn
`93bd8835-0d2c-4570-a99a-d653574af322` searched GitHub twice, broadening
from `python asyncio task queue implementation github` to
`python asyncio task queue`; it found six distinct repositories and inspected
three READMEs. A second real-model Turn
`36f17090-4187-4866-afbd-eda41a50b790` generated its own current-information
gap for a Python async queue question, executed two real GitHub searches, and
returned source-linked Evidence. Both correctly reported
`CREDENTIAL_REQUIRED` for Web Search because no Brave key was configured.
These Turn identifiers are observations from runtime qualification; test
database cleanup does not promise their indefinite retention.

Final controlled live Turn `7fde86d3-2600-4301-87dc-23ced1395ffd` searched
GitHub for mature Python asyncio task queues. Its first query was narrow; the
bounded second query returned seven distinct repositories. Three candidates
were inspected: [Taskiq](https://github.com/taskiq-python/taskiq),
[pgqueuer](https://github.com/janbjorge/pgqueuer), and
[kew](https://github.com/justrach/kew). The real model resumed over that
Evidence, made a source-ID-linked comparison of their observed backends and
repository signals, and stated that maturity was not proven by the sampled
README/metadata alone. Metrics: `query_count=2`, `refinement_count=1`,
`result_count=7`, `fetch_count=3`, `model_tokens=3986`, `sufficient=true`,
no failure category. Earlier live probes in the JSON show a weak narrow result
set and an actual GitHub `RATE_LIMITED` response; the final run succeeded
after query selection and model output budgeting were corrected.

Final controlled, model-initiated live Turn
`aa34c89e-d213-496e-8c77-f96b4f29891b` began from a current-maintenance
question without a Human search verb. DeepSeek requested GitHub and Web
research; the governed GitHub query broadened once, returned six distinct
repositories, and inspected three. DeepSeek resumed with those persisted
source packets (`model_tokens=3422`) and explained that Taskiq's inspected
README explicitly describes async support while the sampled RQ and
Procrastinate material does not establish the same claim. It also stated that
recent repository `updated_at` values alone do not prove sustained maintenance.
Web Search remained `CREDENTIAL_REQUIRED`. This is the complete live
information-gap → governed retrieval → Evidence → grounded answer path for
the available GitHub source class.
The actual HTTP Evidence projection returned `COMPLETED` with seven sources
for the explicit Turn and `PARTIAL` with six sources plus
`CREDENTIAL_REQUIRED` for the model-initiated Turn.

After refining the broadening rule, a further live DeepSeek information-gap
probe for “目前 Python 异步任务队列有哪些维护活跃的库？” generated GitHub and Web
requests itself. The first GitHub query was too narrow; the second removed
`library actively maintained`, returning six distinct repositories including
[RQ](https://github.com/rq/rq), [Taskiq](https://github.com/taskiq-python/taskiq),
and [Procrastinate](https://github.com/procrastinate-org/procrastinate). It
inspected two repositories; the model then resumed with those source packets
and generated structured, Evidence-ID-linked observations (`model_tokens=3400`,
`query_count=2`, `result_count=6`, `fetch_count=2`, `sufficient=true`). The
Web part remained explicitly `CREDENTIAL_REQUIRED`. This probe exercised the
real model and real GitHub API with the same canonical request/Connector
admission contract; the persisted Interaction path is separately covered by
the integration and controlled-Turn evidence above.

## Qualification separation

The `SEARCH-Q1`–`SEARCH-Q9` release-gate cases exercise semantics, Connector
admission, persistence, HTTP projection, model request/synthesis contracts,
failure boundaries, and convergence with deterministic providers. A passing
mocked case does not certify the corresponding live external provider.

| Case | Automated qualification | Live-provider qualification |
| --- | --- | --- |
| SEARCH-Q1 explicit GitHub | Covered by Interaction/Connector/Evidence test | PASS: final controlled live Turn searched, inspected, compared, and cited real repositories |
| SEARCH-Q2 explicit Web | Brave API shape and separate Fetch covered | BLOCKED: no `SPG_WEB_SEARCH_API_KEY`; real Web Search not claimed |
| SEARCH-Q3 combined | Combined Interaction test covers merge and source types | PARTIAL: live GitHub path works; real Web Search remains blocked |
| SEARCH-Q4 model-initiated | Structured information-gap and grounded synthesis covered | PASS: real model initiated GitHub retrieval and resumed grounded synthesis in the live probe above |
| SEARCH-Q5 refinement | Query broadening and duplicate stop covered | PASS: final live Turn changed query and improved the candidate set |
| SEARCH-Q6 provider failure | Rate-limit category and Human wording covered | PASS: a live GitHub rate limit was reported as `RATE_LIMITED`, never as no implementation |
| SEARCH-Q7 credential boundary | Missing key/token preserves public Search and blocks protected subtype | PASS: live Web limit surfaced while public GitHub succeeded |
| SEARCH-Q8 provenance | Persisted event, URL, Evidence ID, and final reference covered | PASS for observed GitHub and direct Fetch sources |
| SEARCH-Q9 convergence | Repeated-equivalent-result case stops within query budget | Deterministic qualification; no intentionally unbounded live run |

The actual runtime cost metric reports provider cost as `UNREPORTED` when a
provider does not supply charge data. No raw chain of thought is persisted.

## Verification and remaining blocker

Frontend Node regression: 75/75 passed. Focused Search unit tests, including
real result-shape handling, authority, failure, and inspection boundaries,
passed. The focused Search release gate passed all nine `SEARCH-Q1`–`SEARCH-Q9`
automated cases (9/9; no skips); its machine-readable report is
[`watt-external-search-release-gate-20260925.json`](watt-external-search-release-gate-20260925.json).
This proves covered implementation paths, while the live Web Search column
above remains blocked by the missing secret. The complete 8+1 / Self-Refine /
Connector / WIC / Search release gate passed 41/41 cases, zero failures and
zero skips, in all four domains (ASSURANCE, INTERACTION, PRODUCTION,
RESILIENCE). Machine-readable evidence is
[`watt-external-search-full-release-gate-20260925.json`](watt-external-search-full-release-gate-20260925.json).
The first gate attempt skipped two real-container cases because the sibling
ECF/Guardian checkouts were on documentation-only branches. After temporarily
checking out their existing production-foundation branches, the real-container
case passed and the complete gate passed; this was an environment correction,
not a code change to those repositories. The full backend suite then completed
at 100% with exit code 0: 1,382 collected tests, three skipped and no failures
(1,379 passed by count). The initial run had exposed a required WIC context
budget overflow and a Connector inventory dependency on unrelated invalid
settings; both were fixed, their exact failing cases passed, and the entire
suite passed on the final run. The 75/75 frontend Node checks passed.

Migration sanity: a fresh isolated PostgreSQL database upgraded through the
single Alembic head `20260925_49`, and `alembic current` confirmed that head.
Search uses the existing append-only response-event and message-reference
schema; it adds no migration. `alembic check` nevertheless reports
autogenerate differences in older tables such as `completion_evaluations`,
`runtime_commits`, and `capability_gaps` (mostly existing constraint/index
names). This is a separate metadata/migration reconciliation finding, not a
claim that the new Search schema is missing.

`SPG_WEB_SEARCH_API_KEY` is the only identified external secret blocking
live Web Search and live combined GitHub+Web qualification. The code and
configuration path are present. No credential is auto-acquired, and no Search
result is inferred from model memory when retrieval is blocked. Human
Acceptance remains pending.

```text
EXPLICIT_GITHUB_SEARCH_WORKS = PASS
EXPLICIT_WEB_SEARCH_WORKS = BLOCKED_EXTERNAL_SECRET
COMBINED_GITHUB_WEB_RESEARCH_WORKS = PARTIAL_EXTERNAL_SECRET
MODEL_INITIATED_SEARCH_WORKS = PASS_FOR_GITHUB
SEARCH_REQUEST_IS_CANONICALIZED_BEFORE_EXECUTION = PASS
SEARCH_RUNS_THROUGH_CONNECTOR_GOVERNANCE = PASS
REAL_EXTERNAL_RETRIEVAL_IS_PROVEN = PASS
SEARCH_RESULTS_ARE_EVIDENCE = PASS
SOURCE_PROVENANCE_IS_PRESERVED = PASS
SEARCH_CAN_REFINE_QUERY = PASS
SEARCH_REFINEMENT_IS_BOUNDED = PASS
SEARCH_PROVIDER_FAILURE_IS_TRUTHFUL = PASS
SEARCH_DOES_NOT_EXPAND_AUTHORITY = PASS
NO_FAKE_SEARCH_FROM_MODEL_MEMORY = PASS
NO_NEW_SEARCH_ARCHITECTURE_LAYER_WITHOUT_PROVEN_OWNERSHIP_GAP = PASS
HUMAN_ACCEPTANCE = PENDING
FULL_RELEASE_GATE = PASS_41_OF_41
BACKEND_REGRESSION = PASS_1379_PASSED_3_SKIPPED
FRONTEND_REGRESSION = PASS_75_OF_75
```
