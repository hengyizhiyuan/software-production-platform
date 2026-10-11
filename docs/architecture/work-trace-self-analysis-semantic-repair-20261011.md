# Watt Trace Self-Analysis — semantic evidence repair

## Scope and status

Independent branch: `codex/watt-trace-self-analysis`. Stable architecture baseline:
`5de657f3cb65780adf50f6557b54171a6c3cfae5`. This follow-up starts at `dee3028`.
No C3 implementation, canonical-main change, production Owner write, new Work,
deployment, permission relaxation or new inference pipeline is involved.

Implementation commits:

- `0a4456db447b0d2af96a3db4b2cc3c25705905d4`: producer evidence semantics,
  original-snapshot checks, required evidence reconciliation and checked gaps.
- `298674ae99d1d624e559b117946fba8478b1dd6c`: reject incorrect record selector
  roots and support an additional checked Owner-field assessment.
- `bf307d57fda5c42ad437fe52080499f464015981`: separate a transfer audit's
  completion rule from actual action observations.
- `4b3353cfab302a9a604f61e4f48fa2910490eacb`: provide unambiguous valid wildcard
  pointer examples in tool schemas, instructions and read-failure feedback.

Final mechanical regression: **127 Python/PostgreSQL tests and 30 Admin JS tests
PASS**, no skips. Final live investigation: **COMPLETED/RESULT_READY**.
The two requested semantic repair regressions: **PASS**. Whole-report semantic
acceptance is **not claimed**; remaining review concerns are recorded below.
ECS deployment: **NOT_DEPLOYED**. Architecture/Human acceptance: **PENDING**.

## Verified implementation findings

The previous gate checked that quotations existed in observed evidence, but did
not encode the producer surface that made each quotation meaningful. Thus an empty
download audit could be treated as missing preview evidence. An absence claim could
also be generated before reading the existing Native Owner identity fields.

The repair stays in the existing evidence adapter, schema and Native tool registry:

| Boundary | Source | Minimum repair | Regression qualification |
| --- | --- | --- | --- |
| Preview versus transfer | `src/spg/infrastructure/trace_analysis_evidence.py`, `source_semantics`, `EvidenceCatalog.check/validate` | Guardian's actual HTTP entries are PREVIEW_HTTP; served_delivery is DELIVERY_TRANSFER. Require matching original citations for specialized facts. A gate PASS alone is not HTTP proof. | Arbitrary routes and randomized IDs; cross-surface citations rejected in both directions; missing Guardian HTTP entries are not replaced by PASS. |
| Existing execution relationships | Same file, `RELATION_FIELDS`, `check/reality` | Read actual PWU/session/attempt identity fields and existing `work_unit_id` alias across frozen original rows. Seed bounded examples before investigation; retain exact original pointers. Links do not prove lifecycle completion. | Session.pwu_id and attempt.work_unit_id expose the same random PWU without reading every row. Available relationships cannot be marked missing. |
| Absence versus unread/redacted | Same file; `src/spg/domain/trace_analysis.py` | Add Native `evidence.check`, receipt-backed gaps and availability reconciliation. Scan original captured scope, then cap returned examples. Invalid group/root selectors fail as reads, rather than returning false absence. | Unknown groups, `/0/pwu_id`, misspelled roots, unread positive records, redaction, unchecked string gaps and contradictory availability. |
| Rule versus event | Same adapter and `src/spg/application/trace_analysis.py`, RULES | Expose action count and completion_rule_description separately. A captured audit object is PRESENT even with no actions; that presence or rule text proves no transfer event. Preserve raw original audit unchanged. | Empty actions and a failed arbitrary action remain distinct from completion; rule text does not generate an event outcome. |
| Report/history display | `src/spg/web/admin.js` | Render report-v2 structured assessments and gaps; continue reading saved v1 string gaps. | Escaped v2 statements/check IDs and existing v1 report rendering. |

No runtime branch uses a Work UUID, business domain, specific route or expected
historical answer. Historical identities exist only in qualification fixtures and
evidence. This is a producer-contract adapter, not a second architecture layer.

## Real evidence and observation boundaries

Historical Work: `3ee622b5-b816-5679-afdc-e5de51cd2702`, a completed real-model
qualification/dogfood Work, not an ordinary customer Work. Frozen diagnostic
capture: `2026-10-11T01:59:43.088902+00:00`, NON_ATOMIC_ACROSS_OWNERS.

- Diagnostic ZIP SHA256: `3df14f6430f47bd1a85d909d3a3e5c51e06fcf84d738e58eda90b0d4530c275c`.
- trace.json SHA256: `a909a2d9b7541caf23597dee1a82fb4ffa09ab2d64ed0dc9987517069f97f2c9`.
- Historical Git pack SHA256: `343bad5f715ee8a0412e2e5dd8238b3ebe6e54cedbde182effbef2d1aed76a69`.
- Source baseline: `d4ad65db95fa1bb3ad7ec951ea844fd4939c2a3d`.
- Candidate revision: `b4280990d55ac9da36eaa0dd9644006df7e8762e`.
- Comparison runtime source: stable `5de657f3`; historical Worker revision: UNKNOWN.

OBSERVED FACT: Guardian result `d71f2935-02ea-4289-a2d4-d363a1783f1e`
contains GET observations for both produced pages, HTTP 200, response_sha256,
observed_at and exact Candidate identity. There are three original Guardian
receipts plus an aggregate projection; six HTTP entries are matches across these
four projections, **not six independent observations**.

OBSERVED FACT: served_delivery has empty actions, client_received/client_saved
UNAVAILABLE, historical_action_identity NOT_RECORDED. completion_basis describes
what ASGI_SEND_COMPLETED would prove. It is not evidence that any historical send
completed, and does not negate the separate Guardian HTTP receipts.

OBSERVED FACT: session `296ef921-e388-54e4-a268-09af4ecbae0d` has pwu_id
`b394e64d-d7d3-5fab-abe3-3c5744497533`; attempt
`dea9d9c9-31c9-4feb-91bc-a5995c9edd2f` has the same work_unit_id. The broad
lookup reports 356 reference-field matches across 469 selected records; these
include projections and are **not 356 distinct attempts**.

ROOT CAUSE HYPOTHESIS: previous model errors arose from interpreting a quotation
outside its producer contract and making negative conclusions from unread rows.
VERIFIED FINDING: the former adapter lacked these explicit scope checks; the new
general tests reproduce and reject those mechanically checkable errors. This does
not prove that every future natural-language claim is entailed by its citations.

## Qualification history

The original qualification document remains unchanged as historical PARTIAL
evidence. No failed run or unedited model report is overwritten in the delivered
evidence bundle.

1. `fa532075-7b2c-4cb7-a61a-3a9305798c68`, source `0a4456d`: COMPLETED,
   12 inference submissions/30 tools. It recognized Guardian HTTP observations
   and Native relationship fields. A model field lookup incorrectly prefixed a
   per-row pointer with `/0`; that motivated `298674a`. Broad semantic acceptance
   is not claimed for this intermediate report.
2. `5ef520b5-31ac-4a2c-bcb6-fc40630f537e`, source `298674a`: report submission
   passed citation/structure/scope checks, but the final Native decision was
   invalid JSON at the 12-submission budget. Overall **FAILED/BUDGET_EXHAUSTED**,
   44 tools. The retained validated draft is reviewable, not an accepted completed
   investigation. Review also caught a rule-versus-send-event overstatement,
   motivating `bf307d5`.
3. `7d1ea2e2-b693-4306-9623-cb6c2ffa4949` uses `298674a` already imported and
   hashed before the next source edit: **COMPLETED/RESULT_READY**, 9 inference
   submissions/29 tools. The unedited report reads both routes' HTTP evidence,
   separates empty transfer audit from preview, and recognizes all three PWU/
   attempt/session groups. Invalid selector attempts are retained as read failures,
   not history gaps. Report digest:
   `ea41f312bf7d0f4081a6abfd4c9ba98c41353166a20ecd9708f1d970186999fb`.

4. Final source `4b3353c`, request `b3766f64-cd1d-4674-aa00-446350f4ec32`:
   **COMPLETED/RESULT_READY**, 10 inference submissions/26 tools, 84 journal
   events, `2026-10-11T05:46:28.596749+00:00` through
   `2026-10-11T05:52:50.601240+00:00` (382 seconds). Same generic investigation
   request, same configured Native model (`deepseek-flash`), unchanged default
   12-inference/48-tool/600-second envelope. No expected repair answer was fed
   into the request. Initial submission cited an unread original delivery record;
   the gate rejected it, the model read that record, then revised the retained
   draft. Feedback is VERIFIED and no residual Native obligations remain.
   Report digest:
   `cd877f01774d1f191f7dffc767a295eeb5bf35cd6321926d7f322a7b1ad5798f`.

Independent review of the unedited final report against original Owners:

- **PASS — preview/transfer separation:** PREVIEW_HTTP assessment cites actual
  Guardian observations for both pages, HTTP 200 and response digests. The
  DELIVERY_TRANSFER assessment explicitly says action_count=0 and PRESENT means
  only an audit object exists. F4 explicitly rejects interpreting completion_basis
  as an event or empty actions as a completed send; it does not deny preview.
- **PASS — existing PWU/session/attempt links:** EXECUTION_RELATIONSHIP assessment
  reads the existing work_unit_id/pwu_id aliases and checkpoint references. The
  EXECUTION timeline cites the original session's pwu_id and records condition
  OPEN without converting that into missing mapping or lifecycle closure.
  No recommendation proposes adding already-existing PWU/session identity fields.
- **PASS — checked absence scope:** the raw-response gap has a performed
  `/result_payload/raw_response` check and INCOMPLETE_CAPTURE, tied to the frozen
  capture. The assessment explicitly recognizes a different producer report's
  field enumeration as PRESENT. No field-query failure is used as absence proof.
- **Remaining semantic review concerns:** F2's first quotation uses the
  inference-decision Self-Refine event (`e9370c45…`) while the fact describes the
  process.run event; the process receipt and narrative are correct, but that
  quotation is misassociated. Some F3/F5 prose also describes raw-body absence
  more broadly than the exact checked field, despite its explicit capture limits.
  Several suggested regression criteria expect no future stochastic failures and
  need Architecture/Human judgment. Do not mistake successful structure/scope
  verification or the two targeted PASS results for whole-report semantic truth.

The last review is a repository/Owner reconciliation by Codex, separate from the
report-generation call. It is not Architecture Lead approval or Human acceptance.
No model-generated report text was manually corrected. `independent-review.json`
records the scoped result and remaining concerns; the evidence bundle contains all
four runs, including the failed second run and its retained validated draft.

## Residual limits

- Quote, source-family and scope checks are not full semantic entailment. Human
  review remains required; advisory reports cannot authorize changes.
- Positive family availability establishes recorded evidence, not rendering,
  client receipt, successful transfer or lifecycle closure.
- Negative field checks apply only to the frozen capture and chosen selector.
  Unexported/empty groups and unknown root fields fail conservatively; arbitrary
  deeper pointers are not validated against the complete Owner schema.
- Redaction, non-atomic capture, missing rejected raw responses and unknown
  historical runtime identity remain evidence limits, not repaired history.
- Provider variance and the existing investigation budgets can still cause a
  failed terminal decision even after a report passes mechanical checks.
- This known historical Work is a targeted repair regression, not an unseen
  holdout or qualification of all future Works. No deployed ECS/UI check is claimed.

Evidence directory:
`C:/Users/yuchunbo/Downloads/Watt-Self-Analysis-Semantic-Repair-20261011`.
