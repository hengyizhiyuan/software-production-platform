# Watt-native Executor Qualification Amendment v7

Date: 2026-09-12

## Authority and retained history

The Human Qualification Owner's bounded, versioned defect-closure authority
continues. V7 retains every v1-v6 outcome. V6 remains two PASS, one FAIL and 33
not started, including its `deepseek-v4-pro/high` response-unknown request and
RMB 0.20880000 reserve.

Combined conservative Provider spend before v7 is RMB 5.02900794.

## Authorized correction

A Provider transport failure can leave a request response-unknown while proving
that no Tool proposal was received and no Tool effect began. The worker now
parks this state as non-retryable `WAITING_RESOURCE` at the latest checkpoint
instead of destroying the Work as `UNABLE_TO_COMPLETE`.

The qualification controller may create one successor execution from that
retained no-effect frontier. It preserves the unknown request and cost reserve,
copies the exact workspace, adds an explicit recovery fact, and sends a new
decision request for residual obligations. It does not reuse the old request
identity or claim knowledge of the missing response. A second response-unknown
boundary in the same trial stops the trial.

Decision-schema rejection, known HTTP failures and effect uncertainty retain
their existing policies. Tool authority and independent verification are
unchanged.

## Frozen v7 plan

V7 preserves the six tasks, seed, 18 A/B pairs, 36 execution order, injections,
checks, scoring and replacement positions. Primary remains
`deepseek-flash/high`; replacement remains `deepseek-v4-pro/high` only at
T3-2-B, T4-1-B and T5-2-B.

Execution is sequential, stops at the first failed execution, and does not
automatically retry a real Provider request. The combined v1-v7 spend cap is RMB
100. V7 has isolated runtime, database, volumes, workspace, evidence and port.
