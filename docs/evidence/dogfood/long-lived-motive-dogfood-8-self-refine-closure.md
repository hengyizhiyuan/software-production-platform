# Long-lived Motive Dogfood #8 — Bounded Self-refine Closure

## Preserved Historical Runtime

The original `watt-motive-dogfood-8` Runtime remains immutable at source
revision `13e5959e71b855da040955eb514ef126e6976395` and tree
`03f7f169a96d3320c7a94d42981e011d17271a7c`:

```text
Work                                  fe19d645-9720-4858-bfaa-a86349b1b946
Work mode / condition                 LONG_LIVED_STEERING / READY
Current Step                          DESIGN / CURRENT
Provider Threads / Turns              1 / 1
Provider terminal / wire validation   COMPLETED / PASS
SemanticStepResultCandidate           CREATED
Application admission                 FAIL
SemanticStepResult                    0
Steering Decisions                    0
Run / PWU / Attempt / Report          0 / 0 / 0 / 0
Runtime Commit                        0
Repository                            clean at the Trusted Baseline
```

The exact first divergence occurred while materializing the advisory semantic
production proposal. The Provider wire schema admitted the root-wide
`tests/**` allowed area, but `RepositoryChangeProposal` correctly rejected it
with `Change Proposal cannot use broad source/test-root fallback`. The
historical Runtime was not retried, repaired, transitioned, or mutated.

## Root Causes and Corrections

The bounded self-refine effort corrected four implementation gaps without
changing the admitted architecture:

1. `SemanticBoundedRepositoryArea` now rejects root-wide `src/**` and
   `tests/**` values at the Provider wire boundary while retaining nested
   bounded areas.
2. The Codex Executor image now installs the locked test extra because the
   independent contract-driven verifier executes typed `PYTEST_TARGET`
   obligations inside that image.
3. The semantic Turn remains `deny_all + read_only` and consumes only the
   persisted `repository_tree_paths` and `context_materials`; it does not
   request container-nested repository tooling or gain `full-access`.
4. A Steering-enabled Work treats an ORCH transition limit as the end of one
   finite activation, not a production failure. It schedules another bounded
   activation from reconstructed Reality, while `NO_SAFE_PROGRESS` and
   infrastructure failure remain fail-closed.

Existing validation covered the Provider wire and repository proposal
contracts separately, ran pytest from a richer host test environment, and used
shorter verification chains. It therefore did not exercise the exact
cross-contract Dogfood payload, the deployed verifier image dependency, or a
production cycle whose eight Verification obligations exceeded one ORCH
activation budget.

## Self-refine Iterations

```text
Validation 1  excluded: active repository still resolved to the old committed source
Validation 2  semantic/PLAN-1B/SPG/Executor PASS; independent pytest unavailable
Validation 3  Provider conservatively returned governed UNRESOLVED from bounded context
Validation 4  attempted read-only repository tooling; Docker bwrap namespace unavailable
Validation 5  semantic/Executor/Completion PASS; 7/8 Verification PASS, ORCH bound reached
Validation 6  complete fresh PASS to legitimate Candidate Authorization boundary
```

Every material boundary moved forward. No correction failed three consecutive
times at the same boundary.

## Final Fresh Real Evidence

Validation 6 used disposable revision
`446e7f2c78e5f0af5e2b13f273dd5d34c6f233c1` and tree
`d0777e015028857ec6194fa27d77834b74f901e2`:

```text
Work                                   dba7450f-9c1f-454d-b5f3-2a5a7c3daa46
SemanticStepResult                     47225012-5ce2-415e-8de9-3b458da946e9
Semantic Provider Thread / Turn        01a07591-e817-79b2-bb81-1b2f35962294 / 01a07591-e942-71c1-b413-9c00b3e87aa3
Semantic result                        DESIGN_DIRECTION / WITHIN_AUTHORITY / completion satisfied
DESIGN transition                      AUTO_CONTINUE to PRODUCE
PLAN-1B                                ONE_PWU_FIT
Run / PWU                              1 / 1
Attempt / generation / retry_of        1 / 1 / none
Outer Dispatch / aggregate Report      1 / 1
Executor Provider Thread / Turn        01a07592-bb66-7b00-807c-5cb3e12d868a / 01a07592-c145-75c2-8717-88d22242af19
Internal Provider Turns                1
Executor outcome                       RESULT_READY / SUCCESS
Observation / Completion               1 / PRODUCED
Independent Verification               8 / 8 PASS
Candidate                              dd1ae5e7-29a7-58d5-91f8-97158ebd91c5 / SEALED
Authorization / Integration / Commit   0 / 0 / 0
Final Work boundary                    NEEDS_ATTENTION / exact Candidate Authorization
```

The eight independent PASS records were `PATH_SCOPE`, `GIT_DIFF_CHECK`,
`PYTHON_COMPILE`, two typed import checks, two typed pytest targets, and one
typed Node test target. The sealed Candidate binds proposed commit
`e20715dac196f3c977bbb46c35adc1d3e16c138d` and tree
`78be8ae2ed42ebe0f7a8b5996d1e6dcadd11b367` to the exact source Baseline.

The one Attempt changed exactly the nine admitted API/Web/test targets with
118 insertions and no out-of-scope path. Its `git diff --check` passed. The
authoritative repository remained clean at the original disposable Trusted
Baseline. Candidate Authorization was not bypassed.

## Closure and Preserved Finding

```text
DOGFOOD #8 BOUNDED SELF-REFINE                       PASS
SEMANTIC_PROVIDER_PRODUCTION_SCOPE_COHERENCE_GAP    RESOLVED
INDEPENDENT_VERIFICATION_DEPENDENCY_GAP             RESOLVED
SEMANTIC_CONTAINER_CONTEXT_GAP                      RESOLVED
ORCH_BOUNDED_CONTINUATION_GAP                       RESOLVED

SEMANTIC_EXECUTION_OBSERVABILITY_GAP
    CONFIRMED / PARTIALLY MITIGATED / OPEN

Duration-aware PWU sizing / capacity-aware decomposition
    DEFERRED / NOT PART OF THIS CLOSURE CHECKPOINT
```

Provider output remained advisory; governed semantic admission, DESIGN
non-mutation, Work/Production admission separation, Authority, PLAN-1B,
single-PWU/Attempt semantics, independent Verification, Candidate
Authorization, and Runtime Commit boundaries remained intact. This evidence
does not authorize integration and does not declare a new Core Closure.
