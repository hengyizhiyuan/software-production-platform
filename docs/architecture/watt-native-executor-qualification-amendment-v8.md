# Watt-native Executor Qualification Amendment v8

Date: 2026-09-12

## Authority and retained history

The Human Qualification Owner's bounded, versioned defect-closure authority
continues. V8 retains every v1-v7 result. V7 remains two PASS, one FAIL and 33
not started, including its frozen zero-test quality score.

Combined conservative Provider spend before v8 is RMB 5.23686778.

## Authorized correction

The frozen quality contract counts submitted Python `test_*` definitions. V7's
evaluator traversed only module-level AST nodes and therefore omitted valid
pytest methods inside test classes. V8 traverses the complete AST, counting
function and async-function test definitions at any class nesting level.

The minimum test counts, task content, external pytest execution, score anchors
and material-defect threshold are unchanged. V7 is not rescored.

## Frozen v8 plan

V8 preserves the exact six tasks, seed, 18 A/B pairs, 36 execution order,
injections, independent checks, quality anchors and replacement positions.
Primary remains `deepseek-flash/high`; replacement remains
`deepseek-v4-pro/high` only at T3-2-B, T4-1-B and T5-2-B.

Execution is sequential, stops on the first failed execution, and never
automatically retries a real Provider request. Combined spend cannot exceed RMB
100. V8 uses isolated runtime, database, volumes, workspace, evidence and port.
