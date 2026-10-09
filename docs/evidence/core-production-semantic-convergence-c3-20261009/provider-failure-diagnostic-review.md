# C3 — Provider Failure Diagnostic Boundary

## Historical evidence

The actual G0 Work `048189aa-0613-5307-b6f4-c430e7977f93` on source `91f5dbc9906d1f857113736981517c1091ec52ae` recorded one formation pending stage and one terminal `OBLIGATION_FORMATION_TRANSPORT_ModelProviderError` stage. The original typed failure metadata was not persisted. The Provider failure kind, request ID, HTTP attempt/replay count and numeric token usage remain **UNKNOWN**. The observed Owner timestamps do not establish a timeout. Earlier WIC/IRK usage is not formation usage. Historical records are unchanged.

## Minimal implementation

The existing ModelFulfillmentCandidateProvider now clears its per-call observation before constructing a runtime and preserves only typed ModelProviderError metadata on formation or semantic-review failure. The existing Work fulfillment terminal receipt reconstructs the safe projection from the actual error, rather than trusting a previous Provider observation. It identifies the failure stage and references every unresolved source from the exact admitted inventory. No new schema, Owner, authority, retry or model call is introduced.

The whitelist is `kind`, `request_sent`, `usage_unknown`, `retryable`, `provider_status`, `termination_reason`, `request_id`, and `occurred_at`. Enum, boolean and timezone-aware timestamp types are checked. Provider status, termination reason and request ID allow only bounded machine characters, with limits of 64, 120 and 200 respectively; known secret values are omitted using the existing redaction helper. Invalid or unavailable fields remain null. Exception text, HTTP bodies, headers, context and arbitrary exception attributes are excluded.

ModelProviderError does not expose numeric usage or HTTP replay count. Consequently the projected numeric token fields and transport retry count remain null, and numeric usage is UNKNOWN even when the original Provider error carries `usage_unknown=false`. Existing `provider_call_count` denotes governed logical call entries, not an inferred HTTP attempt count. Terminal same-basis replay still performs no new call; existing limits remain two candidate attempts, one feedback refinement and one semantic review per candidate, at most four governed calls.

## Qualification boundary

The new module `tests/test_c3_fulfillment_provider_failures.py` contains nine controlled cases for formation/review failure, stale observations, runtime construction failure, safe field bounds, exact unresolved source references, unchanged facts, and terminal budget replay. AST/compile and `git diff --check` passed. Linux execution is pending Root's isolated regression. No live Provider, Work, environment or service was invoked for this amendment. This improves future diagnosis and does not claim that the historical Provider transport failure has been repaired or retrospectively explained.
