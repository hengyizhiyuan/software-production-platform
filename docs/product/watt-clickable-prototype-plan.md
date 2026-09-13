# Watt Clickable Prototype Scope, Acceptance, and Implementation Plan

## 1. Status and objective

```text
Prototype definition
    HIGH-FIDELITY EXPERIENCE SIMULATION

Planning status
    READY FOR HUMAN REVIEW

Prototype implementation
    NOT STARTED / NOT AUTHORIZED BY THIS DOCUMENT

Production implementation
    NOT STARTED / NOT AUTHORIZED BY THIS DOCUMENT
```

The later prototype exists to answer what Watt should feel like to a real user
across the whole first-release journey. It is an experience calibration tool,
not a production client, backend emulator, domain model, technical qualification
environment, or second source of truth.

It implements the target journey described in
[Watt First-release Human Journey and Information Architecture](watt-first-release-human-journey.md),
uses the coverage in the
[Scenario Inventory](watt-first-release-scenario-inventory.md), and keeps every
known mismatch visible through the
[Architecture Tension Register](watt-human-journey-architecture-tensions.md).

## 2. Prototype boundary

### 2.1 Technical approach

Place the prototype under:

```text
prototype/human-journey/
```

Use a small Vite + React + TypeScript application with an isolated package and
lock file. React is justified here because the review needs a persistent shell,
many stateful paths, resettable fixtures, conditional contextual panels, and
rapid scene-level iteration. The current production frontend is plain static
HTML/JavaScript, so importing its Runtime-coupled modules would save little and
would blur the isolation boundary. Visual tokens may be copied intentionally
when useful, but production modules, API clients, and stores are not imported.

The prototype contains:

- a responsive application shell for Home, Work, Queue, and Deliveries;
- deterministic scenario fixtures in typed local files;
- a pure in-memory scenario reducer;
- clickable actions that advance only to declared fixture states;
- a reviewer drawer for pack selection, scene selection, reset, and notes;
- realistic text, previews, assets, evidence summaries, and timelines;
- a permanent `Watt Experience Prototype — simulated data` marker;
- an optional URL fragment containing pack and scene, so a review state can be
  shared without persistence.

The default build has no production base URL and no general network client. A
development guard should fail loudly if code attempts `fetch`, WebSocket,
EventSource, or form submission outside same-document static resources. All
transitions operate on bundled mock data. Starting, pausing, authorizing,
delivering, or resetting a scene must never call production APIs, modify a
database, spend Provider credits, or trigger Executor work.

The prototype is locally runnable with one documented command and deletable as
one directory after formal implementation. It should not require Docker,
PostgreSQL, credentials, or the Watt Runtime.

### 2.2 In scope

The prototype simulates:

- first-use and returning-user Home;
- conversation from vague Motive through correction and readiness;
- a complete Work Formation Review and explicit admission choice;
- Work context across design, planning, queue, execution, recovery,
  verification, result review, delivery, completion, and re-entry;
- zero-, one-, and multi-asset Work, including repository capability states;
- global Queue across multiple Works;
- Needs-me projections with deep links into Work context;
- meaningful stages rather than fake completion percentages;
- pending conversation messages and browser reconnect state;
- pre-authorization software/result preview, changes, checks, limitations, and
  exact Human authorization language;
- delivery history and a later refinement cycle;
- autonomous, awareness-only, and action-required recovery experiences;
- desktop and narrow-width interaction layouts;
- engineering-detail progressive disclosure without requiring it.

### 2.3 Out of scope

The prototype does not simulate a real model, dynamic natural-language quality,
production latency, token streaming performance, real repositories, Git
operations, provider billing, actual queue scheduling, real previews, build or
test execution, Runtime Commit effects, delivery packaging, authentication,
multi-user collaboration, enterprise IAM, Guardian, ECF, distributed
scheduling, final brand identity, or final visual tokens.

Conversation branches use authored deterministic responses. Reviewers judge
content structure, continuity, tone direction, and action placement; they do not
judge real WIC intelligence or Provider performance from the prototype.

## 3. Simulation architecture

### 3.1 Scenario, scene, and projection

Each pack contains immutable starting fixtures and an ordered graph of scenes.
A scene declares:

```text
scene identity
Human-visible condition
facts projected by each real owner
screen emphasis
available Human actions
automatic transition choices
expected next scenes
acceptance focus
related scenario IDs and architecture tensions
```

The reducer stores only the selected pack, current scene, locally typed draft,
opened disclosures, and reviewer notes. A transition replaces the current mock
fact bundle with the declared next bundle. It never derives production truth or
implements recovery policy.

Automatic movement is still deterministic: the reviewer clicks “advance
simulation” or enables an optional short scripted timer. Timers affect
presentation only and can be paused. Reset returns the pack to its exact seed.

### 3.2 Simulation-state mapping

The following labels are reviewer conveniences, not domain lifecycle states.
Every screen should be driven by the mock source facts in the third column;
components must not branch on the convenience label alone.

| Prototype concept | Human meaning | Existing Reality represented by the fixture | Must not imply |
|---|---|---|---|
| `PRE_WORK` | A Motive or question exists; no Work exists | Interaction/WIC records; no admitted Work | Draft Work or production authority |
| `REFINING` | Human and Watt are clarifying meaning | Interpretation revisions, shared understanding, unresolved questions | Conversation text is governed truth |
| `READY_FOR_WORK` | An exact formation proposal can be reviewed | WIC readiness plus proposed formation projection | Readiness is admission authority |
| `DESIGNING` | Admitted Work is resolving product/design issues | Work revision; Guided Design agenda/issues/readiness | A new design owner or lifecycle |
| `PLANNING` | Watt is determining meaningful next outcomes | Steering plan/revision/current step and Reality basis | Executor chooses WHAT NEXT |
| `QUEUED` | A runnable stage is waiting its turn | PWU contract plus queue `QUEUED` | A new task identity |
| `WAITING_FOR_CAPACITY` | Compatible capacity is unavailable | Queue/Execution mode `WAITING_RESOURCE`, resource/capacity facts | Failure or an exact ETA |
| `RUNNING` | Watt is actively producing | Queue `ALLOCATED/EXECUTING`; Attempt/Step facts | Raw Execution Slice as a product object |
| `CHECKPOINTED` | Useful work is durably saved | Committed checkpoint; queue `CHECKPOINTED` or returned-to-queue frontier | Result is complete or verified |
| `PAUSED` | Governed work is safely paused | control request plus Execution mode `PAUSE_REQUESTED/PAUSING/PAUSED` | Immediate process death or settled effects before observation |
| `RECOVERING` | Watt is restoring a coherent safe frontier | Execution mode `RECONCILING`, Recovery Case/Barrier, observations | Automatic replay of unknown effects |
| `WAITING_FOR_HUMAN` | A specific Human decision blocks the path | Queue `WAITING_HUMAN`; Attention; authority requirement | An error inbox disconnected from Work |
| `VERIFYING` | Independent checks are evaluating exact output | result-ready claim, Completion/Verification in progress | Executor's self-report is trust |
| `RESULT_READY` | A result exists and is being prepared for review | immutable output/result claim; observed artifact/evidence | Trusted, authorized, delivered, or accepted |
| `READY_FOR_AUTHORIZATION` | Exact preview and required assurance are reviewable | Candidate/aggregate manifest, verification/admissibility, preview | Human has already approved |
| `AUTHORIZED` | Human authorized one exact result and target set | exact Candidate authorization | Authorization covers a revised result or changed target |
| `DELIVERED` | The promised usable form is available | integration effects, Runtime Commit, Trusted Baseline, Delivery manifest/runtime status | Active Runtime necessarily matches or Human accepted |
| `COMPLETED` | Human says the Work is currently satisfactory | Human acceptance plus Work satisfaction projection | Conversation or Work history is closed forever |
| `REOPENED` | The same Work has entered a new refinement cycle | new Interaction/Work revision and reopened satisfaction/design/steering facts | Unrelated Motive silently changes old Work |

## 4. Prototype scenario packs

Each pack has a reset action and a short “why review this” note. It references
inventory IDs rather than duplicating their acceptance contract.

| Pack | Replayable story and key scenes | Inventory coverage | Primary tensions |
|---|---|---|---|
| P01 — Vague Motive | New Home → provisional understanding → useful recommendation → context addition → postpone or Formation Review | J01, J03, J04, J07, J09, J11, J12, J16 | T01, T03, T04 |
| P02 — Clear idea, no repository | Clear software outcome → Formation Review → admit → design → managed workspace explanation → plan | J12, J16, J17, J22, J28, J34, J35, J38 | T03, T05, T12 |
| P03 — Existing repository | Attach reference → capability observed → Work-scoped authorization → design/change plan → code-result preview | J23, J25, J27, J31, J38, J66 | T09, T11, T12 |
| P04 — Multi-repository Work | Bind two repositories and a document → cross-target plan → aggregate preview → one target converges late | J24, J35, J67, J71, J72 | T08, T10, T20 |
| P05 — Capacity queue | Two Works ready → one running → second waits without fake ETA → allocation → stage transition | J40–J43, J57–J59 | T05, T06, T21 |
| P06 — Interrupted and recovered | Running → checkpoint → worker interruption → recovering awareness → requeue → resume from frontier | J44–J47, J51, J84 | T17, T18 |
| P07 — Human correction during active Work | User corrects business intent → Watt identifies material impact → current activity is bounded → revised Work decision | J05, J30, J37, J49 | T07, T16, T18 |
| P08 — Material scope governance | New requested capability expands destination → clear impact → pause/continue/new Work choices → exact decision | J14, J30, J37, J39, J53–J55 | T07, T16, T19 |
| P09 — Verification self-correction | Result ready → independent check fails → Watt explains no action needed → governed correction → new result passes | J61–J64 | T14, T18, T22 |
| P10 — Preview and authorization | Verified application → interactive mock preview → changes/checks/limitations → request changes or exact authorize | J62, J65, J66, J68–J71 | T08, T09, T14 |
| P11 — Completed Work refined later | Delivery → Human acceptance → leave → returning Home summary → old delivery → refine same Work | J73, J74, J79–J81, J88 | T02, T13, T15 |
| P12 — Attention required | Home Needs-me item → exact Work context → asset credential or unsafe ambiguity → resolve/postpone | J25, J32, J49, J64, J86 | T07, T18, T22 |
| P13 — Conversation branch safety | Direct question → multiple interpretations → correction → unrelated aside → distinct new Motive → return | J02, J05, J10, J13–J15 | T01, T16 |
| P14 — Browser continuity | Assistant replying → second message queued → navigate away/reconnect → messages remain ordered; production unaffected | J60, J76, J83, J87 | T17, T19 |
| P15 — Asset loss and stale Reality | Bound repository changes externally → stale review rejected → access lost → reauthorize or managed alternative | J27, J50, J86, J87 | T11, T18, T19 |
| P16 — Delivery and trust mismatch | Checks pass → authorize → delivery exists → active Runtime differs → explain status → later convergence | J62, J68, J71, J73, J74, J80 | T13, T14, T20 |

All twelve mission-required paths are present in P01–P12. P13–P16 expose
global contradictions that isolated happy-path reviews could miss.

## 5. Prototype screen and component scope

The prototype should implement experience systems, not a catalogue of pages:

1. **Shell and orientation:** top-level navigation, global new-Motive entry,
   current Work identity, prototype marker, and reviewer drawer.
2. **Home:** first-use conversation start; returning Needs-me, changes, active
   Work, queue summary, and recent deliveries.
3. **Work context:** adaptive header; Conversation; Shared Understanding;
   Formation Review; design decision; direction and meaningful stages; current
   production; trust/result; delivery and re-entry.
4. **Queue:** cross-Work order, capacity/wait reason, current activity, and
   governed contextual controls.
5. **Result review:** form-aware mock preview, change summary, checks, evidence,
   limitations, targets, request-changes, reject, and exact authorize.
6. **Deliveries:** usable actions, trust and Runtime status, history, and links
   back to Work/refinement.
7. **Attention projection:** Home summary, local Work card, deep link, decision
   comparison, stale-basis handling, and resolved history.
8. **Progressive detail:** evidence and engineering lineage that can be opened
   without contaminating ordinary language.

## 6. Human prototype acceptance

### 6.1 Review method

The Human Governor reviews one pack at a time. A session begins from reset,
follows every declared branch, and records observations against specific scenes.
Review concerns experience only:

- mental-model clarity and terminology;
- navigation and orientation;
- interaction continuity and conversation placement;
- information hierarchy and unnecessary clicks;
- perceived control and exact authority;
- perceived trust and distinction among result/check/authorization/delivery;
- progress and waiting clarity without fake precision;
- exception and recovery experience;
- ability to tell what changed and what happens next;
- engineering leakage;
- desktop and narrow-width usability.

Prototype acceptance does not test Provider speed, WIC intelligence, API
correctness, database durability, Executor recovery, verification integrity,
security isolation, or production performance.

### 6.2 Scene acceptance ledger

Keep a simple versioned Markdown ledger alongside the future prototype:

```text
prototype/human-journey/acceptance/scenes.md
```

Each row contains pack, scene ID, prototype revision, status, Human observation,
required calibration, decision date, and superseded scene/revision if any. The
only statuses are:

- `DRAFT`
- `UNDER_HUMAN_REVIEW`
- `CALIBRATION_REQUIRED`
- `HUMAN_EXPERIENCE_ACCEPTED`

Approval applies to one scene at one exact prototype revision. A later visual
change does not require reapproval unless it changes the accepted interaction,
information, terminology, authority, or trust contract. A materially changed
scene receives a new revision and retains the earlier decision as history.

### 6.3 Pack exit criteria

A pack is ready to be accepted when the Human can, without an architecture
briefing:

1. state the current intended outcome;
2. distinguish conversation from governed Work;
3. identify what Watt is doing or why it is waiting;
4. identify whether any Human action is required;
5. explain what the proposed action will authorize;
6. distinguish generated, checked, authorized, delivered, and accepted;
7. recover orientation after taking each branch;
8. reach the next sensible action without reading engineering detail.

The overall prototype may be designated
`APPROVED_HUMAN_EXPERIENCE_BASELINE` only after all P0 scenes and the P1 scenes
needed for exception/recovery continuity are `HUMAN_EXPERIENCE_ACCEPTED`, the
four top-level areas work as one mental model, and every accepted architecture
assumption has either existing support or an explicit tension-resolution plan.
This designation governs experience implementation; it is not architectural
truth or Human acceptance of the production product.

## 7. Prototype construction sequence

The later prototype mission should build in six reviewable increments:

1. **Orientation spine:** shell, first/returning Home, Work context frame,
   deterministic engine, reviewer reset, and P01/P13.
2. **Formation and design:** Shared Understanding, Work Formation Review,
   assets at admission, design recommendation/decision, and P02/P03.
3. **Plan, Queue, and progress:** meaningful stages, global Queue, wait/activity,
   pending conversation, and P05/P14.
4. **Attention and recovery:** deep-linked Needs-me, three recovery contracts,
   checkpoints, scope governance, stale basis, and P06/P07/P08/P12/P15.
5. **Result, trust, and authority:** preview, verification, limitations,
   multi-target result, exact authorization, and P04/P09/P10.
6. **Delivery and re-entry:** delivery history, Runtime/trust mismatch,
   satisfaction, returning summary, refinement, P11/P16, responsive polish, and
   complete scene ledger.

Each increment ends in Human scene review. Visual refinement can span packs,
but accepted information and authority contracts remain traceable by scene.

## 8. Formal implementation after prototype acceptance

Production work begins only after the relevant prototype scenes are accepted
and architecture tensions for that block are resolved. Implement meaningful
journey blocks rather than isolated components.

| Block | Human scenes | Required backend/projection capabilities | Likely architecture/data work | Tests and fidelity checks | Runtime Human Acceptance |
|---|---|---|---|---|---|
| I1. Home and orientation | First-use, returning summary, Work finding/switching, change summary | Aggregate current Work/attention/queue/delivery projection; visit/change basis | Resolve T01/T02/T23; possible last-seen record; no Project entity | projection truth tests, empty/returning states, deep links, accepted-scene visual/interaction comparison | Start a Motive; leave/return; locate two Works and one change |
| I2. Formation and contextual assets | Clarify/correct; Formation Review; zero/one/multi asset intake | Exact proposal read/command contract; existing WIC/Work admission; asset capability projection | Resolve T03/T11; define proposal identity and generalized-asset boundary before schema work | no-Work-on-first-turn, stale review, admit/refine/reject, repository-optional and permission tests; prototype fidelity | Human reviews and admits one no-repository and one repository Work |
| I3. Guided Design and direction | Recommendation, alternatives, material decisions, stage plan | Guided Design and Steering composition; Human-readable stage projection | Resolve T05/T16; preserve WHAT NEXT ownership | design decision/plan revision invariants, remembered constraints, scope-change boundaries; scene comparison | Human changes business and technical constraints and understands revised direction |
| I4. Queue, progress, and conversation continuity | Queued/capacity/running/checkpoint/requeue/pause/resume; pending message | Cross-Work queue projection; durable event cursor; governed controls; outbox/reconnect | Resolve T06/T17/T18/T21; no Execution Slice product entity | queue ordering/capacity, browser reconnect, slow-client backpressure, no duplicate turn/effect, control race tests; visual fidelity | Human observes real queue, closes/reopens browser, pauses/resumes safely |
| I5. Attention and recovery | Decision/access/ambiguity/unknown/stale/automatic recovery | Typed attention composition and exact deep links; recovery summaries; conflict delta payload | Resolve T07/T18/T19/T22 without new truth owner | each attention kind, autonomous/inform/action classification, stale decision, UNKNOWN no-replay, asset loss | Human handles one decision, watches one automatic recovery, and resolves one stale surface |
| I6. Result preview and authorization | Verification, self-correction, application/code/multi-target preview, reject/refine/authorize | Form-aware preview adapters; aggregate result/trust projection; exact authorization commands | Resolve T08–T10/T14/T20; preview record/data only after ADR | immutable revision, preview isolation, failed verification, limitation visibility, stale authorization, multi-target convergence | Human previews real result, requests a correction, then authorizes the exact revised result |
| I7. Delivery, satisfaction, and re-entry | Runtime/repository/download delivery, history, acceptance, later refinement | Delivery/Runtime/trust composition; delivery-to-Work deep link; existing acceptance/re-entry | Resolve T13/T15; preserve technical trust vs Human satisfaction | delivery manifest/runtime mismatch, history, request changes, re-entry identity; prototype fidelity | Human opens delivery, records satisfaction, returns later, and refines same Work |
| I8. Integrated journey acceptance | All accepted P0 and required P1 packs | All prior blocks in one isolated current-source Runtime | Close remaining accepted tensions; update SOT status without rewriting history | focused end-to-end contracts plus existing relevant regression suites; performance measured separately | Human runs Motive→Delivery→re-entry and management/recovery journeys; Human alone decides acceptance |

Each block must compare production behavior against exact accepted scene
revisions while also testing Runtime truth. If Reality invalidates a prototype
assumption, stop that block for architecture review, calibrate the prototype,
obtain renewed scene approval, and then continue. Do not force implementation to
copy an invalid mock.

## 9. Internal critique before commit

| Review question | Finding | Revision or guardrail |
|---|---|---|
| 1. Does the map cover Motive → Delivery? | Yes. The 18-stage journey runs from pre-Work expression through formation, design, queue, production, verification, preview, authority, commit, delivery, satisfaction, and re-entry. | P01/P02/P10/P11 collectively exercise the full chain. |
| 2. Does it cover returning-user management? | Yes. Home change summary, Work filtering/switching, delivery history, long-absence return, archive direction, and completed-Work refinement are inventoried. | P11/P14/P16 test orientation after leaving the product. |
| 3. Are queue/wait/recovery paths visible? | Yes. Capacity, provider/resource/Human waits, checkpoint, yield, requeue, resume, automatic recovery, UNKNOWN, restart, and partial convergence are separate scenarios. | P05/P06/P12/P15 expose them in global and Work context. |
| 4. Are Human Authority points explicit? | Yes. Work Admission, asset access/binding, material design/scope decisions, production proposal/control, exact result authorization, external integration, and product satisfaction are distinct. | Every relevant scene puts action beside the governed basis. |
| 5. Is the user forced to learn engineering internals? | No in the target. Nine Human concepts carry the default model; internals remain progressive detail. | Stage/result/trust translations are explicit; engineering identifiers are prohibited as primary labels. |
| 6. Are there duplicate interaction channels? | No. Conversation is the single expression plane; Attention is navigation; structured actions govern exact contextual objects. | No standalone approval inbox or second chat is proposed. |
| 7. Are exceptions product experiences rather than debug output? | Yes. Every fault maps to Watt-recovers, informed-no-action, or Human-action-required with consequence and next step. | Raw error/provider/lease codes stay in engineering detail. |
| 8. Is prototype scope broad enough to expose global contradictions? | Yes. Sixteen packs cross Home, Work, Queue, Attention, preview, Deliveries, assets, recovery, and re-entry. | Extra P13–P16 deliberately test cross-cutting contradictions. |
| 9. Is it small enough to iterate cheaply? | Yes with guardrails. One isolated client, deterministic fixtures, no backend, one reducer, four top-level areas, and no final brand system bound the work. | Build in six increments and keep non-experience runtime simulation out. |
| 10. Are architecture tensions surfaced? | Yes. Twenty-eight tensions identify current Reality, mismatch, safe simulation, and likely implementation change. | Seven experience-critical groups are pre-implementation gates. |

The critique found one scope risk: simulating all ninety-two scenarios as unique
screens would be expensive and repetitive. The plan instead implements sixteen
packs using reusable scenes and branch points while retaining scenario-level
coverage tags. It found one architecture risk: a single simulation enum could
look like a domain lifecycle. The plan therefore requires owner-specific mock
facts and treats the label only as a reviewer cursor.
