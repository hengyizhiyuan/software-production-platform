# Work Control Room — Human Review V4

Status: implementation and focused verification in progress; Human retest pending. This is not a closure record.

## Human findings and bounded response

The Current Interaction occupied fixed space even without a turn, mixed system state with conversation, and could lose the expected compact Composer presentation after a later send. V4 makes the latest Human/Watt exchange an on-demand floating surface, leaves older exchanges in History, and models Composer presentation as explicit compact, composing, submitting, waiting, and settled states. The floating surface is conversation-only. Draft content remains browser-persisted; an empty Composer collapses on an outside click, and send collapses it immediately.

Agenda retains the governed milestone hierarchy and active Working Agreements. The manual agreement form and historical/technical detail move to secondary inspection. Production keeps the Human-readable execution state and only state-relevant machine controls; the operator-only Advance One Step fallback moves to governed evidence/detail. Existing agreement persistence, abandonment, and history are unchanged.

Header attention and Actions now share one projection of actually available Human operations. An internal `NEEDS_ATTENTION` status alone does not create a Human badge. A true decision projects its existing action or conversation response; no action produces “No action required.” Exactly one header attention badge is possible.

## Observed stuck Work

Read-only inspection of the pre-existing local Runtime on 2026-09-18 found Work `cd220d14-f8c6-583b-b76c-295bdc3d27a0` at `NEEDS_ATTENTION` / `PRODUCE`, with `what_happens_next = Configure an Executor capability`. Its Attention API returned zero items; Steering reported `STOPPED` with `HUMAN_ATTENTION` despite `steering_outcome = AUTO_CONTINUE`. This is not an executable Human governance decision. V4 presents this condition as a production/capability blocker without a false Human attention badge. The historical Work and Runtime facts are not altered; restoring an eligible Executor for that Runtime is a separate configuration action, not an invented Human decision.

## Deferred Human finding

`EXCESSIVE_CONFIRMATION_AND_REPETITION` remains open for a later WIC/conversation-quality iteration. Human observation: Watt can repeat settled course-table details and seek another “确认” after clear “开始/继续” language, making the interaction feel bureaucratic. V4 does not change WIC prompts, admission, candidate-first logic, Guided Design, or Human Authority.

## Review boundary

Focused verification on 2026-09-18: 57 affected Node UI/state/appearance/response tests passed; the working-agreement PostgreSQL integration test passed against the isolated `spg_test` database; JavaScript syntax, Python compile/import, `uv lock --check`, and `git diff --check` passed. The Work-source symlink test could not execute on this Windows host because symlink creation returned WinError 1314; this is a host permission limitation, not a passed test.

Browser review of the V4 preview at `http://127.0.0.1:8051/app` confirmed: no empty Current Interaction panel; compact-to-expanded Composer retains its bottom anchor (approximately 1 px difference); outside click with an empty draft collapses; non-empty draft survives outside click and reload; the 2×2 Reality/Agenda/Production/Actions geometry remains intact for an isolated draft Work; exactly one header attention badge corresponds to the visible `Refine Draft` action; Working Agreement creation and manual Advance One Step live in secondary evidence rather than Agenda/Production. No real Provider Turn was invoked for this focused browser check. Two-turn streaming and the historical Work's post-configuration progression still require Human/Provider retest; deterministic ownership and second-send state transitions are covered by focused tests.

The isolated review project is `watt-control-room-v4-human-review`. It has a dedicated PostgreSQL and Runtime volume, plus one clearly named draft Work created through the public API solely for four-surface browser verification. No approval or production step was started. The uncommitted V4 web source is mounted read-only into this preview; it is **not** an activated Trusted Baseline. The historical `watt-local-current` Runtime and all its facts remain unchanged. Human acceptance and formal closure remain separate decisions.
