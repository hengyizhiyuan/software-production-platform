# Watt First-release Scenario Inventory

## 1. Use of this inventory

This inventory is the coverage contract for later prototype construction and
Human review. Priority means:

- **P0:** indispensable first-release journey and prototype scene.
- **P1:** required supporting, branch, exception, or recovery journey.
- **P2:** useful first-release direction that may use a lighter prototype scene.
- **DEFERRED:** intentionally outside the first-release prototype.

Category identifies the primary test shape. A row can still participate in a
larger journey with other shapes. “Outcome” describes the expected Human-visible
result, not a new domain transition.

The frozen planning inventory contains **92 scenarios**:

| Priority | Count |
|---|---:|
| P0 | 50 |
| P1 | 35 |
| P2 | 3 |
| DEFERRED | 4 |

Its primary shape coverage is 27 happy paths, 26 branches, 10 exceptions, 12
recoveries, and 17 management scenarios.

## 2. Pre-Work and Motive

| ID | Scenario | Priority | Category | Human goal | Entry | Expected outcome | Involved capabilities |
|---|---|---|---|---|---|---|---|
| J01 | Vague initial idea | P0 | happy path | Explore an undeveloped idea without completing a form | New Home, no Work | Watt offers a useful provisional understanding and one valuable next move; no Work is created | WIC, Conversation |
| J02 | Direct question before Work | P0 | branch | Get an answer without starting production | New or existing pre-Work conversation | Direct answer; question remains conversation unless the Human later expresses a Motive | WIC |
| J03 | Exploratory brainstorming | P1 | happy path | Develop possibilities without commitment | Pre-Work conversation | Options and judgment accumulate as interpretation context; no admission pressure | WIC, design intent |
| J04 | Add business context | P0 | happy path | Improve Watt's understanding over several turns | Active pre-Work conversation | Shared understanding incorporates relevant context without repeating known facts | WIC |
| J05 | Correct Watt | P0 | branch | Replace a wrong interpretation quickly | Watt has stated an interpretation | Watt accepts the correction, updates later reasoning, and does not defend the old view | WIC, interpretation revision |
| J06 | Disagree with recommendation | P1 | branch | Keep intent while rejecting Watt's judgment | Watt recommends a direction | Watt explains trade-offs briefly, accepts the choice, and preserves the Human decision | WIC, Human Authority |
| J07 | Ask what Watt recommends | P0 | happy path | Receive a clear expert judgment based on known context | Sufficient conversational context | Watt gives one recommendation with basis and trade-off, then asks only a material question | WIC |
| J08 | Request more detail | P1 | branch | Deepen one part without restarting discovery | Watt has answered or proposed | Detail expands in context and preserves prior constraints | WIC |
| J09 | Insufficient information | P1 | exception | Understand what is missing and why it matters | A material decision cannot be made | Watt states the provisional assumption or asks one high-value question; it does not launch a questionnaire | WIC |
| J10 | Multiple plausible interpretations | P0 | branch | Choose the intended meaning without wrestling with jargon | Input materially supports two outcomes | Watt contrasts the consequential difference and lets the Human choose or clarify | WIC, design intent |
| J11 | Not ready to create Work | P0 | branch | Continue thinking or leave safely | Watt judges the idea actionable | The Motive remains available; no Work, asset binding, or production authority is created | WIC, Interaction |
| J12 | Clearly ready to create Work | P0 | happy path | Move from discussion to a durable collaboration | Shared understanding is actionable | Watt presents a Work Formation Review rather than silently creating Work | WIC, Work formation |
| J13 | Accidental topic change | P1 | branch | Ask an unrelated aside without derailing the Motive | Active pre-Work conversation | Watt answers or clarifies relationship while preserving the original Motive | WIC, focus classification |
| J14 | Genuinely new Motive | P0 | branch | Start a distinct outcome without corrupting current context | Input is materially unrelated | Watt recommends a new conversation/Work context and keeps existing Reality unchanged | WIC, Interaction relationship |
| J15 | Return to previous pre-Work Motive | P1 | management | Resume exploration with continuity | Dormant pre-Work conversation exists | Prior understanding is restored and summarized; the Human continues without a new Work | WIC, Interaction history |

## 3. Work formation, admission, and assets

| ID | Scenario | Priority | Category | Human goal | Entry | Expected outcome | Involved capabilities |
|---|---|---|---|---|---|---|---|
| J16 | Formation Review ready | P0 | happy path | See exactly what Watt proposes to work on | WIC readiness reached | Objective, outcome, scope, constraints, expected artifact, and production boundary are readable before admission | WIC, Work projection |
| J17 | Human admits proposed Work | P0 | happy path | Authorize a durable Work from the reviewed proposal | Exact formation proposal visible | One Work is admitted with provenance; production authority remains separate | Work, Human Authority |
| J18 | Formation understanding is wrong | P0 | branch | Correct the proposal without creating Work | Formation Review visible | The proposal returns to refinement and no Work is created | WIC, Work formation |
| J19 | Add final constraint | P0 | branch | Amend the exact proposal before admission | Formation Review visible | Constraint is incorporated into a revised review; old readiness does not authorize the revision | WIC, Work formation |
| J20 | Postpone admission | P1 | branch | Save progress and decide later | Formation Review visible | Review remains resumable and no authority transfers | Interaction, Work formation |
| J21 | Reject formation proposal | P1 | branch | Decline the proposed Work cleanly | Formation Review visible | Proposal is closed or returned to conversation without Work creation | WIC, Human Authority |
| J22 | No existing repository | P0 | happy path | Build software without preparing infrastructure | Admitted Work, empty asset scope | Design continues; Watt explains that a managed workspace can be created at production readiness | Work, Assets |
| J23 | Attach existing repository | P0 | happy path | Use code the Human already has | Work exists; repository reference supplied | Watt observes capability and presents an explicit Work-scoped binding decision | Assets, Human Authority |
| J24 | Multiple relevant assets | P1 | branch | Use repositories, documents, designs, or targets together | Work needs more than one input/target | Assets appear by role and capability; Work identity remains stable | Assets, Work |
| J25 | External asset needs authorization | P0 | exception | Grant only the access needed | Asset is discoverable but capability is not granted | Exact access purpose and consequence are shown; Work can wait or use an alternative | Assets, Human Authority, Attention |
| J26 | Unsupported asset or capability | P1 | exception | Know what Watt cannot use and how to proceed | Capability check fails | Unsupported state and safe alternatives are clear; no fake binding or hidden block | Assets, Attention |
| J27 | Asset changes outside Watt | P1 | recovery | Avoid acting on stale material | Bound asset fingerprint no longer matches | Watt re-observes, explains impact, and revalidates or requests a governed decision | Assets, Steering, recovery |

## 4. Guided Design and planning

| ID | Scenario | Priority | Category | Human goal | Entry | Expected outcome | Involved capabilities |
|---|---|---|---|---|---|---|---|
| J28 | Watt proposes design structure | P0 | happy path | Turn intent into a coherent product/design shape | Work admitted | Watt focuses on the most consequential area and explains why | Guided Design, WIC |
| J29 | Accept recommendation | P0 | happy path | Advance without unnecessary ceremony | Recommendation visible | Decision is reflected in design Reality and the next focus follows | Guided Design, Human Authority |
| J30 | Change business requirement | P0 | branch | Update the desired behavior and understand impact | Guided Design active | Watt distinguishes refinement from material scope change and updates the right owner | WIC, Work, Guided Design, Steering |
| J31 | Change technical constraint | P1 | branch | Add a required platform or integration constraint | Guided Design active | Constraint impact, conflicts, and revised design direction are visible | Guided Design, Work |
| J32 | Unresolved design decision | P0 | exception | Make a material choice with enough context | Two viable choices affect outcome | Watt recommends one, explains trade-offs, and records the Human choice | Guided Design, Attention, Human Authority |
| J33 | Request alternatives | P1 | branch | Compare credible options | Watt has recommended one approach | A compact comparison preserves Watt's judgment and lets the Human choose | Guided Design, WIC |
| J34 | Design ready for production | P0 | happy path | Know that design is sufficient and what will be built | Required design areas satisfied | Readiness is explained with remaining assumptions; production proposal becomes reviewable | Guided Design, Steering |
| J35 | Multiple meaningful stages | P0 | happy path | Understand the path without reading executor tasks | Production requires several outcomes | Plan names ordered outcome stages with verification and dependencies | Steering, PWU planning |
| J36 | Plan changes after new input | P1 | branch | See how new information changes what happens next | New relevant Human input before production | Steering revises direction from current Reality and explains what moved | WIC, Work, Steering |
| J37 | Material change during production | P0 | exception | Change scope without corrupting in-flight work | Production active; input changes destination/authority | Current production is safely bounded or paused; a governed change decision is presented | WIC, Steering, Queue, Human Authority |
| J38 | Production proposal review | P0 | happy path | Confirm output, targets, and checks before execution | Design and plan ready | Plain production proposal is accepted, refined, or declined without exposing contract internals | Steering, PWU, Assets, Human Authority |
| J39 | Emerging direction kept separate | P1 | branch | Preserve a future idea without changing current Work | Related but non-current idea appears | Idea is retained as emerging direction and does not mutate admitted scope | WIC, Steering |

## 5. Queue, production, progress, and control

| ID | Scenario | Priority | Category | Human goal | Entry | Expected outcome | Involved capabilities |
|---|---|---|---|---|---|---|---|
| J40 | Ready but queued | P0 | happy path | Know the Work is admitted and waiting normally | Runnable stage admitted to queue | Queue reason, current order context, and next transition are visible | Queue, Work |
| J41 | Waiting for capacity | P0 | branch | Distinguish capacity wait from failure | No compatible capacity available | Honest wait explanation appears without fake ETA; no Human action is invented | Queue, Capacity |
| J42 | Allocated | P1 | happy path | Know Watt is about to begin | Scheduler grants capacity | UI moves from waiting to preparing/starting with the same stage identity | Queue, Executor |
| J43 | Running | P0 | happy path | Know what Watt is doing now | Native Attempt active | Meaningful current activity, elapsed time, completed stages, and next likely step are visible | Executor, Work projection |
| J44 | Checkpoint saved | P1 | recovery | Trust that useful progress can survive interruption | Executor reaches durable frontier | Calm checkpoint marker appears in history; it is not presented as product completion | Executor, checkpoint |
| J45 | Temporarily yielded | P1 | branch | Understand a planned resource handoff | Active execution yields | Same stage shows “saved and waiting to continue”; no new Work/PWU is implied | Executor, Queue |
| J46 | Requeued | P1 | recovery | Know saved work will continue | Yield or recoverable interruption settled | Queue entry retains continuity and reason; duplicate production is not shown | Queue, recovery |
| J47 | Resumed from checkpoint | P0 | recovery | Continue without losing valuable work | Compatible allocation and checkpoint exist | Activity resumes from retained frontier and recovery overhead is transparent in detail | Queue, Executor, checkpoint |
| J48 | Waiting for provider capacity | P1 | branch | Know an external service wait is being handled | Provider unavailable or rate-limited within policy | User sees “waiting for production capacity,” impact, and ownership; raw provider calls stay hidden | Executor, Queue |
| J49 | Waiting for Human | P0 | exception | See exactly what decision blocks progress | A governed decision or credential is required | Queue and Work link to one Needs-me item with consequence and choices | Queue, Attention, Human Authority |
| J50 | Waiting for external resource | P1 | exception | Resolve an unavailable capability without debugging | Tool, asset, runtime, or account prerequisite missing | Watt explains the needed resource and alternative/continue-later options | Queue, Assets, Attention |
| J51 | Automatic recovery after failure | P0 | recovery | Let Watt handle ordinary faults | Recoverable execution/tool failure | Watt preserves facts, retries only when semantics allow, and reports recovery without demanding Human debugging | Executor, recovery |
| J52 | `UNKNOWN` and reconciliation | P0 | recovery | Know Watt is being cautious about uncertain effects | Process/provider outcome cannot prove external Reality | Unsafe continuation is fenced; Watt re-observes before residual work or asks for action | Recovery, Executor, Attention |
| J53 | Pause by Human | P1 | management | Temporarily stop new work safely | Active or queued stage supports governed pause | Pause request and eventual safe state are distinct; progress remains retained | Human Authority, Queue, Executor |
| J54 | Resume by Human | P1 | management | Continue a paused Work | Paused stage remains compatible | Watt revalidates current basis and resumes/requeues without changing stage identity | Human Authority, Queue, recovery |
| J55 | Stop current production | P1 | management | End the active production path safely | Governed stop is supported | New effects stop, uncertain effects reconcile, and retained output/history remain visible | Human Authority, Executor, recovery |
| J56 | Cancel queued stage | P1 | management | Withdraw work that has not begun | Stage is queued with no active effects | Queue entry is cancelled with clear impact; Work remains available for replanning | Queue, Human Authority |
| J57 | Multiple stages in one Work | P0 | happy path | See meaningful progress across a longer outcome | Plan contains several PWUs | Finished/current/next stages are clear; execution intervals remain hidden | Steering, PWU, Executor |
| J58 | Multiple Works compete for capacity | P1 | management | Understand why one Work waits while another runs | Two Works are runnable | Global Queue explains capacity allocation without turning user into scheduler operator | Queue, Capacity |
| J59 | Stage completes and next begins | P0 | happy path | See continuity across outcome stages | One PWU satisfied; plan has next direction | Milestone history updates and Steering admits or prepares the next stage | Verification, Steering, Queue |
| J60 | Browser stays usable during reply/production | P0 | branch | Continue typing and navigate without corrupting turns | Conversation response or production stream active | Composer accepts ordered pending messages; reconnect does not duplicate or cancel work | Conversation, event stream, Queue |

## 6. Verification, result review, authorization, and delivery

| ID | Scenario | Priority | Category | Human goal | Entry | Expected outcome | Involved capabilities |
|---|---|---|---|---|---|---|---|
| J61 | Verification in progress | P0 | happy path | Know Watt is checking the exact output | Result-ready claim exists | Product says what is being checked and keeps “generated” distinct from “passed” | Verification, Executor claim |
| J62 | Verification passes | P0 | happy path | Understand why the result is reviewable | Required checks pass on exact output | Concise trust summary and inspectable evidence lead to result preview | Verification, Candidate |
| J63 | Verification fails; Watt self-corrects | P0 | recovery | Let Watt fix an ordinary defect autonomously | Failed obligation is within admitted scope and recoverable | Failed check remains in history; governed correction runs and a new exact result is verified | Verification, Steering, Executor |
| J64 | Verification failure needs Human | P1 | exception | Decide when correction changes destination, risk, or access | Failure cannot be corrected within current authority | Needs-me item explains the violated obligation and decision options | Verification, Attention, Human Authority |
| J65 | Preview new application | P0 | happy path | Experience the produced software before approval | Verified previewable application Candidate | Isolated runtime preview opens with exact result identity and known limitations | Candidate preview, Verification |
| J66 | Preview code/software change | P0 | happy path | Understand the change without reading every file | Verified change Candidate | Summary, key behavior, affected areas, checks, and optional diff/evidence are available | Candidate preview, Assets |
| J67 | Preview multiple repositories/assets | P1 | branch | Understand one coherent result across targets | Aggregate result includes multiple targets | Target-by-target impact plus cross-target verification appears as one review | Candidate vector, Assets, Verification |
| J68 | Known limitation or material risk | P0 | exception | Make an informed decision despite residual risk | Reviewable result has disclosed limits | Limitation, consequence, mitigation, and authorization impact are prominent | Verification, Candidate, Human Authority |
| J69 | Request result correction | P0 | branch | Ask Watt to improve the result before integration | Preview open | Current result stays immutable; correction becomes governed follow-up and new result revision | WIC, Steering, Candidate |
| J70 | Reject result | P1 | branch | Decline integration without losing evidence | Preview open | No integration occurs; rejection reason informs replanning while history remains | Human Authority, Candidate |
| J71 | Authorize exact result | P0 | happy path | Approve what was inspected and where it will apply | Eligible exact result and target set visible | Authorization binds that revision only and clearly states expected effects | Human Authority, Candidate |
| J72 | Partial multi-target convergence | P1 | recovery | Understand and safely complete a partially applied authorization | Some targets advanced and others did not | Target facts, safe forward-completion status, and need for reauthorization are explicit | Integration, recovery, Assets |
| J73 | Delivery available | P0 | happy path | Open or obtain the usable outcome | Required commit/trust boundary complete | Runtime, repository update, or download action is present with a manifest and trust summary | Runtime Commit, Delivery |
| J74 | Review delivery and mark satisfaction | P0 | happy path | Decide whether the outcome works in practice | Delivery usable | Human can accept or request changes; only Human acceptance marks current satisfaction | Delivery, Human acceptance, Work |

## 7. Existing Work, delivery history, and resource management

| ID | Scenario | Priority | Category | Human goal | Entry | Expected outcome | Involved capabilities |
|---|---|---|---|---|---|---|---|
| J75 | View and filter Works | P0 | management | Find active, paused, completed, and needs-me Work | Returning Home or Work list | Status and recent change are scannable without a Goal hierarchy | Work projections |
| J76 | Switch Work without losing context | P0 | management | Move between outcomes safely | More than one Work exists | Each Work restores conversation draft, current Reality, and position | Work, Interaction |
| J77 | Rename Work | P2 | management | Use a memorable Human name | Work exists | Display name changes without changing identity, authority, or history | Work projection |
| J78 | Hide/archive Work | P2 | management | Reduce clutter without deleting history | Dormant/completed Work exists | Work leaves default views and remains findable/restorable | Work projection |
| J79 | See changes since last visit | P0 | management | Catch up quickly | Durable events occurred while Human absent | Summary links each material change to current Work context | Work events, Attention, Delivery |
| J80 | Inspect delivery history | P1 | management | Reopen an earlier usable result and basis | Work has one or more deliveries | Exact delivery, trust basis, assets, and later revisions are distinguishable | Delivery, Work |
| J81 | Refine completed Work | P0 | happy path | Extend or improve the same outcome | Satisfied Work and prior delivery exist | Conversation reopens; Watt distinguishes refinement from a new Motive and starts governed revision path | WIC, Work, Steering |
| J82 | Basic usage/capacity visibility | P2 | management | Understand a commercially meaningful limit | Account/capacity restriction affects progress | Product shows remaining allowance or action in plain terms without provider-call controls | Capacity, account projection |

## 8. Cross-cutting exception and recovery

| ID | Scenario | Priority | Category | Human goal | Entry | Expected outcome | Involved capabilities |
|---|---|---|---|---|---|---|---|
| J83 | Browser disconnect/reconnect | P0 | recovery | Return without cancelling or duplicating work | Tab closes or event stream breaks | Current durable state reloads from cursor/projection; queued messages and production remain coherent | Event stream, Interaction, Executor |
| J84 | Runtime or worker restart | P1 | recovery | Trust that service restart does not erase useful progress | Runtime process/worker restarts | Lease/recovery logic restores a coherent frontier and UI explains resumed/recovering state | Executor, recovery, checkpoint |
| J85 | Tool failure | P1 | recovery | Avoid becoming a tool-debug relay | Tool returns failure or uncertain effect | Watt records certainty, uses a safe alternative/recovery when authorized, or asks for the needed decision | Executor, recovery |
| J86 | Asset unavailable or permission lost | P1 | exception | Restore access or choose an alternative | Bound asset cannot be read/written | Impact, required capability, reauthorize/replace/continue-later choices are shown | Assets, Attention, Human Authority |
| J87 | Stale decision surface | P0 | recovery | Avoid approving an obsolete result or plan | Reality changes while review is open | Action is rejected safely, current facts reload, and changed basis is highlighted | Projections, Human Authority, recovery |
| J88 | Return after long absence | P1 | management | Reconstruct the story without reading logs | Work changed across multiple stages/deliveries | Change summary, current outcome, present need, and next step form a coherent narrative | Work events, Delivery, Attention |
| J89 | Enterprise role and approval chains | DEFERRED | management | Delegate authority across an organization | Multi-user enterprise governance requested | Explicitly outside first release; prototype assumes one accountable operator | Future identity/governance |
| J90 | Advanced provider and worker console | DEFERRED | management | Tune models, reasoning effort, retries, and workers | Expert infrastructure administration requested | Explicitly outside first release; engineering diagnostics remain separate | Provider/Executor operations |
| J91 | Future Guardian assurance decision | DEFERRED | branch | Consume Guardian judgments | Guardian exists | No first-release simulation claims Guardian behavior | Future Guardian |
| J92 | Future ECF capability marketplace | DEFERRED | management | Select qualified external production capabilities | ECF exists | No first-release simulation claims ECF behavior | Future ECF |

## 9. Coverage notes

The inventory covers the continuous value journey from Motive through Delivery
and later re-entry, as well as global Work management, Queue, Human Attention,
assets, capacity, authorization, history, exceptions, and recovery. Prototype
scenario packs group these rows into replayable narratives; a pack is not a new
scenario or a new source of truth.

No row authorizes production implementation. Priorities are prototype and
first-release experience priorities; architecture and Runtime owners remain as
defined by their source-of-truth documents.
