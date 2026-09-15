# Watt Core Workspace Experience Calibration Notes
## Adaptive Work Surface, Human Turn Mediation & Work-centric Navigation

Date: 2026-09-14

~~~text
STATUS
    PROTOTYPE_CALIBRATION_DIRECTION

HUMAN_DIRECTION
    PARTIALLY_APPROVED

PROTOTYPE_V2
    IMPLEMENTED_AS_DOGFOOD_CANDIDATE

PRODUCTION_IMPLEMENTATION
    NOT_AUTHORIZED

ARCHITECTURE_CHANGES
    NOT_YET_AUTHORIZED
~~~

This is a living product/design notebook derived from clickable-prototype
dogfood. It preserves conclusions and the reasoning behind them; it is not a
frozen production UX specification.

Information in this note is classified as:

- **Human-approved direction:** a product direction to preserve.
- **Prototype v2 candidate:** behavior that still requires Human dogfood.
- **Unresolved:** terminology or interaction detail intentionally left open.
- **Future architecture work:** a capability requiring separate design and
  authorization.

Related records:

- [First-release Human Journey](watt-first-release-human-journey.md)
- [Scenario Inventory](watt-first-release-scenario-inventory.md)
- [Clickable Prototype Plan](watt-clickable-prototype-plan.md)
- [Architecture Tension Register](watt-human-journey-architecture-tensions.md)
- [Experience-before-Production candidate](experience-before-production-candidate.md)
- [Adaptive Work Patterns candidate](watt-adaptive-work-patterns-candidate.md)
- [WIC / SDD Architecture Study Plan](watt-wic-sdd-architecture-study-plan.md)

## 1. Prototype v1 dogfood observation

Prototype v1 was valuable because it made the full Human Journey concrete and
clickable. After roughly two days of repeated use, the strongest Human
experience problem was that the Work surface felt scattered and insufficiently
focused:

- information was distributed across many panels;
- visual priority was unclear;
- the Human could not easily see where attention belonged;
- Conversation competed too strongly with product and engineering Reality;
- Work state, direction, production and Human attention lacked one stable
  spatial model.

This is not merely a request to rearrange cards. The Human Governor proposes a
new core Work-workspace mental model before lower-level Agenda, PWU, controls
and interaction details are frozen.

## 2. Four primary Work information functions

The four-function model is a Human-approved direction. The labels, contents and
visual design remain subject to prototype calibration.

### 2.1 Reality / current state

Answers: **What is true now?**

Candidate contents vary with Work state:

- intended outcome and shared understanding;
- confirmed facts, constraints and important decisions;
- current solution/design or result;
- limitations;
- trust and delivery state.

Reality is an internal working name. Human-facing alternatives such as
“工作概览”, “当前共识”, “当前情况” or “目标与现状” remain unresolved.

### 2.2 Agenda

Answers: **What remains to be resolved or done next?**

Candidate contents include design completeness, unresolved matters, current
direction, meaningful stages, next focus, remaining production outcomes and
decisions approaching Human attention.

Agenda must not be reduced to a traditional task checklist. Its internal
information architecture remains future prototype work.

### 2.3 Production

Answers: **What is Watt actually doing now?**

Candidate contents include ready/queued, waiting, starting, executing,
checkpointed, yielded, recovering, verification activity and meaningful
completed production outcomes.

~~~text
Production Unit / meaningful stage != Execution Slice
~~~

Raw Executor internals remain hidden by default.

### 2.4 Actions

Answers: **What genuinely needs the Human now?**

Candidate contents include decisions, governed corrections, authorization,
credentials/access, material ambiguity and result review. Actions must not
become a generic notification inbox. An item belongs here only when Human
cognition or authority genuinely matters.

## 3. Adaptive workspace projection

The four functions are not four permanently visible, equal dashboard cards.
Their presence and visual weight should respond to Work Reality, stage, Human
attention, production state and—where useful in the future—a recognized
Work/SDD Pattern.

Examples:

- before production: Reality, Agenda and Actions may dominate;
- during production: Reality, Agenda, Production and Actions may all matter;
- at a decision boundary: Actions may dominate;
- after completion: result, Reality and trust may dominate while Production
  recedes;
- after delivery: Agenda may represent optional refinement, not unfinished
  production.

Candidate projection principle:

~~~text
Work Pattern
+ Current Work Stage
+ Current Facts
+ Human Attention
+ Production Reality
-> Human-facing Workspace Projection
~~~

Pattern may guide emphasis, but current engineering/product Reality remains
authoritative. A wrong Pattern must never hide important Work information or
force a rigid dashboard.

## 4. Human-controlled Focus Mode candidate

The Human Governor approves exploring a focused state for each major workspace
function:

~~~text
default adaptive layout
    -> Human focuses one surface
    -> focused surface occupies most of the workspace
    -> other surfaces collapse to concise summaries or headers
~~~

The approximate 80-90% emphasis and exact mechanics are Prototype v2
candidates, not frozen requirements.

The system may recommend where attention belongs, but must not repeatedly steal
layout control from the Human. Once the Human explicitly focuses a surface,
preserve that focus until exit or a genuinely blocking condition. New attention
should normally appear through badges, emphasis or concise warnings rather than
unexpected layout rearrangement.

“Focus Mode” is a working name only.

## 5. Conversation is an interaction plane, not the stage

Conversation remains persistent across the Work, but it is not equal to
Reality, Agenda, Production or Actions.

~~~text
Conversation != Truth

Engineering / Product Reality is the primary workspace.
Conversation is the Human interaction channel around that Reality.
~~~

Many AI products make Chat the stage and business/engineering state secondary.
Watt should invert that hierarchy:

~~~text
Work Reality is the stage.
Conversation is the interface into it.
~~~

The Human should not need to reread historical chat to recover the current
target, accepted constraints, direction, production state, pending action or
result.

## 6. Conversation and Composer candidate

The Human Governor currently prefers Conversation History in a right-side
panel. A candidate Composer has two forms:

- collapsed beneath the right-side Conversation panel for short replies;
- expanded beneath the central Work workspace when input gains focus or becomes
  substantial.

This has both ergonomic and cognitive intent. While composing substantial
input, the most prominent context above should be current Reality, Agenda,
Production and Actions—not historical chat. Product/engineering facts remain
primary; conversation history is supporting context.

This is a Prototype v2 candidate requiring Human dogfood. Exact dimensions,
thresholds and transition behavior are not frozen.

## 7. Human Turn Mediation direction

### 7.1 Product risk

Sending a message that may affect engineering Reality currently can feel unsafe.
The Human may not know whether Watt understood it, whether it is discussion
only, what Reality it changes, whether confirmation is required, when it takes
effect or how it affects in-flight production.

~~~text
Human says something
-> black box
-> maybe it takes effect
-> maybe it does not
-> timing is unclear
~~~

Automatically mutating Reality on every utterance would be equally unsafe. A
mediation/buffering capability is therefore a future architecture direction.

### 7.2 One coherent Watt identity

The Human initially described the need informally as a “系统精灵”, meaning an
intermediate system capability—not a mascot or separate character.

Human decision:

- no mascot or virtual pet;
- no second assistant;
- no independent AI personality;
- no conflicting conversational identity.

The user should perceive one coherent Watt system. Internal working names may
include Human Turn Mediation Layer or WIC Turn Mediation; neither is frozen.

### 7.3 Candidate responsibility chain

~~~text
Human input
    -> Receipt
    -> Interpretation
    -> Impact Assessment
    -> Governance / Timing
    -> Reality change where appropriate
    -> Human feedback
~~~

Candidate responsibilities:

1. acknowledge receipt immediately where possible without model inference;
2. interpret question, correction, constraint, material change, command, side
   discussion or new Motive;
3. assess impact on Conversation, Work facts, constraints, Agenda, production
   direction, in-flight production and Human Authority;
4. determine whether the interpretation may apply, requires confirmation, must
   wait for a safe frontier, needs Work/Steering revision or remains discussion;
5. change Reality only through appropriate authority and governance;
6. report what Watt understood, whether anything changed, what changed, what
   remains pending, when it becomes effective and whether production is affected.

### 7.4 Truthful feedback

Directional example:

Human: “登录以后首页不要自动跳转了。”

Possible receipt: “已收到。我理解为你正在修改当前 Work 的登录后行为约束，
我正在确认它对当前设计和生产的影响。”

Possible governed outcomes include keeping it as discussion, updating the
constraint and direction, or holding production at a safe boundary pending a
decision.

For “先暂停”, Watt must distinguish:

~~~text
Pause request received
!=
Production safely paused
~~~

It must not claim completion before Runtime Reality proves it.

### 7.5 Rationale and boundary

Mediation may provide immediate feedback, causality, Human control, protection
against impulsive statements or automatic fact mutation, Conversation/Truth
separation, timing visibility and safe handling of active production changes.
It may later connect to Adaptive Work Patterns, SDD refinement, Work Formation,
Steering and Runtime safe-frontier semantics.

Exact ownership, persistence and direct-change/reconfirmation rules are not
frozen and require separate architecture authorization.

## 8. Work-centric navigation

The left navigation should primarily organize active or uncompleted Works.
Candidate capabilities include search, semantic grouping, time grouping,
Human-defined grouping, drag/drop and pinning.

Work remains the organizing object. No Project concept is introduced.

### 8.1 Grouping guardrail

Human-approved rule:

~~~text
group label empty
    -> AI may propose or assign a semantic group

group label exists
    -> do not automatically regroup
~~~

This applies whether the existing label was assigned automatically or edited by
the Human. A generic fallback such as “其他” may be used when similarity is
insufficient. Human-defined organization is authoritative for navigation.

Grouping is presentation metadata, not Work domain Truth. Works displayed
together do not thereby acquire a semantic Work relationship.

### 8.2 Pinning boundary

Pinning is personal/workspace navigation metadata. It must not alter Work
priority, Steering, production scheduling or queue allocation.

### 8.3 Active and historical Work

The active view should primarily contain current/non-archived Works across
formation, design, waiting, production, Human attention, result review,
delivered-but-active and refinement states.

History is a separate aggregate navigation view and may support semantic, time,
Human-defined and fallback grouping.

~~~text
production completed
!= verified
!= delivered
!= Human satisfied
!= automatically archived
~~~

Likely archive candidates include Human-satisfied, explicitly closed,
Human-archived or future policy-dormant Work. Exact archive semantics remain
unresolved. History is a projection, not destruction. Once a Work is genuinely
closed and archived, it remains historical Reality; a later desired change
creates a new Motive-bound Work informed by that history rather than reopening
the old Work. See the canonical
[Work Identity, Closure and Archive Invariants](../architecture/work-identity-closure-and-archive-invariants.md).

### 8.4 Global controls

Account, settings, login/logout and future account-level controls belong at the
bottom of the global shell, not inside Work domain surfaces.

## 9. Work-centric delivery organization

The Human Governor rejects a flat artifact/file list as the primary Delivery
experience.

~~~text
Work
    -> Delivery revision(s)
    -> Artifacts / Runtime / Repository / Download / Documents
~~~

Example:

~~~text
Work: Watt 运营平台
    最新交付
        Web application
        Repository update
        Runtime
        Documentation
    历史交付
        Delivery v2
        Delivery v1
~~~

Artifacts gain meaning from the Work outcome that produced them. Users think
in outcomes, not file inventory. Delivery should preserve Watt's Work-centered
model and must not become a generic file manager.

## 10. Emerging UX principle: 差异，不是怪异

Repeated prototype use is producing a form less similar to chat coding tools,
IDEs, project-management dashboards or developer workflow surfaces. Difference
is not a goal by itself.

Human-approved principle:

> 差异，不是怪异。

Differentiation is valuable only when it emerges from Watt semantics, Human
cognitive needs, engineering truth, clearer control and better production
understanding. Do not invent unusual interaction merely to look different.

The Human should orient primarily around current product/engineering Reality,
not historical Conversation:

~~~text
Conversation
    expresses, clarifies, challenges and decides

Work surfaces
    show accumulated current Reality
~~~

## 11. Iterative prototype rationale

Prototype v1 was intentionally broad. Repeated use was necessary to discover
the right high-level workspace structure before Agenda, Production, PWU,
Actions and control details could be responsibly frozen.

~~~text
Prototype v1
    -> Human dogfood
    -> high-level workspace calibration
    -> Prototype v2
    -> Human dogfood
    -> lower-level interaction calibration
~~~

This is intentional iterative product design, not incomplete planning.

The process is also continuing dogfood for
[Experience-before-Production](experience-before-production-candidate.md):

~~~text
broad Journey planning
-> clickable candidate
-> repeated Human use
-> high-level conceptual rejection/calibration
-> cheaper prototype revision
-> only later production implementation
~~~

This is evidence for future evaluation, not proof that the production pattern
is validated.

## 12. Future Pattern compatibility

Pattern recognition may later influence which surfaces exist, what information
matters, which Agenda items are relevant, when Production appears and which
Human Actions matter.

Pattern remains guidance. Work Reality is authoritative. Patterns must not force
a rigid dashboard or workflow, and the Human should not normally select one
manually. This note remains compatible with the future WIC/SDD study and
[Adaptive Work Patterns candidate](watt-adaptive-work-patterns-candidate.md).

## 13. Collaboration model demonstrated

The Human Governor contributes high-quality perception of what feels wrong,
Product Intent, mental-model and experience judgment, and major direction.

Architecture Lead AI translates observations into product/system implications,
distinguishes UI problems from architecture problems, decides when structure
should be added or removed, and protects ownership boundaries.

The repo-grounded Executor faithfully implements approved prototype or
engineering missions and returns Reality/evidence.

This is Human-as-Cognitive-Governor, not Human-as-approval-gate.

## 14. Human-approved directional decisions

1. Work remains the core workspace organizing object.
2. Primary Work information functions are Reality/current state, Agenda,
   Production and Actions.
3. The functions are adaptive and not permanently all visible.
4. They are not fixed equal quadrants.
5. Human-controlled Focus Mode should be explored.
6. Conversation remains a right-side interaction plane.
7. Prototype v2 may explore collapsed-right and expanded-bottom Composer forms.
8. Product/engineering Reality has stronger visual priority than chat history.
9. A mediation layer between Human input and governed Reality is desired.
10. Mediation must not become an independent visible AI personality.
11. Watt remains one coherent system identity.
12. AI semantic grouping applies automatically only to ungrouped Works.
13. Existing group labels must not be silently recomputed.
14. Human organization overrides automatic organization.
15. Active and historical Works are separate navigation views.
16. Archive/history is not technical production completion.
17. Deliveries and artifacts are organized primarily by Work.
18. Queue remains visible where relevant but is not required as top-level
    navigation.
19. Agenda/PWU/control details remain open for later dogfood.
20. Product differentiation follows “差异，不是怪异”.

## 15. Intentionally unresolved questions

Do not resolve in this mission:

- final Human-facing name for Reality;
- adaptive-layout algorithm and Focus Mode mechanics;
- Composer expansion interaction;
- architecture owner and persistence of Human Turn Mediation;
- acknowledgement, interpretation and commit language;
- direct Reality change versus explicit reconfirmation;
- archive semantics and grouping storage;
- Agenda design and Production/PWU projection;
- result/trust presentation;
- control placement, naming and flow;
- production detail density and exact state terminology;
- panel ratios, responsive behavior, visual system and branding.

## 16. Prototype v2 candidate scope

A future separately authorized deterministic prototype may explore:

~~~text
Left
    Work-centric navigation
    search / grouping / pinning / history

Center
    adaptive Work workspace
    Reality / Agenda / Production / Actions
    Human-controlled Focus Mode

Right
    Conversation History

Bottom / contextual
    adaptive Composer
    mediation feedback
~~~

Prototype v2 must remain isolated from production systems. It was not
implemented, modified or started by this mission.

## 17. Current status

~~~text
STATUS
    PROTOTYPE_CALIBRATION_DIRECTION

HUMAN_DIRECTION
    PARTIALLY_APPROVED

PROTOTYPE_V2
    IMPLEMENTED_AS_DOGFOOD_CANDIDATE

PRODUCTION_IMPLEMENTATION
    NOT_AUTHORIZED

ARCHITECTURE_CHANGES
    NOT_YET_AUTHORIZED
~~~

The earlier documentation mission did not start Prototype v2. The separately
authorized v2 prototype mission subsequently implemented the candidate under
`prototype/human-journey/`. This status update preserves that sequence rather
than rewriting the original planning history.

## 18. Transient Current Interaction Layer

### 18.1 Human-approved direction

The v2 workspace places engineering and product Reality in the center and
Conversation History on the right. Showing Watt's active reply only in the
history panel would repeatedly move Human attention away from the Work itself.

The approved candidate direction introduces a transient Current Interaction
Layer near the expanded Composer. `Current Interaction Surface` and `Transient
Reply Surface` remain working terms.

The active pair behaves conceptually as:

~~~text
Human submits
    -> submitted Human turn remains visible near Composer
    -> Watt acknowledges and interprets impact
    -> Watt reply streams in the central Work context
    -> completed reply receives a reading grace period
    -> the pair calmly leaves the transient surface
    -> the same ordered pair becomes Conversation History
~~~

The current Human turn remains visible because the Human may need to reread the
exact instruction, verify wording and compare Watt's interpretation with it.
It is visually subordinate to Watt's current response and Work Reality.

### 18.2 Communication fades; Reality remains

The transient surface owns communication presentation, not accumulated truth.
After an exchange archives:

- a changed constraint remains in Reality;
- a changed next step remains in Agenda;
- a required decision remains in Actions;
- an affected execution state remains in Production.

~~~text
Transient interaction = current communication
Work surfaces         = accumulated current Reality
~~~

This makes `Conversation != Truth` visible rather than merely documented.

### 18.3 Reading protection and long replies

Prototype v2 uses a reversible reading grace period. Archival pauses while the
transient response is hovered, keyboard-focused, selected or manually expanded.
Long responses have bounded height, local scrolling and an explicit expand
action so they do not cover the Work workspace indefinitely. Reduced-motion
preference removes meaningful movement and uses a clean state change.

Exact timing is a prototype calibration value, not product truth.

### 18.4 One active pair and ordered archival

Only one active Human-Watt pair appears near the Composer. If a new Human turn
starts before the previous pair archives, the previous pair first settles into
Conversation History and the new Human turn becomes current. Each settled
message appears in history exactly once and in source order.

### 18.5 Unified Watt identity

The transient response appears to come from the Work workspace and uses the
same Watt identity as the rest of the product. It does not introduce a mascot,
virtual pet, second assistant or mediation personality. Internal mediation may
remain architecturally distinct in future work, but the Human experiences one
coherent Watt system.

### 18.6 Calm transfer

The approved transition is a restrained central fade-out and right-history
fade-in. There are no flying messages, game-like physics, fireworks or mascot
motion. Small opacity, position and blur changes may clarify continuity.

The governing principle is:

> 差异，不是怪异。

### 18.7 Human Turn Mediation feedback in v2

The deterministic prototype may communicate receipt, current interpretation,
whether Work Reality is affected, whether an effect is immediate, whether a
Human decision is required, and whether production must first reach a safe
frontier. It must distinguish a request from a completed Runtime effect—for
example, `pause requested` does not mean `production safely paused`.

This is experience simulation only. It does not establish a production owner,
persistence contract, governance rule or WIC architecture change.

## 19. Adaptive Workspace Morphing

Prototype v2.1 applies the Human Governor's sketch as the spatial source of
truth for the central Work workspace. Reality, Agenda, Production and Actions
remain the same four information functions with stable implementation
identities `surface-1` through `surface-4`.

With four applicable surfaces, overview is a coherent 2×2 field. Focus does
not open another page: the selected surface grows from its current position,
while the remaining applicable surfaces move into meaningful summary regions.
The four focus configurations preserve the relationships in the sketch:

~~~text
FOCUS_1    1 main above; 2 / 3 / 4 summaries below
FOCUS_2    1 summary above; 2 main; 3 / 4 summaries below
FOCUS_3    1 / 2 summaries above; 3 main; 4 summary below
FOCUS_4    1 / 2 / 3 summaries above; 4 main below
~~~

The implementation keeps each surface component and its body mounted while
changing grid coordinates. A restrained FLIP transition explains movement and
size change; a new focus request interrupts the old transition and becomes the
latest target. Reduced-motion preference switches directly to the new layout.
Compressed surfaces remain keyboard-selectable and expose a title, meaningful
current summary and any Human-required signal. Such a signal does not steal
focus.

When fewer surfaces apply, the visible set fills the available area without
inventing empty functions. Narrow layouts retain the same surface identities
and use a readable vertical arrangement.

This focused correction does not decide final surface names, panel ratios,
timing, visual branding or lower-level Reality, Agenda, PWU/Production and
Actions design. It does not change Current Interaction, Conversation,
Composer, Work navigation, Delivery, lifecycle semantics or production
architecture.

## 20. Visual Expression Decoupling

### 20.1 Approved direction

Prototype v2 interaction and workspace exploration may be promising while its
visual style remains explicitly unapproved and replaceable.

> Experience semantics are stable; visual expression is replaceable.

Product and interaction semantics include Work identity, Reality / Agenda /
Production / Actions, adaptive workspace morphing, Conversation History,
Current Interaction, Composer behavior, Human Turn Mediation, navigation,
lifecycle and governed actions.

Visual expression includes color, surface material, typography, border, radius,
shadow, spacing, density, icon treatment, motion intensity and visual hierarchy
styling. Changing visual expression must not require redesigning product
semantics.

### 20.2 Future Design Token / Theme boundary

When production UI work is authorized, establish an explicit visual-system
boundary using Design Tokens / Theme Tokens. Candidate families include:

~~~text
color.background.*
color.surface.*
color.text.*
color.border.*
color.accent.*
radius.*
shadow.*
spacing.*
typography.*
motion.duration.*
motion.easing.*
density.*
~~~

Names are not frozen and no tokens are implemented by this note.

Avoid scattering arbitrary visual constants through domain-oriented components
or directly binding domain state to a color:

~~~text
semantic state
    -> presentation semantic role
    -> theme token

PRODUCTION_RUNNING
    -> status-active
    -> theme-specific expression
~~~

### 20.3 Theme does not redefine product behavior

A Calm, Industrial or Dark Theme may look materially different while
describing the same Watt product. Theme must not redefine Work identity,
information architecture, workspace state, Focus/Morph behavior, Actions,
Conversation, lifecycle or Production semantics.

Conversation placement, Current Interaction, the four workspace functions,
adaptive presence, morph/focus behavior, Work navigation and History separation
are product/interaction architecture. Accent color, border treatment,
typography personality, shadow depth, background tone and icon style are
replaceable visual expression.

Theme, Density Profile and Motion Profile may eventually vary independently,
for example Neutral Theme + Compact Density + Reduced Motion. This is future
flexibility, not a first-release commitment or current theme-switcher priority.

### 20.4 Future implementation guardrail

When formal UI implementation begins:

1. establish the default Design System;
2. express visual semantics through tokens and components;
3. implement the default Watt style carefully;
4. when economically appropriate, prove decoupling with one materially
   different visual configuration;
5. only then consider broader user-selectable themes.

The first release does not need many themes. The architecture must simply avoid
turning temporary prototype aesthetics into permanent product architecture.
Future visual evolution, enterprise branding and accessibility may benefit,
but none is authorized here.

### 20.5 Open decisions

This direction does not freeze Watt's visual identity, colors, typography,
theme count, theme selector, density selector, motion selector or token names.
It changes no prototype or production implementation.
