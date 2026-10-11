# Watt Trace Analysis — Owner association and conclusion boundaries

## Independent scope

Branch: `codex/watt-trace-self-analysis`. Previous delivery: `b68027c`.
Implementation: `074a5fc6fdb1bd8872a938a16424f07d1f226755`.
Final source: `bbff515567bfbfdc56b4061e7b7b175b71bbc909`.
Baseline architecture remains `5de657f3`. Canonical checkout and C3 are untouched;
no production Work/Owner changes, deployment, schema migration or new AI pipeline.

Initial regression: **131 Python/PostgreSQL + 31 Admin JS PASS**, zero skips/failures.
Final regression: **132 Python/PostgreSQL PASS**, zero skips/failures; the 31 JS
tests also pass (JS source unchanged by the last hypothesis-only adjustment).
Final live historical investigation: **COMPLETED/RESULT_READY**. The requested
association and conclusion-boundary repair regressions: **PASS**.
Architecture/Human acceptance remains **PENDING**. Deployment: **NOT_DEPLOYED**.

## Root cause and minimum repairs

OBSERVED FACT: the previous real-model report F2 described the process.run
Self-Refine event but quoted the inference-decision event as one of its facts.
Both quotations were real and in the same OWNER_RECORD family. That gate did not
establish whether they belonged to the same incident.

VERIFIED FINDING: report-v2 lacked a required primary Owner subject and original
record association validation. Report-v3 requires `subject_evidence_id` for every
finding and an exact citation of that subject. Additional fact citations must have
an explicit original Owner reference, the same Owner identity/projection, or the
same frozen capture metadata identity. Shared Work/attempt, error text, component
or timestamp cannot join distinct incidents.

Source: `src/spg/domain/trace_analysis.py`, `Finding`;
`src/spg/infrastructure/trace_analysis_evidence.py`, `association`, `_references`,
`related`, `validate`. Reference decoding uses existing Native producer contracts:
receipt, inference-step and effect namespaces and declared Owner reference fields.
Model proposals, tool arguments, shared identifiers and arbitrary nested log text
do not create associations. Repository comparison citations retain their distinct
role and cannot become an original historical incident subject.

`evidence.read` exposes bounded `related_records` hints through the existing Native
tool. It does not mark their bodies observed. Those original records must still be
read before quotation. Association proves a recorded link, not causal truth.

OBSERVED FACT: the previous report checked one exported `raw_response` field, then
some F3/F5 prose inferred broader absence of raw provider bodies. Its suggested
regression criteria also included no recurrence of future stochastic failures.

VERIFIED FINDING: report-v2 checked receipt identity/availability but accepted
arbitrary absence text and did not connect that gap to a bounded finding analysis.
Each check now supplies `bounded_conclusion`: exact frozen capture digest, family,
group, field, scanned count, match count, availability and explicit limits.
Missing-evidence and Owner-field assessment statements must copy this value.
Each gap must link to a scoped finding; its analysis must copy the checked boundary
and its classification/epistemic status must remain UNKNOWN. This rejects promotion
of a checked missing field into a defect or platform/history absence. Intermediate
model proposals remain saved unedited; a rejected assertion is not silently rewritten.

Source: same adapter `check/validate`; domain `Finding`; application `RULES`.
Repository comparison and incident hypotheses remain separate from capture gaps.
Uncertainty about a root cause must name the checked field and cannot treat it as
proof about an entire response or a different Owner. Native provider-report field
presence is distinct from the checked execution-step field's availability.

Regression qualifications copy the classification's governed criterion exactly.
Model-variance qualification is recovery within existing permissions/budget or
governed termination, not zero future errors. `regression_scenario` carries the
specific adversarial example. Admin displays escaped primary subjects and scenarios;
saved v1/v2 reports remain readable.

The first live run corrected association, gap scope and regression outcomes, but
review found one additional interpretation limit: a refinement diagnostic's rejected
behavior list was described as the contents of an earlier executed candidate.
The final adapter marks refinement diagnostics, expected reality and repair
hypotheses explicitly. Those are not executed-effect receipts or proof of an
unavailable candidate's contents. Causal analysis must start `假设：` and use
conditional language; the recorded diagnosis belongs in fact. This stays in the
same evidence adapter/schema, with no new analysis stage or model client.

## Regression evidence

- Randomized incident/receipt IDs, identical error/component and shared attempt:
  the referenced receipt is accepted; another incident or its receipt is rejected.
- Incoming and outgoing explicit links work; association metadata alone does not
  permit quotation of an unread linked record.
- A scoped missing field is accepted; global/history absence prose is rejected
  in both the finding analysis and gap statement.
- Wrong field selectors, unknown groups, redaction, preview/download boundaries,
  existing PWU/session/attempt aliases and quotation integrity remain covered.
- A zero-future-failure qualification is rejected; governed recovery/termination
  is accepted. UI v3 escaping and saved legacy rendering pass.
- Owner diagnostic/expected-field roles do not become execution receipts; an
  unlabeled causal assertion is rejected, while an explicit hypothesis is accepted.
- Existing Native substrate, recovery, cancellation, CAS replay, exact Git reads,
  API ownership/CSRF and original PostgreSQL Owner immutability tests pass.

## Real historical qualification

Work: `3ee622b5-b816-5679-afdc-e5de51cd2702`, completed real-model qualification/
dogfood Work. This is known-case repair verification, not an unseen/customer holdout.
Frozen capture: `2026-10-11T01:59:43.088902+00:00`, NON_ATOMIC_ACROSS_OWNERS.
Full ZIP SHA256: `3df14f6430f47bd1a85d909d3a3e5c51e06fcf84d738e58eda90b0d4530c275c`.
trace.json SHA256: `a909a2d9b7541caf23597dee1a82fb4ffa09ab2d64ed0dc9987517069f97f2c9`.
Exact Work source: `d4ad65db95fa1bb3ad7ec951ea844fd4939c2a3d`;
Candidate: `b4280990d55ac9da36eaa0dd9644006df7e8762e`.
Runtime comparison: stable `5de657f3`; actual historical Worker revision: UNKNOWN.

The runner uses the existing TraceAnalysisService, Native Kernel/tool registry and
configured Native inference adapter with a real model (`deepseek-flash`). Only
registry/export inputs are frozen historical data; no expected answer is included
in the generic investigation request. Default 12-inference/48-tool/600-second
envelope is unchanged. Seven actual source-file hashes are saved at start.

Initial request `7075452a-ed31-482e-830a-fa90dae7504c` on `074a5fc`:
**COMPLETED/RESULT_READY**, 9 inference submissions/31 tools, 91 events;
`2026-10-11T06:32:21.944727+00:00` through `2026-10-11T06:37:05.487377+00:00`.
Report digest: `e368e7284876a63b8b17be3e5cfbcf0be034db4db8d754099fcbcf0f0449a7b9`.
Initial submission had two quotation mismatches; existing gates rejected them and
bounded draft revision corrected both. Original report/drafts/history are preserved
under `attempt-1-*`; the interpretive concern above motivated final `bbff515`.

Final request `7980b536-0dee-403d-8057-5746298808a8` on `bbff515`:
**COMPLETED/RESULT_READY**, 10 inference submissions/31 tools, 93 journal events,
no residual Native obligations. Started `2026-10-11T06:39:51.852084+00:00`, finished
`2026-10-11T06:46:42.842185+00:00` (411 seconds), within unchanged default budget.
Report digest: `480f3d60abd094a8c96af0fef89884a1da35b19767b901c5552521e43fc0624c`.

Independent review against original Owner records and exact repository evidence:

| Repair qualification | Result | Actual final-model evidence |
| --- | --- | --- |
| Correct incident association | PASS | F2 anchors receipt `47c852a9…` and cites Self-Refine `66f40d43…`, whose diagnostic receipt_ref names that receipt. F3 anchors inference step `b4d11a60…` and cites Self-Refine `9325939c…`, whose inference_step_ref names that step. No process/inference-event crossover remains. |
| Checked-field conclusion boundary | PASS | F4 analysis/gap copy the exact execution_steps `/result_payload/raw_response` check. F5 analysis/gap copy guardian `/delivery_authorization_state`, which is redacted. Both are UNKNOWN/INCOMPLETE_CAPTURE and explicitly do not establish other Owner/whole-response/history absence. |
| Diagnosis versus executed effects | PASS | F1 states that the scope signal is an Owner diagnosis, uses conditional hypothesis language, and explicitly says missing rejected candidate contents cannot be proved from the listed rejected behaviors or the final diff. |
| Governed stochastic regression | PASS | All three variance findings use the fixed recovery-or-governed-termination criterion. Their scenarios retain permissions and budget, with no zero-future-failure requirement. |
| Earlier repaired evidence surfaces | PASS | Independent Guardian HTTP observations are cited for both produced pages. Transfer audit remains separate; execution links remain PRESENT. No missing-mapping conclusion or transfer-to-preview denial is reintroduced. |

The review is a source/Owner reconciliation by Codex, independent of the
report-generation call, not Architecture Lead approval. No generated report text
was edited. All model drafts, failures and tool outputs remain available for review.
`independent-review.json` records exact association anchors and source hashes.
Original-model report and independent Owner/source reconciliation will be retained
under `C:/Users/yuchunbo/Downloads/Watt-Self-Analysis-Association-Repair-20261011`.

## Boundaries that remain

Typed association and copied scope statements do not prove all free-language
causal hypotheses, recommendations or uncertainty logically follow. They need
Human/Architecture review. Unknown producer references fail conservatively; future
producer contracts require corresponding evidence adapters, not fuzzy error matching.
Redaction, non-atomic historical capture, missing rejected raw bytes and unknown
historical Worker identity cannot be repaired by modifying a report.
No deployment or whole-platform/future-Work semantic guarantee is claimed.
