# Watt Current Milestone Closure — 2026-09-20

```text
MILESTONE_CLOSURE = PASS
HUMAN_ACCEPTANCE = PASS
FULL_REGRESSION = PASS (PRE-FINAL-NARROW-FIXES)
POST_FULL_REGRESSION_QUALIFICATION = FOCUSED PASS
```

This is the canonical closure evidence for the Watt milestone spanning durable
PRE_WORK through governed production, Preview, Delivery, and Human Acceptance.
It preserves the difference between accepted milestone capability and future
UX/productization work. It does not claim that Watt is complete or authorize the
next architecture phase.

## Repository and Runtime basis

- Branch: `feature/spg-first-vertical-slice`
- Full Regression / pre-final-fix implementation baseline:
  `ecc7a11b6375d1fd5777239ac395c365574f8647`
- Final narrow product-fix commit:
  `3875bbd` (`fix(ui): close delivery completion states`)
- Closure lineage: `ecc7a11` -> `3875bbd` -> the closure evidence commit that
  contains this document. The final exact HEAD is reported by Git after commit
  and push in the closure task report; a commit cannot contain its own SHA.
- Migration head/current at qualification: `20260919_44`
- Human Review compose project: `watt-pre-work-human-review`
- Runtime profile: `watt-wic-slice3-dogfood`
- WIC / Conversation: DeepSeek `deepseek-flash`, controlled WIC
- Native Executor: Watt-native, DeepSeek `deepseek-flash/high`
- Final local Human Review Runtime: intentionally stopped after Human review;
  PostgreSQL and Runtime volumes preserved.

## Full Regression evidence

The successful Full Regression completed before the final narrow UI and Delivery
fixes:

| Surface | Result |
|---|---|
| Python | 1,264 total; 1,254 passed; 10 skipped; 0 failed |
| Web/UI | 65 passed; 0 failed |
| Native/Linux | PASS |
| `uv lock --check` | PASS |
| Compile/import | PASS |
| Alembic | head/current `20260919_44` |
| Runtime health | PASS |

The ten Python skips were the intentionally environment/authorization-gated
real-Provider probes. Their relevant real-provider boundaries were qualified in
separate bounded evidence, including WIC, governed streaming, DeepSeek transport,
and Watt-native Executor probes. No skipped case concealed a deterministic test
failure.

The Full Regression is historical evidence for baseline `ecc7a11`. It is not
claimed to cover the post-regression changes below, and it was intentionally not
rerun.

## Post-Full-Regression narrow changes

### Deliver completion projection

`src/spg/web/control-room.js` now projects the terminal `COMPLETE` step as done
when the authoritative Steering projection reports `last_stop_reason=COMPLETE`.
This reconciles the Agenda with a Work whose status is `COMPLETED` and whose
`work_complete` projection is true. Human Delivery acceptance remains a separate
decision and is not redefined as Work completion.

### Delivery Runtime, acceptance, and recovery messaging

`compose.wic-slice3.yaml` now enables the exact-manifest static software Runtime
and publishes its bounded local port range for the Human Review profile.
`src/spg/web/delivery.js` exposes acceptance only after the exact Runtime reports
`READY`, explains the required sequence while it is not ready, and clears a
stale top-page error after a successful non-mutating refresh. The existing
server-side invariant still rejects software acceptance without an accessible
exact-manifest Runtime.

### Asset-version cache repair

`src/spg/web/index.html` uses a new `control-room.js` asset version. An ordinary
refresh therefore loads the completed-Deliver projection instead of retaining
the previously cached script.

## Incremental qualification

Risk-based focused evidence after the Full Regression:

- Control Room Node suite: 18 passed, 0 failed.
- MVP UI/configuration contracts: 13 passed, 0 failed.
- Exact software delivery Runtime restore and explicit acceptance integration:
  1 passed against disposable PostgreSQL `spg_test`.
- JavaScript syntax checks: PASS.
- Compose merged configuration validation: PASS.
- `git diff --check`: PASS.
- Live Work evidence before Runtime shutdown:
  `status=COMPLETED`, `work_complete=true`, Steering current step `COMPLETE`,
  `last_stop_reason=COMPLETE`, progression `STOPPED`.
- Live exact software Runtime: `READY` at the published local origin; manifest
  identity and `index.html` SHA-256 matched the delivery record.
- Live Delivery page after recovery: stale notice empty, exact Runtime link
  visible, and acceptance action available only in the ready state.
- Human re-verification: the final Deliver marker rendered as a check and the
  Human explicitly confirmed the result before requesting Runtime shutdown.

The changed boundaries are frontend projection, Human Review configuration,
Delivery action availability, and cache identity. The focused state, contract,
single integration, live Runtime, and Human evidence directly cover those risks.
This is the adopted `Risk -> Required Evidence` policy, not a claim that the
earlier Full Regression included later code.

## Human Acceptance

```text
HUMAN_ACCEPTANCE = PASS
```

The accepted milestone capability includes:

- PRE_WORK interaction, persistence, multiple PRE_WORK records, and discard;
- Work Admission identity and visible continuity;
- normal production progression and truthful queue/scheduler state;
- Engineering Semantic Truth, including `8×5` interpretation and explicit
  correction/supersession;
- Human correction through re-Steering and re-Production;
- Watt-native execution, worker liveness/recovery, and DeepSeek long-running SSE;
- governed Human-facing streaming;
- Preview, exact artifact/runtime Delivery, and acceptance behavior; and
- final completed Deliver projection.

This Human milestone decision is distinct from an individual immutable
per-manifest Delivery Acceptance row. Earlier failed acceptance attempts returned
409 and created no false acceptance record. The closure records the Human's
explicit milestone acceptance without fabricating Runtime history.

Human Acceptance does not mean that the Human found zero product-improvement
opportunities. The capability is accepted; formal Delivery information hierarchy,
broader product navigation, richer response forms, and further domain grounding
remain future work.

## Resolved major Dogfood cases

- PRE_WORK refresh durability and multiple PRE_WORK/discard behavior;
- Work Admission continuity;
- queue capacity truth and autonomous scheduler progression;
- worker liveness and retained recovery;
- DeepSeek approximately 60-second non-stream transport failure, repaired with
  complete terminal SSE handling;
- governed Human-facing streaming regression;
- `8×5` semantic drift and correction supersession;
- Preview CSP external-image failure at the effective browser/HTTP boundary;
- completed Work leaving Deliver visually incomplete; and
- Delivery acceptance exposed without Runtime readiness and retaining a stale
  recovery error.

## Open non-blocking findings

- [Delivery Human Experience / Productization](../product/delivery-human-experience-productization.md):
  capability accepted; formal product experience remains open.
- [Course-table Domain Grounding](../architecture/case-studies/course-table-domain-grounding-and-semantic-boundary.md):
  domain convention mismatch is future grounding input, not a Semantic Truth
  failure.
- [WIC Software Production SOP × LLM](../architecture/wic-software-production-sop-and-llm-direction.md):
  redesign remains `NOT_STARTED` and requires separate authorization.
- [Waterfall CSP Loop and Guardian Recovery](../architecture/case-studies/waterfall-demo-csp-loop-and-guardian-recovery.md):
  repeated-failure and Human-perspective assurance evidence remains preserved for
  future Guardian design.
- Preview / external assets: passive HTTPS image/CSP behavior is fixed and
  regression-protected; broader isolated Preview forms and additional external
  resource capabilities remain future work where demanded by product scope.

None is a blocker for this milestone.

## Closure decision

The pre-fix Full Regression passed, the final narrow changes have direct focused
qualification and Human re-verification, Human Acceptance is PASS, and no
blocking finding remains. Publishing the closure commit to the existing upstream
completes the repository-side closure gate.

```text
MILESTONE_CLOSURE = PASS
NEXT_PHASE = WIC SOFTWARE PRODUCTION SOP × LLM / SOFTWARE DOMAIN GROUNDING
NEXT_PHASE_IMPLEMENTATION_AUTHORIZED = NO
```
