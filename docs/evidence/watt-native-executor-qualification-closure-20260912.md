# Watt-native Executor — Qualification Closure Reality

Date: 2026-09-12

This report records the resumed qualification run against branch
`feature/spg-first-vertical-slice`. The qualified implementation was committed
as `af4ea416e426450cb3a03ba89005f398942e0520` on top of base revision
`e40f69b0c001604b9149a491695116fb2200289f`. It preserves every failed and
response-unknown Provider request. It does not claim Human Product Acceptance.

## Amendment v2 update

The explicitly authorized v2 amendment added a kernel-enforced Landlock process
domain for each Tool delivery and froze executable engineering-quality anchors.
The corrected Q39/Q40 probe now passes file-content, directory-enumeration,
control-plane, metadata, cross-domain signal, and process-reaping checks with
zero Provider requests. Historical shared-host and intermediate signal-scope
failures remain in separate evidence files.

The first revised benchmark execution `T5-1-B` then failed terminal acceptance
after five completed Provider requests. Its independent client/server tests and
compile checks all pass, but the runtime reached `UNABLE_TO_COMPLETE`; the v2
all-18-B gate is therefore impossible. The remaining 35 v2 executions were not
started. Combined conservative Provider spend is RMB 3.74041178. Full evidence is
in [watt-native-executor-continuity-benchmark-v2.md](watt-native-executor-continuity-benchmark-v2.md).

## Amendment v3 update

The authorized v3 run froze the same 36 executions under digest
`3877434d4c25e80dda179133054495e80b3be26ff0488b9f502f71ad6004d056`.
`T5-1-B` passed with perfect frozen quality scores and validated the v2 terminal
fix. `T3-1-B` then failed because a completed, metered Provider response was not
an admissible native decision, even though all output checks passed. The runner
was stopped to conserve budget; the already-started `T4-1-B` retains one
response-unknown request and one recorded technical intervention. V3 therefore
retains one PASS and two FAIL records; 33 executions were not started. Combined
conservative spend is RMB 3.88252724. Evidence:
[watt-native-executor-continuity-benchmark-v3.md](watt-native-executor-continuity-benchmark-v3.md).

## Amendment v4 update

V4 retained the same frozen qualification content under digest
`04affa90cf744deef9db257156014910ea712bad9aea28d3634e7de45f784124`.
`T5-1-B` passed with 18 independent tests, two compile checks and 4/4/4/4/4
quality. `T3-1-B` then terminated after two completed Provider responses failed
the oversized terminal-decision schema, while its repository checks passed. V4
is frozen as one PASS, one FAIL and 34 not started. It spent RMB 0.10763544 with
no response-unknown reserve; combined conservative spend through v4 is RMB
3.99016268. Evidence:
[watt-native-executor-continuity-benchmark-v4.md](watt-native-executor-continuity-benchmark-v4.md).

## Amendment v5 update

V5 ran 12 executions under digest
`e41cb81112581bf5bf252d923c28a668d1e57c4af839676b36bf733a50cee74c`.
The first eleven passed, including the former T3-1-B failure trigger and one
`deepseek-v4-pro/high` replacement. T4-1-A then failed terminal acceptance after
using the SOURCE_VECTOR mount identity as a Tool cwd in a single-mount
workspace; its files and independent checks pass. V5 remains 11 PASS, one FAIL
and 24 not started. Combined conservative spend through v5 is RMB 4.67781665,
including a retained RMB 0.06720000 response-unknown reserve. Evidence:
[watt-native-executor-continuity-benchmark-v5.md](watt-native-executor-continuity-benchmark-v5.md).

## Amendment v6 update

V6 passed T5-1-B and T3-1-B, then stopped on T4-1-B. The Tool path correction
worked, but the `deepseek-v4-pro/high` successor had one request with unknown
response and an unresolved lowercase-prefix test. The execution remains FAIL;
33 were not started. Combined conservative spend through v6 is RMB 5.02900794.
Evidence:
[watt-native-executor-continuity-benchmark-v6.md](watt-native-executor-continuity-benchmark-v6.md).

## Amendment v7 update

V7 passed its first two executions. T4-1-B then reached `RESULT_READY`, passed
33 tests and compile verification, and had no unknown response, but the quality
evaluator omitted twelve test methods nested in pytest classes and assigned a
material tests defect. V7 remains two PASS, one FAIL and 33 not started.
Combined conservative spend through v7 is RMB 5.23686778. Evidence:
[watt-native-executor-continuity-benchmark-v7.md](watt-native-executor-continuity-benchmark-v7.md).

## Amendment v8 qualified result

V8 preserved the six frozen meaningful tasks, 18 A/B pairs, 36 executions,
quality rubric, failure injections, Provider profiles and RMB 100 aggregate
hard cap under plan digest
`6bcd04af0d4eef2d951767c6d1e20ae3930e259b49da0202eae7fe4c939b481a`.
All 18 A and all 18 B executions reached `RESULT_READY`, passed their frozen
independent checks and scored 4/4/4/4/4. The three preassigned replacement B
executions used `deepseek-v4-pro/high` across three task types and passed. V8
spent RMB 1.61292174 with RMB 0.06720000 retained for one response-unknown
request; combined conservative v1-v8 spend is RMB 6.91698952. No real Provider
request was automatically retried and Human technical intervention remained
zero. Evidence:
[watt-native-executor-continuity-benchmark-v8.md](watt-native-executor-continuity-benchmark-v8.md).

## Final classification

```text
CONTINUITY_QUALIFIED
    YES

TECHNICALLY_QUALIFIED
    YES

RUNTIME_READY_FOR_HUMAN_ACCEPTANCE
    YES

HUMAN_ACCEPTED
    NOT ASSESSED
```

The v1-v7 failures remain immutable historical evidence. V8 is a separately
authorized, versioned amendment that corrected identified contract and harness
defects without rewriting any prior result. It supplies the positive release
evidence; it does not relabel earlier failed or response-unknown requests.

## Continuity benchmark

The authoritative positive result is the versioned V8 report and machine
evidence in `.spg/validation-evidence/native-cont-v8/`. It records all 18 pair
rows, 36 execution outcomes, exact profiles, source baselines, checkpoints,
recovery injections, repeated-work digests, usage, cost and timing.

- A outcomes: 18/18 PASS; B outcomes: 18/18 PASS.
- Every execution retained zero material intent or constraint drift and a
  4/4/4/4/4 quality score; every paired quality delta is 0.
- Replacement B executions T4-1-B, T3-2-B and T5-2-B passed with
  `deepseek-v4-pro/high`; all others used the frozen primary profile.
- A known cost was RMB 0.76634510; B known cost was RMB 0.84657664.
- A elapsed total was 1377.573s; B was 1367.566s. Median B-minus-A was 5.473s;
  aggregate B-minus-A was -10.007s.
- Nine successors recovered prescribed residual work. Repeated inference
  request digests were zero. Forty repeated Tool semantic-input digests were
  reads/checks; exact Git and test evidence found no duplicated unauthorized
  mutation.
- One T4-2-A response remains unknown with its full RMB 0.06720000 reserve. A
  successor continued from the proven no-effect frontier without replay.
- Combined conservative real Provider spend for all retained v1-v8 history is
  RMB 6.91698952 of RMB 100.

## Qualification closure evidence

| Case | Status | Evidence and remaining boundary |
|---|---|---|
| Q01 | PASS | Real DeepSeek native production, repair, exact Candidate, independent Verification and Runtime Commit. |
| Q02–Q11 | PASS | Contract/idempotency/lifecycle/process suites pass. Material revisions remain generation-bound and stale evidence cannot advance trust. Q08 now captures binary, tracked, untracked and ignored useful dirty input without changing the Human tree, records cache exclusion recipes and restores exact digests. Exact Provider/tool/context/source/environment/capability/usage provenance and UNKNOWN measurement behavior are retained. |
| Q12–Q28 | PASS | Both terminal/update orderings, durable controls, crash frontiers, receipt-suffix recovery, process termination, capacity/quota, compaction, model replacement and stale fencing are covered by focused cases, the 100-round allocation race and all prescribed V8 B injections. No Human mission resend or hidden salvage occurred. |
| Q29 | PASS | A real retained-volume restart preserved Work `897ad04e-ea3b-4abb-8353-856e5fa53f8a`, PWU `0350f1e1-e5f1-4a23-847a-ebc32166f4d2`, Session `1714fae5-83eb-4dbe-b9b6-6a4cb12fbdc7`, Attempt `8bc1eb43-1b20-46f3-9d22-297d9fd69f52`, generation, epoch and tree digest. Recovery used zero Provider requests. Evidence: `.spg/validation-evidence/native-cont/q29-host-reboot.json`. |
| Q30 | PASS | Unexpected loss restores exact verified pinned content only into a distinct successor workspace, with checkpoint and residual-obligation lineage. Missing/corrupt content records `LOST / RECOVERY_PROMISE_FAILED`, quarantines both materializations and invents no output. |
| Q31–Q35 | FOCUSED_PASS | Two-repository Candidate, exact Verification, PARTIAL convergence, forward recovery, drift invalidation and aggregate atomic commit pass on real Git/PostgreSQL fixtures. |
| Q36 | PASS | The PostgreSQL matrix passes for new fact, material constraint, correction, local approach request and unrelated Motive. Each retains its exact meaning/focus/impact/runtime basis; material changes require Human governance and stale active-cycle evidence is blocked, while unrelated demand becomes a separate new-Work recommendation. |
| Q37 | FOCUSED_PASS | Forged/self-issued assurance and stale evidence are rejected. |
| Q38 | FOCUSED_PASS | Traversal, hardlink, archive escape, special file, `.git` access and a descriptor-anchored directory-to-symlink race are rejected; the outside file remains unchanged. |
| Q39 | PASS | The real Landlock-per-delivery probe denies application control, metadata, public redirect origin and localhost rebinding targets at the kernel connect boundary. Provider/DB/Docker credentials are absent and an approved immutable pytest dependency works inside scoped filesystem access. Evidence: `.spg/validation-evidence/native-cont-v8/q39-q40-isolation-v3-landlock.json`. |
| Q40 | PASS | The original shared-host failure remains retained. The corrected real probe denies other-Work content/enumeration and cross-domain signals, proves holder-process reaping and permits immutable dependency reuse. |
| Q41–Q42 | FOCUSED_PASS | PWU-wide spend accounting, unknown reservations, pins, hibernation, restore and retention behavior pass focused tests. |
| Q43 | PASS | Checkpoint `ENOSPC` cannot advance the DB pointer. Tool Host preflight returns 507 before effects when its durable receipt reserve is exhausted. During an actual v8 PostgreSQL outage it executed and spooled one bounded Tool result; after PostgreSQL and Tool Host restart, the exact delivery receipt and workspace output were recovered with zero Provider requests. Evidence: `.spg/validation-evidence/native-cont-v8/q43-db-outage-spool.json`. |
| Q44 | TECHNICAL_PASS / HUMAN_PENDING | Exact Candidate/authorization/delivery identities, immutable preview artifacts and expiry/reopen behavior are deterministic. Final visual inspection and delivery acceptance remain the separate Human Product Acceptance action. |
| Q45 | FOCUSED_PASS | Publish-before-ack replay, monotonic event sequences, RESET and snapshot high-water pass. |
| Q46 | PASS | A live slow subscriber consumed ten events while a required production milestone committed in 12.759ms, then disconnected. Reconnect from sequence 10 replayed all 592 remaining durable milestones through sequence 602. Queries remain capped at 256 rows; native SSE carries durable milestones rather than a lossy text-delta queue. Evidence: `.spg/validation-evidence/native-cont-v8/q46-slow-subscriber.json`. |
| Q47 | FOCUSED_PASS | Five latency classes retain measured spans and explicit unavailable stages. |
| Q48 | PASS | 30 cold and 30 warm samples used the same source/image and a 2 vCPU / 4 GiB, network-none, read-only profile. Cold first-action p50/p95: 2.532256/2.917585 s. Warm: 1.728224/2.187867 s. Warm p50 improved 31.752%. Evidence: `.spg/validation-evidence/native-cont/q48-cold-warm.json`. |
| Q49 | PASS | Legacy/native capability contracts coexist. The router binds each handle to its immutable backend across default cutover and rollback, rejects binding/default mismatch and legacy multi-repository admission, and keeps both native PostgreSQL state and legacy readers available after rollback. Migration rollback is additive. |
| Q50 | PASS | Checkpoint bundle schema version 1 is now persisted. An unsupported version parks in non-retryable `WAITING_RESOURCE` before Provider kernel construction or Tool receipt recovery, retains its checkpoint pointer, and records zero inference/tool effects. Migration `20260912_39` completed 38→39→38→39 while preserving the original checkpoint ID and restoring version 1. |

The current non-PostgreSQL suite completed at 100% with exit code 0. The current
native runtime PostgreSQL suite completed 22/22, including Q30 and Q49; the Q36
matrix completed 5/5 in a separate isolated PostgreSQL instance. Python
compilation and `git diff --check` passed.

## Qualification fixes

The resumed run made bounded fixes without changing the frozen benchmark:

- recovered the first interrupted trial from its durable frontier rather than
  replaying it;
- made benchmark state durable and bound exact Provider model/effort profiles;
- retained response-unknown cost reservations and sanitized Provider exception
  persistence;
- enforced monotonic successor Session steps and PWU-wide resource limits;
- prevented stale heartbeat shutdown races from masking the primary failure;
- forced a terminal decision after bounded ineffective model rounds;
- repaired qualification checkpoint injection and source-layout validation;
- added descriptor-anchored symlink-race and archive/disk-full negative tests;
- added checkpoint schema versioning and an incompatible-reader fail-closed
  gate in migration `20260912_39`;
- added durable Tool Host delivery receipts, pre-effect capacity backpressure
  and receipt lookup across PostgreSQL/Tool Host restarts;
- added exact dirty-input overlay capture/restore with binary and ignored useful
  artifacts plus explicit reproducible-cache exclusions;
- added explicit lost-workspace successor recovery and truthful failure records;
- pinned active execution handles across legacy/native default changes;
- completed the five-kind Human steering and live slow-subscriber probes.

## Cutover and rollback reality

The native and legacy implementations remain distinct and capability-described.
An operational router rehearsal started a real native PostgreSQL execution,
changed the default to legacy, retained observation of the native handle,
rejected an incompatible new native admission, admitted/read a legacy handle,
then rolled the default back while both readers remained valid. The migration
rehearsal rolled checkpoint schema 39→38→39 without losing the v1 checkpoint.
Historical failed benchmark versions remain readable and do not participate in
new admissions.

## Human acceptance runtime reality

The isolated environment was destructively reset only within its own Compose
project and rebuilt from the current source overlay:

```text
Compose project:  watt-native-human-acceptance-v32
UI:               http://127.0.0.1:8042/app
API:              http://127.0.0.1:8042
Seed Work:        2e92e1eb-6aa7-4749-8c60-1527afe45197 (DRAFT)
Source basis:     af4ea416e426450cb3a03ba89005f398942e0520
Provider profile: deepseek-flash / high
```

The current seeded Work is `2e92e1eb-6aa7-4749-8c60-1527afe45197` (`DRAFT`),
the migration is `20260912_39`, and all five services are running. The exact
final Git revision is reported in the Runtime Reality Report. Reset is
limited to this Compose project: `down -v --remove-orphans`, followed by
`--profile provider up -d --no-build` with the same three Compose files. The
8040 service and all retained v1-v8 qualification environments were not
modified by this reset.

Human Product Acceptance remains a separate Human action and has not been
performed or inferred.
