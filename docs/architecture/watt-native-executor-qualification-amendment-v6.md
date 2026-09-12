# Watt-native Executor Qualification Amendment v6

Date: 2026-09-12

## Authority and retained history

The Human Qualification Owner's authorization for future bounded, versioned
ordinary defect closure applies. V6 retains every v1-v5 result. V5 remains 11
PASS, one FAIL and 24 not started. Its RMB 0.06720000 conservative unknown
reservation is retained even though the associated injected failure is now
known to have occurred before request send.

Combined conservative Provider spend before v6 is RMB 4.67781665.

## Authorized corrections

V5 exposed two harness/context defects:

1. SOURCE_VECTOR exposes container identity paths while Tool arguments use a
   workspace-relative namespace. The inference context now includes a
   `TOOL_PATH_CONVENTION` fact. A single mount uses `.` as cwd and unprefixed
   file paths; multiple mounts use their declared Tool path prefixes. Provider
   instructions explicitly forbid deriving Tool arguments from container paths.
2. A deterministic benchmark capacity/quota injection that fires before request
   send now carries `request_sent=false` into durable step evidence. Unknown-cost
   reconciliation excludes only that proven no-send case. Actual HTTP or
   transport ambiguity remains conservatively response-unknown.

Neither correction broadens filesystem grants, changes Tool Host enforcement,
weakens verification, or changes Product intent.

## Frozen v6 plan

V6 preserves the exact six tasks, seed, 18 A/B pairs, 36 execution order,
injections, verification, scoring anchors and replacement positions from v5.
Primary is `deepseek-flash / high`; replacement is `deepseek-v4-pro / high` only
at T3-2-B, T4-1-B and T5-2-B.

Execution remains sequential with no automatic retry of real Provider requests.
The combined v1-v6 Provider spend may not exceed RMB 100. V6 has its own
Compose project, PostgreSQL and checkpoint volumes, workspace, evidence
directory and port.
