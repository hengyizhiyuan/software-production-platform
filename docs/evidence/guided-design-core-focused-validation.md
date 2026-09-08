# Guided Design Core Focused Validation

Date: 2026-09-08
Starting checkpoint: `fac6cdc4323d98234c9e6c27a2c03a79da8117f3`
Branch: `feature/spg-first-vertical-slice`

## Result

```text
Guided Design Core = IMPLEMENTED / FOCUSED VALIDATION PASS
Human Product Acceptance = PENDING
Architecture STOP = NONE
```

## Deterministic and integration evidence

Focused contracts prove:

- the general product/system schema is product-neutral and dependency-coherent;
- agenda issues map to exact Plan Steering DESIGN Steps;
- current focus comes from the current Steering Step;
- issue satisfaction requires an admitted semantic result;
- skip/reopen requires rationale and produces append-only agenda/Plan revisions;
- readiness is derived from unresolved critical Reality, not list length;
- earlier admitted result summaries are supplied to later DESIGN Steps;
- WIC Work Reality context facts and requests reach semantic execution;
- stale or invented Reality references fail closed;
- restart reconstructs process, agenda, current focus, results and readiness;
- intermediate issues cannot produce and the final issue must produce a typed
  proposal to claim completion;
- proposal review projects one typed Human Attention boundary;
- proposal approval is exact/idempotent and only then permits PLAN-1B
  `ONE_PWU_FIT` and SPG Run/PWU admission;
- production/Runtime evidence can reopen an issue without rewriting history;
- legacy immediate-production and pre-Guided long-lived behavior remain valid.

The affected suites cover WIC, Work, API, Plan Steering, semantic Provider wire
contracts, PLAN-1B, SPG, Completion, Verification, Candidate, Integration,
Runtime Commit and Runtime activation. PostgreSQL execution uses an isolated
temporary PostgreSQL 16 container and migration head `20260908_27`.

Focused results:

- Guided Design/domain/PLAN-1B/Steering/Runtime activation/Provider wire/SPG/UI/
  WIC contract group: 77 passed;
- WIC admission/semantic execution/Steering truth PostgreSQL group: 61 passed,
  2 skipped (the real-Provider gates were intentionally separate);
- affected API/Work/long-lived Steering/Completion/Verification/Candidate/
  repository integration/Runtime Commit group: 207 passed, 1 skipped;
- final gated real-Provider proof: 1 passed, 24 deselected.

## Real Provider proof

One bounded proof scenario starts with:

> 我想做一个运营管理平台。

A second test-fixture Interaction provides governed clarification of target
users, the closed-loop operational problem, first-stage outcome and explicit
non-goals. This is integration evidence, not Human Product Acceptance.

The proof uses `openai-codex 0.147.0`, ChatGPT authentication, ephemeral
read-only threads and `deny_all` approval. Every Turn consumes a freshly
reconstructed input and the strict `_SemanticProviderPayload` output schema.
No secret contents or raw transcript are preserved.

Observed result:

- real schema admission and semantic generation: PASS;
- JSON decode / strict wire validation / wire-to-domain conversion: PASS;
- application admission and persisted governed results: PASS;
- 5 governed semantic results were admitted from 5 independent Provider
  Threads / 5 Turns: PASS;
- 4 design issues reached `SATISFIED`: motive/users/problem,
  outcomes/scenarios, boundary/non-goals and capabilities/workflow;
- earlier admitted results remained available to later issues: PASS;
- agenda revision 5 and current focus
  `responsibility-information-interaction` reconstructed from PostgreSQL: PASS;
- readiness remained truthfully `NOT_READY` and execution stopped at the
  governed `STEERING_DECISION_REQUIRED` Human Attention boundary: PASS;
- Run / PWU / Attempt / Dispatch / production Provider Report / Candidate /
  Authorization / Integration Effect / Runtime Commit: `0` throughout.

The final successful run completed in 709.40 seconds. The gated regression is
`test_guided_design_real_provider_leads_multi_step_design_without_production`.
The test emits these exact per-run issue and Thread/Turn counts; this evidence
does not infer Human acceptance from Provider success.

## Migration and repository guards

- `alembic heads`: `20260908_27 (head)`.
- `alembic current`: `20260908_27 (head)`.
- `alembic check` reports only the pre-existing unique-constraint naming
  differences already admitted for legacy tables. It reports no Guided Design
  table, column, index or check-constraint drift.
- compile/import: PASS.
- `uv lock --check`: required final guard.
- `git diff --check`: required final guard.

## Product surface

The API and Control Room expose process objective/schema, agenda revision,
current focus and rationale, progress, issue states, skip/reopen rationale,
readiness blockers and upcoming transition. The exact production proposal is
shown through existing Work/Production Plan fields and existing Attention
actions; no broad UI redesign is claimed.

## Findings

`PRE_AUTHORIZATION_WORK_PREVIEW_REQUIRED` is implemented for the Guided Design
to production transition through exact governed proposal review. Broader
product presentation and Human Product Acceptance remain pending.

The first real proof attempt stopped correctly because the vague Motive lacked
Human-owned users/problem facts. The next attempt showed that admitted WIC
`context_facts` were not yet carried into semantic input. That bounded
`WIC -> DESIGN` context propagation gap was fixed and regression-tested before
the successful fresh proof. No Architecture STOP or Authority weakening was
required.

## Status boundary

This record proves implementation and focused engineering validation. It does
not prove enterprise completeness, full ECF/Production Passport, or Human
Product Acceptance.
