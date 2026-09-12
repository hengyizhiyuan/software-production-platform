# Watt-native Executor — Human Acceptance Preparation

Status: **HISTORICAL PREPARATION SNAPSHOT / SUPERSEDED BY TECHNICAL CLOSURE**.

The technical qualification prerequisites described below are now complete.
The Human Governor has deferred Human Product Acceptance to the later
system-wide Human Journey and UX/UI reconstruction phase. This retained script
does not represent an acceptance decision and does not keep the Watt-native
Executor technical phase open. See the
[final technical closure](../evidence/watt-native-executor-technical-closure.md).

The architecture requires a Human to start a governed PWU, observe queue and
allocation, interrupt and resume execution, inspect retained checkpoints and
artifacts, preview the exact Candidate, authorize it, and observe delivery. No
automated test may substitute for that decision.

## Historical technical environment at preparation time

- Compose project: `watt-native-executor-runtime-qualification`
- UI: `http://127.0.0.1:8040/app`
- Database migration: `20260911_34`
- Running technical services: PostgreSQL, Watt application, native coordinator,
  native Tool Host
- Provider Worker: not started
- Seeded acceptance Work/PWU: none
- Real Provider Threads/Turns created by this mission: 0/0

This environment is deliberately not labelled an acceptance runtime. Its image
contains the uncommitted implementation while its Git Source of Truth remains
the prior clean HEAD, so it cannot serve as an exact reviewed acceptance
baseline.

## Historical prerequisites before Human acceptance

1. Close the open mandatory qualification gaps documented in
   [implementation progress](../evidence/watt-native-executor-runtime-implementation-progress.md).
2. Run the full current-tree deterministic regression and required fault/race
   suites on an exact clean checkpoint.
3. Create and review a clean repository checkpoint; observe its exact commit,
   tree, image, migration, policy, and environment profiles.
4. Provision a fresh isolated acceptance Runtime and bootstrap its own Trusted
   Baseline through the normal governed path.
5. Configure one explicitly authorized inference Provider and verify zero-turn
   readiness without exposing credentials.
6. Seed a representative Work/PWU through existing Work, Steering, and SPG
   authority; do not insert native queue rows manually.

## Human checklist once ready

- Start one PWU and identify its exact Work, Plan/PWU contract, source vector,
  capability grants, and resource envelope.
- Observe entered queue, resource wait, allocation, execution, and checkpoint.
- Request Pause during real useful work; verify no new effect admission after
  the barrier and inspect the quiescent checkpoint.
- Resume from the exact checkpoint without resending the whole mission.
- Simulate one admitted worker interruption; verify fenced ownership,
  independently observed effects, salvage, and unfinished-work continuation.
- Inspect exact artifacts and evidence; confirm Executor says `RESULT_READY`,
  not `TRUSTED`.
- Observe independent Completion and Verification.
- Preview the exact Candidate, authorize it as Human, and observe governed
  integration, Runtime Commit, Trusted Baseline, activation where applicable,
  and delivery.
- Record Human acceptance or exact findings against the reviewed commit/tree.

No acceptance outcome is recorded by this document.
