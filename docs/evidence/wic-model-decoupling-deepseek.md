# WIC model decoupling and DeepSeek migration evidence

Date: 2026-09-13

Status: **FUNCTIONAL_PROVIDER_MIGRATION_PASS / PERFORMANCE_TARGET_NOT_YET_MET**

Human Product Acceptance: **NOT PERFORMED**

## Repository reality before migration

The HTTP Turn API acknowledged and queued work in `WorkInteractionService`,
which built an exact persisted interpretation basis and called
`CodexSdkWorkInteractionCapability`. Eligible pre-Work turns used one Codex SDK
thread/turn; active Work and differing semantic/conversation profiles used two
sequential turns. The transport imported `openai_codex.Codex`, created ephemeral
threads and depended on the host `CODEX_HOME/auth.json` login state. Partial
`natural_response` text was process-local until the complete semantic envelope
passed validation and admission.

The domain contracts, Conversation context/composer, Work admission boundary,
Guided Design boundary, coalescing rule, streaming safety and persistence rule
were already valid and are preserved.

## Implemented boundary

`WattModelRuntime` now contains a small explicit Provider Registry and an exact
purpose-to-profile router. `WIC_SEMANTIC`, `CONVERSATION_RESPONSE`, and
`EXECUTOR_PRODUCTION` are distinct purposes. The first two currently resolve to
DeepSeek `deepseek-flash`; Executor retains its independently qualified profile.

The DeepSeek Responses adapter owns:

- the canonical secret handle and base URL;
- a persistent keep-alive HTTP client and sequential request lock;
- strict JSON Schema requests and raw output streaming;
- request/effective-model identity, token usage and phase timing;
- credential-safe normalized failure categories;
- zero automatic Provider retries;
- removal of annotation-only schema text without removing validation rules;
- a configured 4,096-token output ceiling.

WIC semantic and Conversation expression remain separate high-level ports. The
pre-Work facade coalesces compatible profiles into one request and streams only
the `natural_response` JSON value. Active Work remains staged. DeepSeek types do
not enter Work, WIC domain, Work admission or Guided Design.

The legacy Codex implementation is retained as an explicit rollback adapter.
Its imports are lazy. An import-denial readiness test proved the default
DeepSeek application can be composed without importing `openai_codex`.

## Environment contract

The ignored local file is `.env`, mode `0600`. The canonical variables are:

```text
SPG_DEEPSEEK_API_KEY
SPG_DEEPSEEK_BASE_URL
SPG_WIC_PROVIDER_ADAPTER=deepseek
SPG_WIC_PROVIDER_MODEL=deepseek-flash
SPG_WIC_PROVIDER_REASONING_EFFORT=low
SPG_CONVERSATION_PROVIDER_ADAPTER=deepseek
SPG_CONVERSATION_PROVIDER_MODEL=deepseek-flash
SPG_CONVERSATION_PROVIDER_REASONING_EFFORT=low
SPG_WIC_COALESCE_PRE_WORK=true
```

The Executor can read the same canonical secret handle but retains its own model
and reasoning settings. The prior Executor-specific DeepSeek key variable remains
a compatibility fallback in typed settings; normal Compose wiring uses the
canonical variable. The key value was never printed or committed.

The app must restart after WIC profile changes. The native worker must also
restart after migration of the shared key source. No Codex login cache is needed
for default WIC startup.

Before the first real request, no-request readiness reported:

```text
readiness=PASS
provider=deepseek
wic_model=deepseek-flash
wic_reasoning_effort=low
conversation_model=deepseek-flash
conversation_reasoning_effort=low
coalescing_eligible=true
credential_configured=true
provider_request_sent=false
codex_sdk_imported=false
automatic_retry_count=0
```

## Functional and semantic qualification

The full local collection found 1,088 tests: all 472 runnable tests passed and
616 explicitly environment-gated cases were skipped. Focused migration tests also
proved Responses request shape, strict schema, raw-stream parsing, request/usage
normalization, no-request readiness, no automatic retry, secret-safe errors,
one-request pre-Work coalescing, useful-text-only streaming, and profile-driven
staged selection.

Existing regression coverage preserves ambiguous/insufficient Motive behavior,
refinement, new/unrelated Work handling, active Work focus, correction,
clarification, constraints, ordinary conversation, admission, coalesced safety
and staged composition. These tests compare domain outcomes and governance
boundaries rather than exact prose.

Real DeepSeek turns used `deepseek-flash/low`, sequentially, without retries:

| Case | Result |
| --- | --- |
| initial pre-Work goal | Useful provisional understanding, one recommendation/trade-off and one material operator question; no Work created |
| promotion background refinement | Preserved an operations backend for Watt promotion; distinguished audience from operators; recommended the content-to-channel-to-results workflow |
| Human correction | Accepted the correction immediately; persisted framing remained `PRODUCT_SYSTEM`, not an operational activity |
| design-document location question | Answered that no document/path yet exists and did not invent a path |
| recommendation | Reused Watt, audience and three-channel context; made one concrete workflow recommendation with rationale and trade-off |
| active Work constraint change | Preserved Motive and the full new internal-only constraint; classified `ON_TOPIC / HUMAN_GOVERNANCE_REQUIRED` |

The first active Work probe exposed a real defect: it retained the constraint but
classified the change as `NO_GOVERNED_CHANGE`. That failed result is retained as
history. The WIC contract was clarified so explicit constraint additions,
removals and corrections cannot use that disposition. The independent recheck
returned `HUMAN_GOVERNANCE_REQUIRED`.

## Streaming and authority

DeepSeek `response.output_text.delta` events feed a JSON string extractor. Only
decoded `natural_response` characters reach the SSE presentation buffer. The
semantic envelope is never streamed as conversational text. The final envelope
must validate against the existing strict Watt schema, reference the exact basis,
pass candidate admission and commit before the final Watt message becomes durable.
An invalid trailing semantic result therefore cannot turn an early draft into
Work or completed Conversation truth.

## Latency instrumentation

Process-local Turn diagnostics now observe request receipt, durable
acknowledgement, orchestration start, Reality load, context assembly, Provider
queue/send/acceptance, first Provider event, first token, first meaningful text,
semantic completion, validation, persistence, application completion and final
SSE emission. Missing data stays null after restart or eviction. A dedicated
Turn timing endpoint exposes this diagnostic view without changing product
truth.

## Bounded local performance sample

The isolated end-to-end runtime used port `8044`, a dedicated PostgreSQL volume
and current source. One connection warm-up plus four sequential warm pre-Work
HTTP/SSE turns produced:

| Case | Ack | Provider first token | Meaningful first text | Semantic complete |
| --- | ---: | ---: | ---: | ---: |
| initial | 31.9 ms | 9.422 s | 9.472 s | 12.467 s |
| refinement | 20.4 ms | 12.006 s | 12.113 s | 16.189 s |
| correction | 44.8 ms | 5.359 s | 5.576 s | 10.445 s |
| direct question | 19.3 ms | 7.869 s | 8.006 s | 10.740 s |
| recommendation | 20.2 ms | 4.097 s | 4.121 s | 7.578 s |

Across all five local observations, meaningful-first-text p50 was **8.006 s**,
interpolated p95 was **11.585 s**, minimum was **4.121 s**, and maximum was
**12.113 s**. For the four warm turns alone, p50 was **6.791 s** and the
interpolated p95 was **11.497 s**. Both samples are too small and local to
establish a production SLA.

The initial end-to-end case decomposed to Provider request sent at 55 ms, first
Provider event at 1.840 s, first token at 9.422 s, semantic completion at
12.467 s, validation at 12.469 s, persistence at 12.530 s and client stream
completion at 12.546 s. Refinement showed the same shape: send at 41 ms, first
event at 0.871 s, first token at 12.006 s, semantic completion at 16.189 s and
persistence at 16.249 s.

The valid active Work staged recheck used two requests. Semantic first token was
6.750 s and completion was followed by Conversation first token at 2.875 s;
meaningful first text was 13.538 s and total completion 14.027 s. This is the
intentional active-Work serialization boundary, not pre-Work regression.

After the final runtime restart, one cold-connection smoke with the 4,096-token
ceiling also passed the full Responses/SSE/validation/persistence path. It
acknowledged in 27 ms but first meaningful text was 18.258 s (Provider first
token 18.082 s). This cold observation is excluded from the warm five-turn
percentiles and demonstrates material Provider variance rather than a stable
3–5 second result.

A controlled warm pre-Work request after schema annotation compaction reported:

```text
input_tokens=3487
cached_tokens=1792
output_tokens=1824
reasoning_tokens=1128
total_tokens=5311
retry_count=0
meaningful_first_text=7.917s
total=11.024s
```

At the official 2026-09-13 peak `deepseek-v4-flash` rates, that recorded request
has a conservative estimated charge of **USD 0.00318**. This is an estimate from
reported token usage, not a Provider billing-ledger total. Unknown usage remains
explicit for failed/transport-ambiguous calls.

## WIC performance gap

`PERFORMANCE_TARGET_NOT_YET_MET`.

The 3–5 second healthy-warm target was reached only by the fastest recommendation
observation, not by the p50 or p95. Watt-owned pre-send work was tens of
milliseconds and post-model validation/persistence was roughly tens of
milliseconds. Provider acceptance arrived below two seconds, while 4.1–12.0
seconds elapsed before the first output token. The dominant measured gap is
therefore model reasoning/generation before visible output. Refinement also grew
the exact context and missed more of the cacheable prefix.

The next bounded optimization work can proceed without another provider rewrite:

1. qualify a non-thinking/lower-latency WIC profile against the frozen semantic
   regression set before changing the default;
2. stabilize and shorten the shared instruction/schema prefix further to improve
   cache hits while retaining all constraints;
3. measure a larger warm sample by role and context size;
4. evaluate a separate faster Conversation profile for active Work, using the
   existing staged seam;
5. retain one-request pre-Work streaming and the exact final validation boundary.

## Dogfood and scope

Domain additions are limited to provider-neutral model identity/profile/result
contracts. Application changes are bootstrap selection, latency observation and
the diagnostic endpoint. DeepSeek-specific protocol code is confined to
Provider infrastructure and the WIC Provider adapter. No DeepSeek types or
branches were added to Work admission, Work domain, Guided Design, Guardian or
Executor production semantics. The only Executor edit accepts the canonical
shared secret source while keeping its independent profile and legacy fallback.

No database schema change was required; migration head remains `20260912_39`.
No Human Product Acceptance was performed.

Protocol and pricing authority:

- <https://api-docs.deepseek.com/guides/responses_api/>
- <https://api-docs.deepseek.com/api/create-response/>
- <https://api-docs.deepseek.com/quick_start/pricing/>

## Closure

```text
WIC_MODEL_DECOUPLING PASS
DEEPSEEK_WIC_PROVIDER PASS
CHATGPT_CODEX_LOGIN_DEPENDENCY_FOR_DEFAULT_WIC REMOVED
WIC_SEMANTIC_REGRESSION PASS
CONVERSATION_RESPONSE_PATH PASS
PRE_WORK_COALESCING PRESERVED
PERFORMANCE_INSTRUMENTATION PASS
PERFORMANCE_ARCHITECTURE READY_FOR_3_TO_5_SECOND_TTFT_OPTIMIZATION
PERFORMANCE_TARGET NOT_YET_MET_WITH_MEASURED_GAP
```
