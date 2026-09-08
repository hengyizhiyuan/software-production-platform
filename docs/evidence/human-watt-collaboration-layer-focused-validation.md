# Human–Watt Collaboration Layer Focused Validation

Status: **IMPLEMENTED / DETERMINISTIC VALIDATION PASS / REAL PROVIDER PROOF PASS**

Closure: **VALIDATION COMPLETE — PENDING ARCHITECTURE LEAD REALITY REVIEW**

Experience calibration v2: **FOCUSED DETERMINISTIC VALIDATION PASS / REAL
PROVIDER V2 PROOF PASS / HUMAN PRODUCT ACCEPTANCE PENDING**
Experience refinement v2.1: **FOCUSED VALIDATION PASS / REAL PROVIDER V2.1
PROOF PASS / HUMAN PRODUCT ACCEPTANCE PENDING**


## Scope

This evidence covers the Human–Watt conversation/Turn foundation, asynchronous
processing, SSE response delivery, Guided Design facilitation, seed schema
selection, PostgreSQL persistence, restart reconstruction, and the mandatory
Human scenario:

> 我想做一个运营管理平台。

## Deterministic evidence

- focused Python contract tests: 17 passed;
- browser-state/UI tests: 23 passed;
- affected PostgreSQL WIC/Guided Design tests: 31 passed, 3 protected real
  Provider tests skipped;
- migration from an empty PostgreSQL database through `20260908_28`: passed;
- migration round trip `20260908_28 -> 20260908_27 -> 20260908_28`: passed;
- final migration state: `20260908_28 (head)`;
- Python compile/import, Node syntax, lock check, and `git diff --check`: passed
  at the recorded validation point.

Deterministic coverage proves persisted Human/Watt messages, Turn lifecycle,
failure recording, SSE status/delta/completion events, three seed schemas,
schema matching, stage/focus/rationale/progress projections, restart
reconstruction, and the absence of automatic Work or production admission.

## Real Provider evidence

### Harness attempt

The first attempted real proof did not produce valid evidence because the test
harness passed an incorrect keyword to its local polling helper. Service
shutdown waited for any already-started background processing, but the
disposable database was removed without retaining the terminal Provider result.
It must not be reported as a pass.

### Explicitly authorized proof

After the harness correction, the Human explicitly authorized exactly one
additional real Codex Provider Turn with no retry or Resume. The Turn used the
mandatory Chinese scenario, a read-only ephemeral Codex thread, and a fresh
disposable PostgreSQL database.

Observed terminal application fact:

```text
InteractionTurn = FAILED
```

The assertion did not include the persisted `failure_code` and
`failure_message`, and the disposable database was removed after the run.
Therefore the exact Provider/adapter failure reason was not retained in test
output.

## Evidence extraction improvement

The validation harness now detects a terminal `FAILED` Turn before its success
assertions and before fixture cleanup. It builds a sanitized report containing
the Turn ID, status, failure code/message, and available timestamps; writes the
report atomically to an explicit `SPG_REAL_PROVIDER_EVIDENCE_PATH` or the
Git-ignored `.spg/validation-evidence/` default; and embeds the same JSON in the
pytest failure output.

Credential-shaped values, authenticated URL user information, Provider
thread/turn/request identifiers, and user-home identity are redacted. Provider
and model metadata are intentionally excluded. A deterministic harness test
proves field completeness, UTF-8 persistence, redaction, and file creation.
This improvement does not alter `InteractionTurn`, the Provider contract, or
Guided Design behavior. No additional Provider Turn is authorized or executed
by this record, and the prior real proof remains failed.

### Model compatibility and final proof

Two configuration-level compatibility failures remain preserved as historical
evidence: `gpt-6-astra` required a newer Codex runtime, and
`gpt-5.3-codex` was not supported by the current ChatGPT authentication
channel. Model selection remained configuration-driven. The compatible
`gpt-5.6-sol` model subsequently reached the complete application path; that
run exposed one validation-harness-only mismatch between the obsolete
`design_facilitation_guidance` assertion and the authoritative
`design_facilitation_strategy` projection. Product behavior and validation
criteria were unchanged when the harness field reference was corrected.

After that correction, one final explicitly authorized real Provider Turn ran
with no retry and no Resume. The sanitized success evidence records:

- input: `我想做一个运营管理平台。`;
- Provider model: `gpt-5.6-sol`;
- Turn status: `COMPLETED`;
- schema: `watt:guided-design:general-product-system` version `0.1`;
- design stage: `Motive, users, and problem`;
- next focus: clarify why the product or system should exist and for whom;
- focus rationale: a solution direction is unsafe until the beneficiary and
  problem are explicit;
- facilitation strategy: `CLARIFY`;
- persisted conversation message count: 2.

The local sanitized artifact is
`.spg/validation-evidence/human-watt-provider-proof-gpt-5.6-sol-20260908.json`.
It is retained outside Git and contains no credentials, authentication state,
Provider thread identifier, or Provider turn identifier.

## Governance and production guard

- no retry;
- no Provider Resume;
- no second concurrent Turn;
- no Work admission path invoked;
- no Run, Plan, PWU, Attempt, production artifact, Verification, Candidate,
  Repository Integration, Runtime Commit, or Trusted Baseline mutation;
- disposable proof database removed;
- existing Watt Runtime databases and histories untouched.

The mandatory real Provider scenario is proven. Deterministic validation and
the real Provider proof are both PASS. Architecture closure remains subject to
an Architecture Lead Reality Review; this evidence does not self-admit that
separate authority decision.

## Experience calibration v2 evidence

The v2 calibration replaces completion-time response slicing with real
Provider notification consumption. Focused deterministic evidence proves:

- the structured Provider schema emits the Human-facing natural response first;
- fragmented JSON, whitespace, escaped newlines, Chinese Unicode, and
  supplementary Unicode characters are decoded incrementally;
- only Human-facing response text is exposed, never the structured assessment
  envelope;
- response content is observable while an Interaction Turn is still
  PROCESSING;
- the final persisted Watt message retains the streamed prefix and adds the
  existing Design Schema path/stage/focus projection;
- late SSE consumers reconcile against the persisted final message;
- restart reconstruction and the absence of automatic Work/production facts
  remain unchanged;
- the Provider instruction receives the matched ordered Design Schema and
  requires active design-path explanation, focus selection, rationale,
  proactive guidance, known-information reuse, and at most one material
  question.

Focused results at this validation point:

- WIC Provider contract/stream tests: **6 passed**;
- WIC PostgreSQL persistence/restart/SSE tests: **9 passed, 2 real Provider
  tests skipped by authorization gate**;
- affected Guided Design and governed Work integration tests: **10 passed**;
- frontend/state tests: **23 passed**;
- Python compile/import: **PASS**.

One attempted launch of the v2 real proof was rejected before process creation
because the current mission did not explicitly authorize repository-context
egress to Codex/OpenAI. No Provider Thread or Turn was created and no data was
sent. This is a pre-execution authorization boundary, not a Provider or product
failure.

After explicit Human authorization, exactly one v2 real Provider Turn ran with
gpt-5.6-sol, no retry, and no Resume. The sanitized evidence records:

- Interaction Turn: **COMPLETED**;
- incremental Human-facing response observed: **true**;
- response delta observed before terminal state: **true**;
- streamed response matches the persisted final-message prefix: **true**;
- schema: **General Product/System Design v0.1**;
- stage: **Motive, users, and problem**;
- next focus: clarify why the product/system should exist and for whom;
- focus rationale: downstream direction is unsafe before beneficiary and
  problem are explicit;
- design path explanation present: **true**;
- conversation messages persisted: **2**.

The local sanitized artifact is
.spg/validation-evidence/human-watt-collaboration-v2-real-provider-20260908.json.
It remains outside Git. The disposable test database was cleared normally; no
Work, PWU, production Run, Runtime Commit, or Trusted Baseline mutation was
created.

This proves the real Provider transport, incremental-delivery path, schema
selection, focus projection, and durable final-message alignment. It does not
self-declare Human Product Acceptance; a Human must still judge whether the
guidance feels sufficiently active and useful.

## Experience refinement v2.1 evidence

The v2.1 refinement closes the two implementation gaps identified by Human
Acceptance while preserving Human Acceptance as a separate authority decision.

### One assistant-message lifecycle

- submitting a Turn creates one transient Watt message in the conversation;
- SSE deltas update that same message rather than a separate processing area;
- the persisted Watt message for the same Turn replaces the transient
  projection at completion;
- the Shared Understanding response surface is hidden when conversation owns
  the visible Watt response;
- the bounded application stream buffer reconciles to the exact persisted
  response, without becoming durable Truth.

Deterministic frontend coverage proves same-Turn replacement and no duplicate
rendering. PostgreSQL/SSE coverage proves the concatenated emitted deltas equal
the final persisted Watt message.

### Progressive design-lead behavior

The Provider policy now requires progressive disclosure, reuse of persisted
Conversation Reality, concise approach/stage explanation, one next design
action, useful direction or trade-offs when supported, and at most one
highest-impact unresolved question. The deterministic completion wrapper no
longer appends the complete Design Schema path to the first response.

Focused validation at this checkpoint:

- Node syntax: **PASS**;
- frontend/state tests: **24 passed**;
- WIC Provider and UI contract tests: **14 passed**;
- Guided Design plus WIC PostgreSQL/SSE tests: **15 passed, 2 real Provider
  tests skipped by the authorization gate**;
- governed Work/WIC regression: **24 passed, 1 skipped**;
- no Work or production fact created.

An initial real-proof launch was rejected before process creation because
repository-context egress had not yet been explicitly authorized. No data was
sent and no Provider Thread or Turn was created. After explicit Human
authorization, exactly one real Provider Turn ran with `gpt-5.6-sol`, no retry,
and no Resume. The sanitized evidence records:

- Interaction Turn: **COMPLETED**;
- incremental response and pre-terminal delta observed: **true**;
- streamed response equals persisted final response: **true**;
- schema: **General Product/System Design v0.1**;
- stage: **Motive, users, and problem**;
- facilitation strategy: **CLARIFY**;
- progressive disclosure: **true**;
- next design action present: **true**;
- persisted conversation messages: **2**.

The local sanitized artifact is
`.spg/validation-evidence/human-watt-collaboration-v2.1-real-provider-20260908.json`.
It remains outside Git and contains no credentials. The disposable proof
database contains no Work, PWU, production Run, Runtime Commit, or Trusted
Baseline mutation. This is real product-path evidence, not Human Product
Acceptance; that judgment remains pending.
