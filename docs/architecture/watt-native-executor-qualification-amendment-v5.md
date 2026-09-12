# Watt-native Executor Qualification Amendment v5

Date: 2026-09-12

## Authority and retained history

The Human Qualification Owner authorized v4 and future bounded, versioned
closure for ordinary implementation defects. V5 retains v1 through v4 as
immutable qualification evidence. In particular, v4 remains one PASS, one FAIL
and 34 not started; no v4 outcome is replayed or reclassified.

The combined conservative Provider spend before v5 is RMB 3.99016268.

## Authorized correction

V4 showed that the DeepSeek Adapter required a terminal response to reproduce
Watt-owned state, including the current WorkingPlan and the complete native
InferenceResponse shape. That boundary is corrected as follows:

1. API Function Calling remains the only way to propose `CONTINUE` and Tool
   effects.
2. Provider text is constrained to the terminal fields `action`, `summary`,
   `result_claim` and `residual_obligations`.
3. Watt supplies the already-authoritative current WorkingPlan when it builds
   the native response.
4. `RESULT_READY` still requires a non-null claim; text `CONTINUE` remains
   invalid; downstream independent Verification is unchanged.
5. A rejected decision records only stable validation locations and types, never
   raw Provider output or credentials. One corrected next decision remains the
   hard limit.

This correction does not change Work intent, Tool authority, effect execution,
recovery semantics, acceptance checks, quality scoring, or Provider profiles.

## Frozen v5 plan

V5 preserves the exact six tasks, randomization seed, 18 A/B pairs, 36
execution order, injection assignment, independent acceptance checks, quality
anchors and model-replacement positions from v4. Primary remains
`deepseek-flash / high`; replacement remains `deepseek-v4-pro / high`, assigned
only to T3-2-B, T4-1-B and T5-2-B.

Execution is sequential with no automatic retry of a real Provider request. The
combined v1-v5 conservative spend must remain at or below RMB 100. V5 uses an
independent Compose project, PostgreSQL database/volume, runtime port,
workspace, checkpoints and evidence directory. Earlier runtime state is not v5
execution context.
