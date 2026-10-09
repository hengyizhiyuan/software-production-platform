# Work AI Diagnostic Export v1 — qualification record

Date: 2026-10-09 (Asia/Shanghai). Source base: `bf90e4fb03520ff154ed846921cb77907ce7c6b5`, tree `59e08f627049df5485e37103541010b2a8510dad`. This branch was developed in an independent worktree. The final export commit/tree are reported in the delivery response; this file records the tested source tree before commit.

## Executed checks

| Scope | Result | Evidence |
|---|---|---|
| Unit and negative tests | 8 PASS | `tests/test_work_diagnostic_export.py`: compact/full structure and hashes, missing PWU/Candidate, redaction, owner denial, productless denial, filename allowlist, size error, explicit capacity truncation. |
| Isolated PostgreSQL integration | 2 PASS | `tests/integration/test_work_diagnostic_export.py`, isolated `watt-admin-diagnostic-pg-20261009`; local DESIGN fixture and produced PWU/Candidate fixture; route auth/foreign Work/unknown Work/path rejection, same-Work isolation, 40-record conversation capped at 30 while preserving the first Human input, pre/post Owner table counts. These are fixtures, not live qualification. |
| Admin JS interaction | 26 PASS | `tests/js/test_admin_surface.cjs`, including lazy list loading, successful download, detail links and server error notice. |
| Real browser | PASS | Headless installed Microsoft Edge against `tests/browser_diagnostic_app.py` and isolated local PostgreSQL; `tests/browser_diagnostic_smoke.py` confirmed list ZIP download, detail `report.md` download, error notice and no list Trace hydration. |
| Real ECS Work, DESIGN | PASS for read-only export logic | Work `408e408a-fab8-5a34-b101-b922043cb6fd`: `DESIGN`, `WAITING_HUMAN`, 8 saved conversation entries, one Steering Decision, zero PWU/Candidate, zero Verification/Guardian. Compact ZIP about 27.3 KB; 157,112 uncompressed bytes; 0.74–1.09 s across observed runs; hash and ZIP checks passed. Read-only SQL separately identified current DESIGN/HUMAN_ATTENTION. |
| Real ECS Work, production | PASS for read-only export logic | Work `3ee622b5-b816-5679-afdc-e5de51cd2702`: `COMPLETE`, `COMPLETED`, 7 conversation entries, 3 PWU, 3 Self-Refine entries, 6 Verification entries, 1 Candidate, 4 Guardian entries. Full ZIP about 1.64 MB; 13,100,547 uncompressed bytes; 5.76–7.15 s across observed runs; hash and ZIP checks passed. |

The ECS qualification ran the **exact current branch exporter and bounded Trace methods** in memory in the pre-existing `watt-cloud-worker-api-1` image. It used a PostgreSQL connection whose `transaction_read_only` was asserted `on`. It printed only Work IDs, stage/state, evidence counts, sizes, timing and integrity results. It did not write a remote file or bring real conversation, model output, tokens or credentials into this repository. The endpoint is **not deployed to ECS**; the real ECS HTTP/UI route is therefore not yet qualified. Timing is one sample per case, not a service-level latency guarantee.

## Case A–J disposition

- **A — DESIGN stall:** Real ECS Work above satisfies stage, Human Attention, conversation and absent PWU/Candidate. Human Decision source is present as a Steering Decision; this check does not claim that every intended Human decision was saved.
- **B — full production:** Real ECS Work above has the requested PWU, Self-Refine, Verification, Candidate and Guardian categories. Source refs and exact Work identity are retained by Trace. Completeness of every external historical source is UNKNOWN.
- **C — UNKNOWN/NOT_REACHED:** Unit and DB tests confirm empty later stages are not labelled PASS; the report says `NOT_REACHED_OR_NOT_OBSERVED` where those meanings cannot be proved apart.
- **D — identity/isolation:** Exact owner lookup precedes Trace; foreign and unknown Work requests are rejected. Shared Interaction sibling exclusion is inherited from the directional Trace reader and is exercised by DB integration. Productless historical Works are denied without tenant owner proof.
- **E — sensitive content:** Test secrets in free text, nested JSON, headers and URLs are redacted; long text is marked. No redactor can guarantee detection of every novel credential syntax; external sharing still requires review.
- **F — ZIP/integrity:** Unit, DB, real browser and in-memory ECS checks opened ZIPs, parsed JSON and validated all manifest-listed SHA256 hashes.
- **G — size:** Table reads are capped, fallback exclusions are explicit and a critical-evidence overflow fails explicitly. Synthetic overflow and database-backed 40-to-30 row cap tests passed; the latter found and fixed ordering of equal-timestamp conversation records by durable sequence. Real compact/full samples remained below 5/20 MB uncompressed. Separate paged raw-owner attachment export is not implemented; existing exact Owner/Trace retrieval is the supported follow-up.
- **H — read-only:** Integration compared Owner table counts before/after; real ECS connections asserted `transaction_read_only=on`. No model or execution path is invoked by the exporter.
- **I — Admin interaction:** JS and real Edge checks passed on an isolated test server. ECS production browser route remains untested because this branch is not deployed.
- **J — C3 parallelism:** Base excludes the unqualified N1/C3 commits. On this date C3 checkout was at `f2dda0549efe35e7855f26f73a5770ac4159f97a` with uncommitted edits to Work/Steering/Verification/Guardian and related files, but no observed edit to this branch's four changed runtime/UI paths. C3 final commit and combined-tree compatibility remain UNKNOWN. A rebase/merge qualification must use both exact final commits.

## Synthetic examples

`samples/compact/` and `samples/full/` contain the four individual files; the adjacent ZIPs package them. They are generated entirely from test data, with fixed synthetic Work ID `00000000-0000-4000-8000-000000000001` and Product ID `00000000-0000-4000-8000-000000000002`. Sample ZIP SHA256:

- compact: `8d8f468c1e12377aede7d19a00a109e6e001eb0c1aa09169cdefea227b252944`
- full: `e88480e8fd7b3e2f92575ec7864685a3b0a758640d0f6169e876fba51742186c`

Regeneration changes capture timestamps and ZIP hashes; verify the current files after regeneration. These examples must never be described as real ECS evidence.
