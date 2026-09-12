# Watt-native Executor Runtime — Final Technical Closure

Date: 2026-09-13

This is the authoritative current-status record for the Watt-native Executor
technical program. Architecture specifications and earlier evidence retain
their historical facts; where a historical status differs, this record and the
final qualification evidence describe current Reality.

## Final classification

```text
IMPLEMENTATION_COMPLETE
TECHNICALLY_QUALIFIED
CONTINUITY_QUALIFIED
HUMAN_ACCEPTANCE_DEFERRED_BY_HUMAN_GOVERNANCE
READY_FOR_LATER_HUMAN_JOURNEY_INTEGRATION
TECHNICAL_PHASE_CLOSED
```

This classification does not assert `HUMAN_ACCEPTED`.

## Qualified Repository Reality

- Branch: `feature/spg-first-vertical-slice`.
- Qualified repository revision reviewed for closure:
  `d51dadf5dabcbd1d69ea5d4391be7e318f8fe11e`.
- Executable qualification implementation revision:
  `af4ea416e426450cb3a03ba89005f398942e0520`. The following `d51dadf`
  commit changes only evidence wording.
- Migration current/head: `20260912_39`.
- Native PWU/binding contract schema: version 2.
- Supported checkpoint bundle schema: version 1; incompatible versions park
  fail-closed before Provider or Tool recovery.
- Provider: DeepSeek.
- Primary qualified profile: `deepseek-flash / high`.
- Compatible replacement profile: `deepseek-v4-pro / high`.

The SOT-only closure commit containing this record is reported by exact hash in
the final closure report after commit. It does not change the qualified
executable source.

## Core technical evidence

- Q01 completed real native DeepSeek software production through bounded
  inference, Tool Host effects, independent checks, Candidate and governed
  Runtime Commit.
- Provider/model identity is an admitted replaceable resource. The OpenAI to
  DeepSeek migration changed the adapter and exact profile without redesigning
  the Native Kernel, PWU, Session, Checkpoint or recovery semantics.
- The broad non-PostgreSQL regression suite passed; the native PostgreSQL suite
  passed 22/22 and the five-kind Human steering matrix passed 5/5.
- Q01–Q50 technical requirements are closed. Q44's technical identity,
  preview and authorization mechanics pass; the product-level Human decision
  is intentionally deferred.
- Continuity Benchmark v8 completed all 18 A/B pairs and 36 real executions.
  A and B each passed 18/18, every execution reached `RESULT_READY`, every
  independent check passed, every score was 4/4/4/4/4 and every paired quality
  delta was zero.
- Three preassigned B executions across three task types successfully used
  `deepseek-v4-pro / high`; the remaining qualified trials used
  `deepseek-flash / high`.
- Nine successor recoveries preserved residual obligations. No Provider
  inference request digest was repeated. Repeated Tool semantic-input digests
  were reads/checks and caused no duplicated unauthorized mutation.
- Multi-repository CandidateVector, independent Verification, truthful
  `PARTIAL`, forward recovery, exact authorization, per-target convergence and
  aggregate Runtime Commit passed.
- Landlock execution isolation, hostile filesystem/network boundaries,
  cross-Work separation, durable Tool receipts, database-outage recovery,
  backpressure and incompatible-checkpoint fail-closed behavior passed.
- Fair queue/allocation scheduling, worker fencing, resource accounting,
  retained-volume recovery and cold/warm measurements passed their prescribed
  qualification evidence.
- The legacy/native router cutover and rollback rehearsal kept existing handles
  pinned to their original backend and retained both readers. Migration
  `39→38→39` preserved checkpoint identity and restored the supported reader.

The authoritative details are in the
[Qualification Closure Reality](watt-native-executor-qualification-closure-20260912.md)
and [Continuity Benchmark v8](watt-native-executor-continuity-benchmark-v8.md).
All failed and response-unknown v1–v7 qualification attempts, including the P2
HTTP 400 history, remain immutable evidence and are not rewritten as success.

## Human governance disposition

Human Product Acceptance is
`DEFERRED_BY_HUMAN_GOVERNANCE` until the later system-wide Human Journey,
architecture/data-model calibration and UX/UI reconstruction phase. This is an
intentional governance deferral, not a technical qualification gap. The
retained acceptance environment is engineering evidence and does not imply a
Human acceptance decision.

The retained engineering environment is Compose project
`watt-native-human-acceptance-v32`, available at
`http://127.0.0.1:8042/app`, with isolated database and runtime volumes. It may
be stopped without deleting evidence by running `docker compose stop` against
that project and the same three Compose files. A destructive reset is scoped
only to that named project with `down -v --remove-orphans`, followed by
`--profile provider up -d --no-build` with `compose.yaml`,
`compose.native-executor.yaml` and
`compose.native-executor.human-acceptance.yaml`. No historical qualification
project or volume is part of that reset scope.

## Architecture truths retained at closure

1. PWU production continuity does not require continuous execution.
2. `UNKNOWN` does not authorize blind replay.
3. Session, Attempt, Step and Effect remain distinct.
4. Provider/model is a replaceable inference resource, not Executor identity.
5. OpenAI to DeepSeek migration did not require Native Kernel, PWU, Session,
   Checkpoint or recovery redesign.
6. Real model replacement succeeded inside continuity qualification.
7. Execution Queue and Capacity Scheduling are part of Watt's production model.
8. Multi-repository production is first-class.
9. Executor emits `RESULT_READY`, not `TRUSTED`.
10. Verification and future Guardian remain independent from Executor.
11. Human Authority remains distinct from Verification and Product Acceptance.
12. Platform qualification cost is an internal Watt production-system cost;
    each user is not required to repeat the platform benchmark.

## Non-blocking future directions

- WIC model decoupling and API-based Provider migration, with DeepSeek as the
  first target Provider.
- Later Human Journey and UX integration.
- Future Guardian integration through the independent assurance boundary.
- Future ECF integration through the governed context boundary.
- Later distributed and capacity-scheduling evolution behind the qualified
  queue/allocation contracts.

These directions do not reopen the Watt-native Executor technical phase. The
recommended next program step is **WIC Model Decoupling / API-based Provider
Migration with DeepSeek as the first target Provider**.
