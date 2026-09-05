# Long-lived Motive Dogfood #2 Post-admission Activation Finding

## Preserved Result

```text
Long-lived Motive Dogfood #2
    PASSED WORK ADMISSION
    FAILED AT POST-ADMISSION STEERING ACTIVATION

STEERING_BOOTSTRAP_TRIGGER_GAP
    CONFIRMED
```

The preserved pre-fix Work `86bf8147-0d51-45f5-b74f-07d764343a20` reached
`LONG_LIVED_STEERING / READY` through Work Draft Attention approval and retained
an admitted Engineering Scope. It then remained at
`STEERING_BOOTSTRAP_PENDING` with zero Steering Plans, Run, PWU, Attempt,
Dispatch, Provider Report, or Provider Turn.

The product UI used `POST /api/attention/{attention_id}/resolve`. That entry
point persisted admission but did not invoke Steering bootstrap; the HTTP layer
then applied the immediate-production ORCH scheduling rule to every READY Work.
ORCH truthfully made no production progress because the long-lived Work had no
Runtime binding. Restart recovery also required an existing Steering Plan, so
it could not repair this pre-bootstrap interruption window.

Contributing findings:

- `POST_ADMISSION_AUTO_CONTINUE_GAP`
- `STEERING_DRIVER_SCHEDULING_GAP`
- `RESTART_BOOTSTRAP_ELIGIBILITY_GAP`

## Development Resolution

MVP-PLAN-STEER-1H introduces one mode-aware post-admission service used by both
Work approval entry points. For long-lived Work it idempotently creates one
Steering Plan, active Revision, and CURRENT Step, then schedules the bounded
Plan Steering Driver. For immediate-production Work it preserves existing ORCH
scheduling. Startup repairs `READY + LONG_LIVED_STEERING + no SteeringPlan`
before applying normal driver restart eligibility. Failure never falls through
to ORCH, and activation alone does not pre-create Run/PWU.

```text
MVP-PLAN-STEER-1H
    CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

Reality-driven Plan Steering
    IMPLEMENTED FOR MVP BEHAVIOR
    REAL DOGFOOD CONTINUES
```

This development correction does not reinterpret Dogfood #2 as successful and
does not mutate its Runtime. A fresh Runtime and the same Motive are required
for post-review reproduction.
