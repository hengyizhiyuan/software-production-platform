# Control Room Slice 4 Human Acceptance Preparation

## 1. Status

~~~text
Preparation observation date
    2026-09-07

Control Room Slice 4 Contract
    DEFINED

Human Product Acceptance
    NOT STARTED

Acceptance environment
    NOT READY

Preparation blocker
    ACTIVE RUNTIME DOES NOT CONTAIN THE CLOSED SLICE 3 PROJECTION
~~~

This record prepares the Human-operated acceptance activity defined by the
[Control Room Slice 4 Contract](../architecture/software-production-control-room-slice-4-implementation-contract.md).
It records environment Reality and a checklist. It is not Human acceptance
evidence and does not decide the acceptance outcome.

## 2. Repository Reality

Observed host repository:

~~~text
Branch
    feature/spg-first-vertical-slice

Host HEAD
    ec26d17a8474878b7f0a4adaf76e14e1ea066951

Working tree
    DIRTY - admitted Slice 3 implementation and documentation remain
    uncommitted
~~~

The host working tree contains the Slice 3 Human-facing markers:

- Production Objective;
- Attention Center;
- Understanding Alignment;
- Current Direction;
- Trust Summary.

No repository mutation was performed during preparation.

## 3. Runtime availability and baseline Reality

Observed local Runtime:

~~~text
Compose project
    watt-local-runtime

Application
    healthy

PostgreSQL
    healthy

UI
    http://127.0.0.1:8000/app

GET /health
    200

GET /app
    200
~~~

Observed production and activation Reality:

~~~text
Current Trusted Baseline revision
    ad6c446674ea4402a2164ddb0132b1394a3b9366

Current Trusted Baseline tree
    f4ac6d1906fe785a209bf4538089d7a160ea1713

Baseline Pointer version
    1

Runtime Commit
    82db580e-d0b4-53a0-8973-12a233c8bcfb

Active application revision
    b7b6ea33cfdcd89fb0f7e717d1a99f5c7891e14c

Runtime activation state
    ACTIVATION_REQUIRED
~~~

The running HTTP assets contain the existing Shared Understanding surface but
do not contain the Slice 3 Current Direction or Trust Summary surfaces. The
running application therefore cannot represent the complete closed Slice 1-3
Control Room capability set.

The application is available, but availability is not acceptance readiness.
No restart, rebuild, activation, database write, Work transition, or Runtime
mutation was performed.

## 4. Representative existing journey

The current Runtime contains one existing governed production story suitable
as a candidate for later Human review after the environment is made
representative:

~~~text
Interaction
    00561e9a-d82f-4ddb-8c98-ffe29524d190

Work
    9a2cc451-c603-520d-ba7f-9c963a3061a8

Work status
    COMPLETED

Trusted result
    true

Current Steering step
    COMPLETE

Human attention required now
    false
~~~

Motive:

> Reduce the Human's anxiety during AI-assisted development by making it easy
> to tell whether the AI is still working normally.

Governed desired outcome:

> During development, the Human can readily determine whether the AI remains
> active and operating normally, without requiring a complex monitoring
> system.

The existing story includes:

- Human expression and governed Work Reality;
- a long-lived Steering Plan;
- completed Design, Produce, Verify/Accept, and Complete steps;
- a Human-authorized Candidate and converged repository integration;
- Completion and eight passing Verification obligations;
- a Runtime Commit and advanced Trusted Baseline;
- an explicit Active Runtime divergence.

This makes it useful for reviewing Objective, Understanding, Status,
Direction, and Trust without creating new production facts. The current
Active Runtime divergence is also a truthful condition the future Trust
Summary must present rather than hide.

## 5. Environment readiness checklist

These preconditions must be confirmed before the Human begins Slice 4
acceptance:

- [ ] A clean, reviewed repository checkpoint contains the closed Slice 1-3
  implementation and required contracts.
- [ ] The application is built from the exact accepted checkpoint.
- [ ] The Current Trusted Baseline, active application revision, and intended
  acceptance source are coherent.
- [ ] The active Runtime checkout is clean or its exact governed state is
  explicitly explained.
- [ ] `GET /health` returns 200.
- [ ] `GET /app` returns 200.
- [ ] The running UI contains Production Objective and Attention Center.
- [ ] The running UI contains Understanding Alignment and Shared
  Understanding.
- [ ] The running UI contains Current Direction and Trust Summary.
- [ ] No new Work, Provider call, or production fact is required merely to
  begin acceptance.

At this preparation checkpoint, the repository-checkpoint, activation
coherence, clean-checkout, Current Direction, and Trust Summary preconditions
are not satisfied.

## 6. Human acceptance checklist

The following items are for the Human Governor to execute after all
environment preconditions pass. They remain unchecked in this preparation
record.

### A. Objective

- [ ] I can identify the active Motive.
- [ ] I can identify the governed Work and Desired Outcome.
- [ ] I can tell whether the Work is currently satisfied.
- [ ] I can answer: "What are we producing?"

Observation:

~~~text
NOT YET PERFORMED BY HUMAN
~~~

### B. Understanding

- [ ] I can see what the Human originally said.
- [ ] I can see what Watt interpreted.
- [ ] I can see what became governed Reality.
- [ ] I can distinguish all three without treating interpretation as
  authority.
- [ ] I can answer: "Does Watt understand what I mean?"

Observation:

~~~text
NOT YET PERFORMED BY HUMAN
~~~

### C. Status and Attention

- [ ] I can identify the current Work state and production activity.
- [ ] I can see whether the system is active, waiting, blocked, or complete.
- [ ] I can see whether Human Attention is required.
- [ ] I can understand an existing decision or transition without creating a
  new one for the test.
- [ ] I can answer: "What is happening now?"

Observation:

~~~text
NOT YET PERFORMED BY HUMAN
~~~

### D. Direction

- [ ] I can identify the active Plan revision and current step.
- [ ] I can identify the next step, or understand why no next step remains.
- [ ] I can see the admitted rationale and Reality basis.
- [ ] I can distinguish a Plan Steering decision from a Control Room
  presentation.
- [ ] I can answer: "Why is the next step this?"

Observation:

~~~text
NOT YET PERFORMED BY HUMAN
~~~

### E. Trust

- [ ] I can identify Completion Reality.
- [ ] I can identify the Verification result and supporting obligations.
- [ ] I can identify the Runtime Commit and Current Trusted Baseline.
- [ ] I can distinguish a trusted repository result from the Active Runtime.
- [ ] I can see the current `ACTIVATION_REQUIRED` condition without it being
  presented as active trust.
- [ ] I can answer: "Why should this result be trusted?"

Observation:

~~~text
NOT YET PERFORMED BY HUMAN
~~~

### F. Coherence and progressive disclosure

- [ ] The default view is understandable without internal implementation
  knowledge.
- [ ] The default view is not overloaded.
- [ ] Relevant details are available when needed.
- [ ] No two projections contradict each other.
- [ ] No projection appears to own a truth that belongs to WIC, Plan Steering,
  SPG, Verification, Runtime, or Human Governance.

Observation:

~~~text
NOT YET PERFORMED BY HUMAN
~~~

## 7. Finding capture

Human observations must be recorded without repair during acceptance.

Use:

- **Product Experience Gap** for confusing information, missing explanation,
  poor visibility, or ineffective presentation;
- **Architecture Gap** only for missing Reality ownership or a missing or
  violated capability boundary.

For each finding record:

~~~text
Observed condition
Expected Human understanding
Relevant projected Reality
Classification
Critical / non-critical
Recommended product priority
~~~

The current stale Active Runtime is an acceptance-environment preparation
blocker, not a Human Product Acceptance result and not by itself an
Architecture Gap.

## 8. Preparation conclusion

~~~text
Environment checks
    PASS

Application availability
    PASS

Representative existing journey
    AVAILABLE

Complete Slice 1-3 UI in active Runtime
    FAIL

Human Product Acceptance
    NOT STARTED

Preparation result
    BLOCKED UNTIL A REVIEWED CHECKPOINT IS ACTIVE
~~~

The narrow next preparation step is to establish a reviewed clean checkpoint
containing the admitted Slice 1-3 Reality, then use the existing governed
Runtime activation/bootstrap mechanism to make that exact checkpoint active.
That action requires separate authority and is not performed by this record.
