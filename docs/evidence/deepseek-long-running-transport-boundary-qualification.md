# DeepSeek Long-Running Transport Boundary Qualification

Date: 2026-09-20

## Scope

This qualification diagnoses the approximately 60-second DeepSeek Responses
disconnect observed by the Watt-native Executor and records the bounded transport
repair. It preserves Native Executor work decomposition, Tool semantics, Attempt
recovery, and high reasoning. It does not perform Full Regression, Closure, or
Human Acceptance.

## Repository and Runtime basis

- Branch: `feature/spg-first-vertical-slice`
- Start HEAD: `a6de8fe9dee3d5711e8a68e994a2375abfbf6729`
- Qualification HEAD: `a6de8fe9dee3d5711e8a68e994a2375abfbf6729`
- Provider endpoint: `https://api.deepseek.com/responses`
- API mode: Responses API
- Provider/model: DeepSeek `deepseek-flash`
- Native Executor reasoning effort after repair: `high`
- Client: Python `urllib.request` / `http.client`
- Configured socket timeout: 120 seconds
- Explicit container proxy variables: none
- Runtime network: the Human Review Docker network used by the Native Worker

The probe reused the Native Worker's credential and configuration path without
printing or persisting credential values. It did not create Work, PWU, Attempt, or
Tool effects.

## Original failure

Human Dogfood had observed Native Executor inference failures around 60.7–61
seconds. The local client timeout was 120 seconds. Failures included
`IncompleteRead` with `received_bytes=0`. Lowering reasoning and restricting each
inference to one `file.write` reduced exposure but did not explain the transport
boundary.

## Transport path

```text
Native Executor
  -> DeepSeekResponsesInferenceAdapter
  -> urllib.request / http.client
  -> Docker bridge and host network
  -> DeepSeek Responses endpoint
  -> CloudFront
  -> provider ELB/frontend
```

The Worker container had no `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, or equivalent
proxy environment variable. DNS resolved the public DeepSeek endpoint directly.
The real streaming response identified `server: elb`, `via: ...cloudfront.net`,
`transfer-encoding: chunked`, and `connection: close`.

## Deliberate reproduction

The same high-reasoning request and payload shape were sent sequentially from the
running Native Worker container.

### Non-streaming

- Request payload: 4,575 bytes
- HTTP status: 200
- Response headers: 1.219 seconds
- First response-body byte: never observed
- Response-body bytes: 0
- Disconnect: 60.660 seconds
- Exception: `IncompleteRead`
- Completion: absent

This reproduces the Human Dogfood signature while proving that connection setup,
request delivery, and HTTP response headers completed before the failure.

### Streaming diagnostic comparison

- Request payload: 4,574 bytes
- HTTP status: 200
- Response headers and first byte: 2.116 seconds
- Transport: SSE
- Received bytes: 3,173,083
- Received data events: 14,504
- Terminal event: `response.completed`
- Completion: 47.363 seconds

SSE continuously delivered reasoning and function-call argument events. No
keep-alive comment frames were required because model events themselves kept the
connection active.

### Repaired adapter long-running proof

The repaired production adapter then ran a separate high-reasoning request beyond
the original failure boundary:

- Duration: 65.873 seconds
- Response headers: 2.385 seconds
- First byte: 2.388 seconds
- Received bytes: 4,413,702
- Received events: 20,147
- Terminal event: `response.completed`
- Syntactically complete: yes
- Semantic action: `CONTINUE`
- Normalized Tool: one `file.write` proposal
- Proposed artifact size: 41,261 bytes
- Effective model: `deepseek-flash`
- Total tokens: 21,408

The request crossed 60 seconds without reducing reasoning or artificially
shortening the requested engineering result.

## Boundary ownership

The evidence rules out Watt's configured 120-second timeout as the 60-second
owner. It also rules out a model execution limit because the equivalent streamed
request completed and a later repaired streamed request ran for 65.873 seconds.

The narrowest supported conclusion is:

> The non-streaming chunked response body was closed by the upstream
> DeepSeek-serving CloudFront/ELB transport path after approximately 60 seconds
> without body activity.

The response headers expose CloudFront and ELB, but the evidence does not identify
which internal component configured or enforced the idle boundary. This report
therefore does not claim that the DeepSeek model itself owns a 60-second limit.

## Repair

The DeepSeek Native Executor adapter now:

- requests the existing Responses API with `stream=true` and
  `Accept: text/event-stream`;
- consumes SSE incrementally without retaining reasoning deltas;
- waits for the complete response object carried by `response.completed`;
- passes that final object through the existing Tool-call, structured-result,
  usage, and model-identity normalization;
- rejects EOF, malformed SSE, `response.incomplete`, or interrupted transport
  before the terminal event;
- keeps OpenAI and other Responses-compatible adapters on their existing behavior;
  and
- does not execute a Provider-proposed Tool until the complete semantic response
  has been validated.

## Error taxonomy and diagnostics

Provider transport now preserves these stable failure codes:

- `CONNECT_FAILURE`
- `TIMEOUT`
- `UPSTREAM_DISCONNECT`
- `INCOMPLETE_RESPONSE`
- `EMPTY_RESPONSE`
- `PROVIDER_ERROR`
- `INVALID_MODEL_RESPONSE`

Each inference observation or failed inference step can retain secret-free
transport facts:

- stream/non-stream mode;
- whether response headers arrived;
- HTTP status when available;
- header and first-byte elapsed time;
- total elapsed time;
- received byte and event counts;
- whether a terminal event arrived;
- whether the response was syntactically complete; and
- stable failure code.

Authorization headers, credentials, response text, and hidden reasoning are not
included in these diagnostics.

## Retry behavior

Transport interruption remains recoverable through the existing Attempt queue and
checkpoint behavior. Recovery is capped at three automatic retries. A response
without `response.completed` cannot propose a Tool, so retry cannot duplicate a
Tool from that interrupted submission. Tool receipts already represented in the
durable checkpoint are rehydrated rather than replayed.

Provider transport recovery is projected separately from genuine execution
capacity waiting. Repeated failure steps retain the same stable code and timing
fingerprint so later recovery strategy or Guardian work can recognize recurrence.

## Temporary workaround review

| Temporary workaround | Why it was added | Still required | Architecturally justified | Decision |
|---|---|---:|---:|---|
| Native Executor reasoning default forced from `high` to `low` | Reduce generation duration below the unexplained disconnect boundary | No | No | Removed; repository and Human Review runtime restored to `high` |
| At most one `file.write` proposal per inference | Shorten individual model responses during recovery | No | No | Removed; multiple semantic Tool proposals remain supported |
| Existing bounded Attempt retry | Prevent endless replay of transient Provider failures | Yes | Yes | Kept; capped at three and checkpoint-aware |
| Existing bounded internal execution turns | Bound Native Executor resource use | Yes | Yes | Kept; independent of the transport incident |

## Qualification matrix

| Case | Evidence | Result |
|---|---|---|
| A. Short normal response | Final Human Review runtime P1 real-provider probe | PASS |
| B. Long non-stream response | HTTP 200 headers, then 0 body bytes and `IncompleteRead` at 60.660 s | REPRODUCED |
| C. Long streaming response | Repaired adapter completed at 65.873 s with terminal event | PASS |
| D. Stream interrupted after partial bytes | Mocked SSE EOF before terminal | PASS: `INCOMPLETE_RESPONSE`, never success |
| E. Connection closed before first byte | Fault-injected `RemoteDisconnected` | PASS: `UPSTREAM_DISCONNECT` |
| F. Retry | PostgreSQL Attempt retry and checkpoint recovery tests | PASS: bounded, no duplicate settled effect |
| G. Explicit Provider error | SSE `response.failed` and HTTP resource-error contracts | PASS: `PROVIDER_ERROR` |
| H. Executor integration | Real P2: two DeepSeek submissions plus one isolated read-only Tool Host delivery | PASS |

The P2 result used `deepseek-flash/high`, completed two sequential Provider
submissions, settled exactly one `file.read`, created no production Attempt, and
performed zero mutations.

## Regression protection

- `BUG_CLASS`: Long-running non-streaming Provider response is interrupted at an upstream idle transport boundary.
- `ROOT_CAUSE`: HTTP 200 headers arrive promptly, but the DeepSeek-serving CloudFront/ELB path closes a non-streaming chunked body near 60.7 seconds before any body bytes; SSE model events avoid the idle interval.
- `PROTECTED_INVARIANT`: A valid long-running Provider result is not failed by Watt's own timeout; incomplete responses never become semantic success; Provider transport recovery remains distinct from execution-capacity waiting; bounded retry never duplicates settled effects.
- `PERMANENT_TESTS`: DeepSeek streaming contract and Tool normalization tests, partial/empty/disconnect/timeout/Provider-error fault tests, durable diagnostic persistence test, bounded retry test, and checkpoint effect-rehydration test.
- `TEST_LEVEL`: Provider contract, transport fault injection, PostgreSQL integration, Native Executor contract, and real bounded Provider/Tool Host probe.
- `GOLDEN_JOURNEY_IMPACT`: Strengthen `GJ-07 Provider or Executor Failure`; do not add a Golden Journey.

## Focused verification

Passed:

- DeepSeek inference adapter and streamed Tool-call contracts;
- model runtime and Native Executor contracts;
- transport interruption, timeout, empty response, and Provider error handling;
- multiple Tool proposals without the one-write workaround;
- bounded retry and checkpoint effect rehydration;
- transport diagnostic persistence in PostgreSQL;
- Control Room Provider-recovery projection;
- compose/product configuration contracts;
- Python compile/import;
- `uv lock --check`;
- `git diff --check`;
- Alembic current/head: `20260919_44`.

Full Regression was not run by design.

## Human Review runtime

- Compose project: `watt-pre-work-human-review`
- URL: `http://127.0.0.1:8045/app`
- Source: current preserved working-tree overlay at `/acceptance-source`
- Provider/model: DeepSeek `deepseek-flash`
- Native Executor reasoning: `high`
- DeepSeek streaming: enabled
- Runtime version: `12f8291b77e068661c9f801a4b5639a222b835a38b94a3c455b90e7ce9c97910`
- App, PostgreSQL, and Tool Host: healthy
- Human Acceptance: pending Human

## Status

```text
60S_BOUNDARY_REPRODUCED_OR_NARROWLY_CHARACTERIZED = PASS
BOUNDARY_OWNER = DEEPSEEK-SERVING CLOUDFRONT/ELB PATH / INTERNAL COMPONENT NOT OBSERVED
WATT_CLIENT_TIMEOUT_NOT_FALSELY_RESPONSIBLE = PASS
STREAMING_VS_NON_STREAMING_COMPARISON = PASS
LONG_RUNNING_PROVIDER_PATH = QUALIFIED
INCOMPLETE_RESPONSE_NEVER_SUCCESS = PASS
TRANSPORT_FAILURE_NOT_CAPACITY_WAIT = PASS
BOUNDED_RETRY_NO_DUPLICATE_SIDE_EFFECT = PASS
TRANSPORT_DIAGNOSTICS = PASS
TEMPORARY_EXECUTOR_WORKAROUNDS_REVIEWED = PASS
REGRESSION_PROTECTION = PASS
FULL_REGRESSION = NOT_RUN_BY_DESIGN
CLOSURE = NOT_PERFORMED
HUMAN_ACCEPTANCE = PENDING_HUMAN
COMMIT = NOT_CREATED
PUSH = NOT_PERFORMED
READY_FOR_HUMAN_REVIEW = YES
```
