# Watt-native Executor Qualification Amendment v2

Date: 2026-09-12

## Authority and retained history

This amendment was explicitly authorized after the original continuity benchmark
closed. It does not edit, discard, or reclassify that run. The original plan
digest remains
`e57d664eb9dbe2988949c0cecf1bb37ab010ecdaf07808dc1921d93bcac91c57`;
its 18 A/B pairs, 36 executions, failures, response-unknown requests, and
conservative RMB 3.69511347 spend remain historical qualification facts.

The revised run is a new benchmark version because two pre-output contract
conditions have changed:

1. untrusted Tool Host processes now execute in a kernel-enforced isolation
   domain limited to the admitted Work workspace and a delivery-private scratch
   directory; and
2. engineering-quality scores now have frozen, executable 0–4 anchors.

The T5 verifier also runs the client and server suites in separate processes and
working directories. This removes the known Python top-level `tests` package
collision without changing the task, acceptance behavior, or either repository.

## Runtime isolation boundary

The trusted Tool Host daemon remains a separately networked, non-root service.
Every untrusted process delivery is launched in a fresh Linux Landlock domain:

- Landlock ABI 6 or newer is mandatory and startup fails closed otherwise;
- file reads and directory enumeration are allowed only for runtime system
  roots, the current Work workspace, and a delivery-private scratch directory;
- writes are allowed only in the current workspace and scratch directory, with
  Watt path grants still enforcing the narrower admitted write scope;
- TCP bind/connect is denied in the untrusted domain;
- signal scope prevents a process from signalling a process outside its domain;
- `no_new_privs` is set before the repository process is executed;
- the process remains subject to the Tool Host service's non-root identity,
  dropped capabilities, read-only root filesystem, resource limits, and isolated
  executor network.

Landlock does not hide every metadata-only `stat(2)` result. The qualification
gate therefore tests content reads and directory enumeration, which are the
operations that disclose another Work's private content. UDP restrictions before
Landlock ABI 10 are supplied by the Tool Host's isolated Docker network; hostile
egress is verified from the sandboxed process. The daemon never exposes a Docker
socket or container-control capability.

Historical isolation evidence is retained separately:

- `q39-q40-isolation-v1-shared-host.json`: original cross-Work read failure;
- `q39-q40-isolation-v2-signal-gap.json`: first Landlock probe with an incorrect
  signal-scope bit, retained as a failed intermediate result;
- `q39-q40-isolation-v2-landlock.json`: corrected file, control-plane, metadata,
  cross-domain signal, and process-reaping probe.

## Revised benchmark contract

The revised benchmark preserves the original six meaningful tasks, three A/B
pairs per task, 18 pairs and 36 executions. It preserves the randomization seed,
task order produced by that seed, A/B injection assignments, acceptance text,
and the three replacement B executions T3-2-B, T4-1-B and T5-2-B.

Profiles remain frozen:

- primary: DeepSeek `deepseek-flash`, reasoning effort `high`;
- replacement: DeepSeek `deepseek-v4-pro`, reasoning effort `high`.

All real Provider requests are sequential. A request with an unknown response is
never replayed automatically. The combined Provider hard cap for the original
and revised runs is RMB 100. The revised ledger begins with the original
conservative RMB 3.69511347 charge and must reserve the worst permitted next
request before sending it. No profile, effort, task, injection, or acceptance
criterion may be changed to fit the budget.

## Frozen engineering-quality anchors

Every dimension is scored by the deterministic evaluator outside the model
execution. A mandatory verification failure, an unauthorized path change, a
missing required output, intent drift, an unsafe effect, or a required injection
that was not observed fails the execution regardless of score.

The common scale is:

| Score | Anchor |
|---|---|
| 4 | All mandatory evidence passes and no material issue remains. |
| 3 | Mandatory evidence passes with only minor, non-material debt. |
| 2 | Useful output exists, but material repair or evidence is still required. |
| 1 | Output is limited, fragile, or substantially incomplete. |
| 0 | Output is absent, wrong, outside scope, or unsafe. |

Dimension-specific anchors are frozen in
`benchmarks/native_executor_continuity_v2/spec.json` and implemented by
`evaluator.py`:

- **correctness** combines truthful `RESULT_READY` with every frozen independent
  verification result;
- **maintainability** checks parsable source and explicit unfinished-code debt;
- **scope discipline** compares every Git change and required output with each
  repository's exact write scope;
- **tests** combines independent checks with a task-specific minimum focused-test
  count frozen before revised outputs exist;
- **operability** requires a completed result, passing executable checks, bounded
  source artifacts, and the task's forbidden-network constraint.

Any dimension below 3 is a material defect. For each pair, B's five-dimension
mean may be no more than 0.25 below A. Acceptance, safety, intent retention, and
recovery gates cannot be compensated by a higher score elsewhere.

## Exit rule

The revised benchmark can close continuity qualification only if all 18 B
executions pass the frozen mandatory gates, all hard invariants hold in all 36
executions, model-replacement evidence remains valid, every recoverable injection
continues from retained obligations without technical Human repair, and the
quality equivalence rule passes. A revised failure remains a failure and is not
replaced by another benchmark version without a new explicit amendment.
