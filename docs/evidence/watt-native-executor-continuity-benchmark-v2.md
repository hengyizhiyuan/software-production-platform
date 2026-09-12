# Watt-native Executor Continuity Benchmark v2 Reality

Date: 2026-09-12

Amendment: `docs/architecture/watt-native-executor-qualification-amendment-v2.md`

Frozen v2 digest:
`6f04b354694d9fdd9b536d49d7879f18c136d8149d8d73a59677d0dd5abdfc97`.
The original digest `e57d664eb9dbe2988949c0cecf1bb37ab010ecdaf07808dc1921d93bcac91c57`
and its completed 36-execution result remain authoritative historical evidence.

## Current result

The first frozen v2 execution, `T5-1-B`, reached a real terminal result and
failed. The remaining 35 executions were not started because one failed B
execution already makes the all-18-B gate impossible, and continuing would spend
Provider budget without a possible positive v2 classification.

```text
T5-1-B terminal outcome:          UNABLE_TO_COMPLETE
Frozen independent verification: PASS (5 client tests, 3 server tests, both compile checks)
Exact two-repository scope:       PASS
Required injection observed:     PASS (two_repo_partial_convergence)
Provider requests:               5 completed, 0 response-unknown
v2 Provider spend:               RMB 0.04529831
Prior conservative spend:        RMB 3.69511347
Combined conservative spend:     RMB 3.74041178 / RMB 100
Human technical interventions:   0
```

Frozen scores were correctness 2, maintainability 4, scope discipline 4,
tests 4, and operability 2. Correctness and operability are material defects
because the runtime did not truthfully reach `RESULT_READY`, even though the
external checks passed.

## Failure diagnosis

The first segment wrote useful output and the injected worker loss occurred only
after the durable receipt. Recovery retained the receipt with no duplicate
inference or tool-effect digest. The recovered execution then completed all four
required files inside the exact client/server scopes.

At inference step 4 the Provider returned `CONTINUE`, proposed the final writes,
and predicted an empty residual list. The kernel accepted the empty list before
the proposed effects had been observed, so step 5 received no available tools.
The model could see the written files but could not run the still-needed pytest
and compile checks, and truthfully returned `UNABLE_TO_COMPLETE`. External frozen
verification then showed the implementation and all eight submitted tests pass.

The ordinary runtime defect has been fixed: a `CONTINUE` response now keeps tools
available after its effects, while the existing three ineffective-round bound
still prevents endless repeated checks. The earlier cumulative-receipt fix also
keeps the full settled evidence frontier in every checkpoint. Focused native
kernel and DeepSeek Adapter tests pass.

This execution remains a v2 failure. It was not deleted, relabelled as PASS, or
automatically replayed. A further benchmark version would require an explicit
qualification amendment; v2 cannot produce `CONTINUITY_QUALIFIED`.

Machine-readable evidence is retained in
`.spg/validation-evidence/native-cont-v2/results.json` and `frozen-plan.json`.
