# Watt Regression Protection and Golden Journey Governance

## Purpose

This document defines how Watt converts Human Dogfood failures into durable
engineering memory without allowing verification cost to grow linearly with the
number of historical incidents. It governs the choice of permanent regression
protection and the evolution of a small Golden Human Journey suite.

Recent Dogfood exposed failures in PRE_WORK durability and admission continuity,
Engineering Semantic Truth retention, Work and Human-action projections, queue and
scheduler progression, Provider and Executor recovery, and UI consistency. The
system must absorb those failures without adopting a policy of one permanent
browser journey for every bug.

## Governing principle

> A historical bug should normally be converted into a durable system invariant,
> then protected at the lowest-cost test layer capable of reliably detecting its
> recurrence.

The normal path is:

```text
Real Human failure
  -> root cause
  -> protected invariant
  -> lowest-cost permanent regression protection
       -> unit
       -> contract
       -> integration
       -> UI-state
  -> strengthen a Golden Journey when the invariant belongs to a core Human journey
```

A historical incident does not automatically justify a new Golden Journey.

## Bug closure discipline

The default engineering rule is:

> No regression protection, no bug closure.

Every meaningful production or Human Dogfood defect must identify:

| Field | Required meaning |
|---|---|
| `BUG_CLASS` | The stable failure category, independent of the incident date. |
| `ROOT_CAUSE` | The system cause rather than the visible symptom. |
| `PROTECTED_INVARIANT` | The condition that must remain true. |
| `PERMANENT_TESTS` | The focused checks that detect recurrence. |
| `TEST_LEVEL` | Unit, contract, integration, UI-state, or an explicitly justified alternative. |
| `GOLDEN_JOURNEY_IMPACT` | Existing journey strengthened, new journey proposed, or none. |

A local repair is not fully absorbed until suitable recurrence protection exists.
When deterministic reproduction is impossible, protection may use fault injection,
Provider contract or resilience tests, monitoring and reconciliation invariants, or
Guardian evidence requirements. A conventional test case is not mandatory when it
would make a weaker or misleading assurance claim.

## Lowest-cost reliable protection

Regression protection belongs at the cheapest layer that can reliably observe the
invariant:

| Defect surface | Default protection |
|---|---|
| Function or state-transition logic | Unit test |
| API, schema, authority, or capability boundary | Contract test |
| Cross-module persistence or lifecycle behavior | Integration test |
| Frontend projection and action availability | UI-state test |
| Core Human production capability | Strengthen the relevant Golden Journey when needed |

Browser E2E is not the default for behavior that a smaller deterministic test can
protect. Low-cost tests may grow substantially; expensive journeys must grow much
more slowly.

## Invariants and Golden Journeys

An invariant states a condition that must always hold. Examples include:

- PRE_WORK conversation survives persistence, reload, and restart.
- PRE_WORK admission preserves Work identity and Human-visible continuity.
- `BLOCKED` identifies a truthful resolution owner.
- `NEEDS_ATTENTION` exposes an executable Human action.
- A queued item has a live progression owner and a truthful waiting reason.
- Production and Verification consume admitted Engineering Semantic Truth rather
  than independently reinterpreting Human intent.

A Golden Journey proves that Watt can still complete a meaningful Human goal while
the relevant invariants hold together. Many historical defects can map to the same
journey.

Golden Journeys represent durable user capabilities, not incidents. They remain:

- limited in number and stable over time;
- oriented around Human goals;
- black-box or near-black-box where practical;
- representative of real product use;
- required at major qualification and release boundaries.

When a bug is found, first ask whether an existing journey lacks an assertion. If
so, strengthen that journey. Add a journey only when the failure reveals a genuinely
new Human production journey. Incident-shaped names such as
`GJ-2026-09-19-pre-work-refresh-bug` are prohibited.

## Candidate Golden Journey families

These families are an initial direction, not a frozen or currently implemented
suite.

| ID | Durable Human capability |
|---|---|
| `GJ-01 Greenfield Production` | PRE_WORK -> refinement -> Admission -> Production -> Verification -> Preview -> authorization or delivery. Covers durability, identity continuity, automatic progression, Candidate creation, and usable Preview. |
| `GJ-02 Human Correction` | Existing understanding or result -> material Human correction -> Semantic Truth supersession -> stale result invalidation -> re-Steering -> re-Production -> corrected Preview. |
| `GJ-03 Brownfield Change` | Existing repository and product Reality -> understand -> modify -> verify -> Candidate -> delivery. |
| `GJ-04 Mid-Work Interaction` | Active Work -> side question, status question, or refinement -> consistent production truth -> uninterrupted continuation. |
| `GJ-05 Human Authority` | Material decision required -> truthful stop or wait -> actionable Human control -> decision -> governed continuation. |
| `GJ-06 Execution Control and Recovery` | RUNNING -> Pause, Resume, or Stop -> Reality reconciliation -> recovery or replanning. |
| `GJ-07 Provider or Executor Failure` | Provider, Tool, or Executor failure -> truthful failure state -> bounded recovery -> no Work or Semantic Truth corruption. |
| `GJ-08 Delivery` | Verified Candidate -> authorization -> exact artifact -> delivery. |

## Consolidating observed failures

| Human-visible failure | Protected invariant | Permanent protection | Journey impact |
|---|---|---|---|
| PRE_WORK disappears after refresh | PRE_WORK conversation is durable across reload and restart. | Persistence and lifecycle integration tests. | Add a reload or recovery assertion to `GJ-01`. |
| Admission temporarily hides the Workspace | PRE_WORK -> admitted Work preserves identity and visible continuity. | Integration and UI-state tests. | Strengthen `GJ-01`; do not add a journey. |
| Semantic drift such as `8×5` | Downstream Production and Verification consume admitted Engineering Semantic Truth. | Semantic, Production, and Verification integration tests. | `GJ-02` proves correction and supersession together. |
| `BLOCKED` with no action required | A blocked state has a valid resolution owner; Human attention implies an executable action. | State and projection contract tests. | Strengthen `GJ-05`. |
| Queue or scheduler stall | Every queued item has a live progression owner or a truthful typed waiting reason. | Scheduler and lifecycle integration tests plus recovery assertions. | Strengthen `GJ-01`, `GJ-06`, or `GJ-07` according to cause. |
| Provider, runtime, or UI projection failure | Failure and recovery projections reflect durable Runtime Reality without corrupting Work. | Provider contracts, fault injection, integration, and UI-state tests. | Strengthen `GJ-07`; use another journey only when the affected Human capability requires it. |
| PRE_WORK response appears only after a long pause or Fast text reverses a negative instruction | Human-facing wording starts only after governed semantics, then progresses through the Conversation Realizer; pre-governance text reports reception only. | Provider-path contract, response-event reconstruction, Fast negative-instruction, SSE, and browser paint assertions. | Strengthen `GJ-01`; do not add a journey. |

## Qualification tiers

| Boundary | Required verification direction |
|---|---|
| Ordinary development | Focused unit, contract, integration, and UI-state tests selected from the affected surface. |
| Significant vertical capability | Focused tests plus the relevant Golden Journey families. |
| Major architecture or milestone qualification | Affected focused suites plus the Golden Journey Suite. |
| Closure or Release | Golden Journey Suite plus Full Regression plus Human Acceptance and any required assurance gates. |

Full Regression is not required for every implementation task. Focused verification
remains the normal development tool, while Closure and Release retain the broadest
assurance obligations.

## 2026-09-20 milestone application

The current Watt milestone applied this governance rather than treating every
late Human finding as a reason to repeat the entire regression suite. Before the
final narrow UI and Delivery repairs, the closure Full Regression reached 1,264
Python outcomes: 1,254 passed, 10 intentionally skipped real-Provider probes,
and zero failed. The Web/UI suite passed 65 cases, Native/Linux qualification
passed, and lock, compile/import, migration-head, and Runtime-health integrity
checks passed.

Human review then found three narrow post-regression defects: the terminal
Deliver milestone projection remained visually current after Work completion;
the Human Review profile displayed software acceptance while its exact delivery
Runtime was disabled and left a stale error after recovery; and the unchanged
frontend asset URL allowed an ordinary browser refresh to retain the old
projection code. These changes were qualified with the lowest-cost reliable
evidence: UI-state and configuration contracts, the Control Room Node suite, a
single PostgreSQL software-delivery acceptance integration case, live exact
Runtime/hash evidence, and Human re-verification.

The earlier Full Regression remains immutable historical evidence and is not
claimed to cover those later fixes. The decision not to rerun it is an explicit
application of `Risk -> Required Evidence`: the changes were narrow, their
affected invariants were directly observable, and focused evidence plus Human
re-verification covered the changed boundaries.

The expected scalable shape is:

```text
many low-cost invariant protections
+
small high-value Golden Journey suite
```

Regression-test count and Golden Journey count must not scale linearly with the
historical bug count.

## Guardian and assurance sufficiency

Guardian is the future owner of assurance sufficiency, not necessarily the executor
of every test:

```text
Change and risk
  -> affected obligations
  -> required focused regression evidence + required Golden Journeys
  -> evidence collection by execution infrastructure
  -> Guardian assurance judgement
  -> gate, findings, exceptions, and confidence
```

Historical failure classes should increase assurance obligations for related future
changes. A Work-lifecycle change may require lifecycle integration tests, PRE_WORK
and Semantic Truth continuity evidence, `GJ-01`, and `GJ-02`. A Markdown-renderer-only
change should not automatically require every Native Executor recovery journey.

This establishes the future direction `Risk -> Required Evidence`. It does not
authorize Guardian implementation.

## Historical failure as engineering memory

> Real Dogfood failures should become engineering memory.

The memory may take the form of stronger invariants, contracts, targeted regression
tests, Golden Journey assertions, failure taxonomy, and assurance obligations. The
desired flywheel is:

```text
Real production or Dogfood failure
  -> root-cause understanding
  -> architecture or process improvement
  -> regression protection
  -> future qualification
  -> lower recurrence probability
```

## Immediate adoption and non-goals

This governance applies immediately to new Human Dogfood defects. Future repair
reports must include the six `REGRESSION_PROTECTION` fields and use the lowest-cost
sufficient permanent protection. A new Golden Journey requires a genuinely new
Human journey.

This document does not authorize a new E2E framework, conversion of every existing
test, immediate creation of the candidate journey families, Guardian implementation,
running every test for every change, replacement of focused verification, replacement
of Human Acceptance, or removal of Full Regression from Closure and Release.

### GJ-01 queue progression assertion

Future `GJ-01 Greenfield Production` qualification must observe automatic progression
from an admitted PWU through Queue, allocation, Attempt execution, Verification, and
Preview. A queue may be described as waiting for capacity only while a compatible live
worker exists and its finite slot is occupied. When no live compatible worker owns
progression, Production must show system-owned recovery and must not ask the Human to
advance, retry, or repair the scheduler. Recovery after worker or scheduler restart must
reuse the durable queue item without duplicating the Attempt.

### GJ-01 Preview passive-resource assertion

Future `GJ-01 Greenfield Production` qualification must open the exact Watt Preview
in a real browser and prove that passive external HTTPS images required by the
artifact render successfully, including an HTTPS redirect to another CDN host.
The same observation must prove that Preview still blocks external active scripts
and does not introduce wildcard `default-src` or `script-src` policy.

`REGRESSION_PROTECTION`

- `BUG_CLASS`: Preview passive-resource capability is narrower than the admitted artifact.
- `ROOT_CAUSE`: Watt Preview emitted `img-src 'self' data:` as an HTTP response policy, which cumulatively overrode artifact image allowances.
- `PROTECTED_INVARIANT`: Watt Preview supports artifact-required passive HTTPS images while retaining its active-resource boundaries.
- `PERMANENT_TESTS`: Candidate Preview and static delivery Runtime assert the shared CSP; GJ-01 observes image load, redirected CDN load, and external-script rejection in a real browser.
- `TEST_LEVEL`: API integration, Runtime integration, and existing Golden Journey browser evidence.
- `GOLDEN_JOURNEY_IMPACT`: Strengthen `GJ-01 Greenfield Production`; do not add a journey.

### GJ-07 long-running Provider transport assertion

Future `GJ-07 Provider or Executor Failure` qualification must distinguish a
Provider-declared error, connection failure, timeout, upstream disconnect,
incomplete response, empty response, and invalid model response. A valid
long-running response must not fail because Watt's own client timeout is shorter
than the admitted Provider operation. When the Provider supports streaming, Watt
must require a complete terminal event before accepting the semantic result and
must preserve safe response-header, first-byte, byte/event-count, elapsed-time,
and completeness evidence when the transport is interrupted.

An incomplete inference response cannot propose or execute a Tool effect. Bounded
recovery must resume from durable Attempt Reality and must not replay already
settled Tool effects. Repeated equivalent transport signatures must remain
observable for later recovery-strategy or Guardian assessment; they must not be
reported as execution-capacity waiting.

`REGRESSION_PROTECTION`

- `BUG_CLASS`: A non-streaming long-running Provider response is interrupted near a transport idle boundary before any response body bytes are delivered.
- `ROOT_CAUSE`: The DeepSeek Responses path returned HTTP 200 headers promptly, then its non-streaming chunked body was closed at approximately 60.7 seconds with no body bytes; the same request completed through SSE because events kept the Provider-side CloudFront/ELB path active. Evidence narrows ownership to that upstream Provider transport path rather than Watt's 120-second client timeout, without attributing the close to an unobserved internal component.
- `PROTECTED_INVARIANT`: Long-running Provider inference uses a complete, activity-bearing transport; partial or unterminated streams never become successful inference results.
- `PERMANENT_TESTS`: Provider contract tests cover streamed success and Tool calls, partial-stream interruption, pre-body disconnect, empty response, explicit Provider error, safe transport diagnostics, and bounded Attempt retry without duplicate effects.
- `TEST_LEVEL`: Provider contract, transport fault injection, persistence integration, and Native Executor integration.
- `GOLDEN_JOURNEY_IMPACT`: Strengthen `GJ-07 Provider or Executor Failure`; do not add a journey.

## Status

```text
REGRESSION_PROTECTION_GOVERNANCE = ADOPTED
BUG_PER_E2E_MODEL = REJECTED
INVARIANT_FIRST_MODEL = ADOPTED
GOLDEN_JOURNEY_SUITE = EVOLUTIONARY / NOT_FULLY_BUILT
FULL_REGRESSION = CLOSURE_OR_RELEASE_BOUNDARY
GUARDIAN_RISK_TO_REQUIRED_EVIDENCE = FUTURE_DIRECTION
IMPLEMENTATION_AUTHORIZED_BY_THIS_DOCUMENT = NO
```
