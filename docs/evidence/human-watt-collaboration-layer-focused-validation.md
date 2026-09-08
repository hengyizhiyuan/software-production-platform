# Human–Watt Collaboration Layer Focused Validation

Status: **IMPLEMENTED / DETERMINISTIC VALIDATION PASS / REAL PROVIDER PROOF PASS**

Closure: **VALIDATION COMPLETE — PENDING ARCHITECTURE LEAD REALITY REVIEW**

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
