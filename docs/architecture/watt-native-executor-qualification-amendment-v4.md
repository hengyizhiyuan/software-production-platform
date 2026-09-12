# Watt-native Executor Qualification Amendment v4

Date: 2026-09-12

## Authority and retained history

The Human Qualification Owner authorized v4 and future bounded versioned closure
for ordinary implementation defects, provided every failed version remains
evidence and the frozen tasks, profiles, gates and combined RMB 100 cap do not
change.

V4 retains without reclassification:

- v1: 36 executions, conservative RMB 3.69511347;
- v2: failed `T5-1-B`, RMB 0.04529831;
- v3: one PASS, two FAIL, including RMB 0.06720000 response-unknown reserve.

The combined conservative Provider spend before v4 is RMB 3.88252724.

## Authorized correction

An observed Provider response that cannot be converted to an executable native
decision no longer immediately destroys otherwise valid Work:

1. the Adapter validates the response and emits a stable payload-free rejection
   reason before any Tool effect starts;
2. the kernel records the metered inference failure and checkpoints a synthetic
   `PROVIDER_DECISION_REJECTION` receipt;
3. the next request contains that new receipt and asks for one corrected decision,
   so it is not a replay of the rejected request;
4. a second rejected decision terminates `UNABLE_TO_COMPLETE`.

Transport-unknown requests are never replayed. Invalid Tool proposals never
execute. Provider content and credentials are not persisted in qualification
evidence.

## Frozen v4 plan

V4 preserves the exact six tasks, randomization seed, 18 A/B pairs, 36 execution
order, injection assignment, acceptance checks, quality anchors and model
replacement positions from v3. Profiles remain `deepseek-flash / high` and
`deepseek-v4-pro / high`, with replacement only in T3-2-B, T4-1-B and T5-2-B.

Execution is sequential. The ledger includes all prior conservative spend before
reserving each next request against the combined RMB 100 cap. V4 uses a new
database, workspace, checkpoint volume, evidence directory, Compose project and
port. Earlier runtime state is never used as v4 execution context.

All original Qualification Contract and Amendment v2 quality, safety, continuity
and comparison gates remain mandatory. Failed v4 executions remain failures.
