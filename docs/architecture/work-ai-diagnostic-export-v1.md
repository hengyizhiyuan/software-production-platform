# Work AI Diagnostic Export v1

This Admin feature packages one authorized Work's existing Owner evidence for human or AI diagnosis. It creates no Work, production event, Quality finding, Guardian result, or alternate lifecycle store. It follows [Program ADR-0002](https://github.com/hengyizhiyuan/software-production-system/blob/1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1/docs/04-decisions/ADR-0002-STOCHASTIC-NATIVE-ENGINEERING.md): deterministic identity, provenance, authorization, integrity and evidence limits; open diagnostic hypotheses remain with the consuming AI and Human.

## Contract and scope

- `GET /api/admin/works/{work_id}/diagnostic?mode=compact|full` downloads `watt-work-<id>-diagnostic.zip`.
- Add `file=report.md`, `file=trace.json`, or `file=evidence-manifest.json` for individual downloads. `diagnosis-context.md` is in the ZIP.
- The existing Admin session authenticates the request. `WorkRegistryService.get(actor, work_id)` checks the exact Work's Product owner before `ProductionTraceService.entity_trace("work", work_id, ...)` reads the directional Work lineage. Productless historical Works have no durable tenant owner and are denied for export until ownership is proven; their ordinary Trace remains governed by its existing route.
- The Work list only fetches the bounded registry page. Export hydrates one Trace after clicking. Both modes share the `production-trace-v1` owner projection; compact omits raw owner bodies, full includes them subject to redaction and capacity.
- `trace.json` wraps the existing Trace as `lifecycle`, with `schema_version=watt-work-diagnostic-v1`, exact Work ID, capture metadata, missing evidence and warnings. It is a live read, not a historical qualification snapshot. `report.md` is a readable projection of the same data; it must not be interpreted as independent Owner truth.

## Evidence and consistency

Database lineage is read through one `unit_of_work` transaction. The registry, owner database, Guardian result files and Preview projection are read at separate instants. `capture.captured_at`, `lifecycle.basis.at`, `capture.consistency=NON_ATOMIC_ACROSS_OWNERS`, and manifest warnings describe that boundary. No global atomic snapshot or full historical completeness is claimed. Missing stages remain `NOT_REACHED_OR_NOT_OBSERVED`; `UNKNOWN` is never a pass. Model proposals, tool effects, local Self-Refine and independent Guardian outcomes remain distinct in the Trace. The exporter never calls a model or mutating application service.

`source_revision` and `source_tree` are taken only from observed PWU/source Owner records when available; otherwise they are `null`. No configured revision or runtime image string is used as a substitute. The manifest contains the SHA256 and byte count of each *other* file, and intentionally does not hash itself. Verify it by opening the ZIP, hashing each named entry, and comparing the recorded values.

Each individual-file request performs a new live capture. Its `X-Evidence-SHA256` response header verifies that response body. A separately downloaded manifest does not establish a common snapshot with separately downloaded report/Trace files; use the ZIP when cross-file hash matching matters.

## Redaction and limits

The exporter applies the Trace's existing safe projection and a second recursive pass: sensitive field suppression, credential and private-key patterns, URL credentials/query tokens, email and Chinese mobile-number redaction, and explicit long-text markers. These rules cover common forms; an administrator should still review an export before sharing it with an external AI. Human text, model responses and logs are labelled untrusted evidence in the report and analysis context. A fixed four-name ZIP allowlist prevents archive path traversal. No repository, binary artifact, Holdout file or arbitrary filesystem path is packaged.

Defaults are 600 rows per Owner table, 5 MB compact and 20 MB full in uncompressed file bytes, and four files. The bounded reader retains earliest, failure-bearing and latest rows when a table exceeds its cap. Text is capped at 4,096 characters in compact and 32,768 in full. Guardian result file inspection stops at 2,000 files. When capacity is exceeded, duplicated and verbose projections are removed in documented order while retaining identity and a bounded failure chain; the manifest and Trace record exclusions. If critical evidence still cannot fit, the endpoint returns an explicit error rather than an incomplete package labelled complete. Server settings: `SPG_DIAGNOSTIC_EXPORT_MAX_ROWS_PER_TABLE` (30–5,000), `SPG_DIAGNOSTIC_EXPORT_MAX_BYTES` (1,024–100,000,000), `SPG_DIAGNOSTIC_EXPORT_MAX_FILES` (1–4; fewer than four rejects the standard package).

The current endpoint does not provide a separate paged raw-owner attachment API. For details excluded by caps, an authorized engineer must use the existing exact Trace/Owner retrieval path and verify identity before associating those records with this export.

## Future quality handoff

Quality Revolution can consume this versioned export as input to failure-signal extraction, clustering and improvement proposals. Any Finding, Campaign, regression qualification, governed Work or trusted-baseline promotion must continue through existing Quality and Human admission Owners. This version performs none of those actions.

## Parallel integration with C3

This branch starts from `bf90e4fb03520ff154ed846921cb77907ce7c6b5` (tree `59e08f627049df5485e37103541010b2a8510dad`), before unqualified N1/C3 Runtime changes. It edits `production_trace.py` only to add an optional bounded Work read and expose an observed source tree; ordinary Trace behavior is unchanged when the new option is absent. Before merging with C3, compare exact source commits and the Work/IRK/Steering/Verification/Guardian Trace shapes, then rerun the focused DB and Admin tests on the combined tree. Passing this isolated branch does not qualify C3 or its runtime.
