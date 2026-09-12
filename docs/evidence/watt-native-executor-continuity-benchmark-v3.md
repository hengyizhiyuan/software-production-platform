# Watt-native Executor Continuity Benchmark v3 Reality

Date: 2026-09-12

Amendment: `docs/architecture/watt-native-executor-qualification-amendment-v3.md`

Frozen digest:
`3877434d4c25e80dda179133054495e80b3be26ff0488b9f502f71ad6004d056`.
V1 and v2 plans, outcomes and costs remain unchanged.

## Result

V3 is failed and stopped. Three frozen executions have final ledger records; 33
were not started after the all-18-B gate became impossible.

| Execution | Terminal | Frozen checks | Score | Provider evidence | Outcome |
|---|---|---|---|---|---|
| T5-1-B | RESULT_READY | 11 tests plus four repository-isolated checks pass | 4/4/4/4/4 | 6 completed, 0 unknown | PASS |
| T3-1-B | UNABLE_TO_COMPLETE | 3 tests and compile pass | 2/4/4/4/2 | 3 completed, 0 unknown; final observed decision rejected by Adapter | FAIL |
| T4-1-B | STOPPED | Required files incomplete | 0/4/2/0/0 | 1 completed, 1 response-unknown | FAIL/CONTROLLER STOP |

`T4-1-B` began immediately after `T3-1-B` completed. The qualification
controller interrupted the runner to avoid further spend after v3 could no
longer pass. That interruption is recorded as one technical intervention. The
in-flight Provider request was not replayed and retains its full conservative
reservation.

Provider cost:

```text
Prior v1 + v2 conservative spend: RMB 3.74041178
V3 known spend:                   RMB 0.07491546
V3 response-unknown reservation: RMB 0.06720000
Combined conservative spend:     RMB 3.88252724 / RMB 100
Remaining authorized ceiling:    RMB 96.11747276
```

## Findings and bounded fixes

The v2 terminal-decision fix is validated by `T5-1-B`: the same first frozen
injection now retained its tool frontier, completed both repositories, executed
all verification and reached `RESULT_READY` with no duplicated request/effect
digest or technical Human intervention.

`T3-1-B` exposed the next independent boundary. DeepSeek returned a completed,
metered response that could not be converted into an admissible native decision.
The Adapter recorded the response and usage, did not execute any invalid proposal,
and did not replay the request, but the Worker converted the Adapter error directly
to `UNABLE_TO_COMPLETE`. All frozen output checks subsequently passed.

DeepSeek's Responses API is stateless and does not store responses, so the
response ID cannot retrieve the original payload for post-hoc inspection. Its
official API also warns that function-call arguments may not be valid JSON and
must be validated by the client.

The following ordinary runtime fixes were completed after preserving the v3
failure:

- observed decision-validation failures now carry a stable, payload-free reason
  code;
- the kernel checkpoints a synthetic `PROVIDER_DECISION_REJECTION` receipt and
  permits one corrected next decision with the rejection code in context;
- the original request is never replayed and no invalid Tool effect starts;
- a second rejected decision terminates `UNABLE_TO_COMPLETE`;
- durable inference audit and future benchmark ledgers retain the stable reason
  code without Provider response content or credentials.

The full non-integration suite, focused kernel/Adapter tests, compilation and
`git diff --check` pass after the fix. V3 remains failed and was not rerun.

Machine-readable evidence is retained in
`.spg/validation-evidence/native-cont-v3/results.json` and `frozen-plan.json`.
