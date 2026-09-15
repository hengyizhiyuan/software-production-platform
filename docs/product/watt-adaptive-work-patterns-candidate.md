# Watt Adaptive Work Patterns
## WIC Focused Refinement & Production Pattern Candidate

Date: 2026-09-14

~~~text
PATTERN_GUIDANCE_DIRECTION
    APPROVED

PATTERN_TAXONOMY
    NOT_FROZEN

IMPLEMENTATION
    NOT_STARTED

UX_DOGFOOD_REVIEW
    PENDING

PATTERN_DETAIL
    CANDIDATE / REQUIRES_DOGFOOD
~~~

This memo preserves the candidate detail discovered through Watt WIC dogfood
and external SDD study. The
[WIC Intelligence Architecture Closure](../architecture/watt-wic-intelligence-architecture-closure.md)
approves Adaptive Work Pattern guidance as an architecture direction while
leaving taxonomy, representation, routing, confidence, blending, switching,
UI, and implementation unfrozen. Existing lifecycle and ownership boundaries
remain unchanged.

## 1. Dogfood finding

WIC deliberately permits open conversational refinement before Work Admission.
This protects an important invariant:

> A Human's first expression must not be prematurely forced into a rigid schema
> or immediately converted into Work.

Human dogfood exposed the complementary failure mode:

- conversation can expand without a strong sense of convergence;
- Watt may repeatedly rediscover what should be discussed next;
- the Human may not feel that Watt recognizes the kind of problem;
- useful questions can become mixed with low-value exploration;
- interaction may feel less intelligent even when the model is capable;
- Work Formation may lack a natural professional structure.

~~~text
DO NOT PREMATURELY STRUCTURE
!=
REMAIN COMPLETELY UNSTRUCTURED FOREVER
~~~

The candidate response is to preserve natural Human expression while allowing
Watt to progressively recognize a suitable Work or Production Pattern and use
it to focus subsequent refinement.

## 2. External reference: Kiro

Kiro is an external reference, not a design authority. Useful mechanisms to
study include spec-driven development, requirements-first and design-first
flows, Quick Spec, Bug Fix Spec, explicit Requirements -> Design -> Tasks
artifacts, requirements analysis for ambiguity/conflicts/assumptions/missing
edge cases, and sandboxed execution.

The lesson is not to copy Kiro's UI, artifact sequence or developer workflow.
Complex AI software production can benefit from recognized work patterns that
constrain the reasoning/search space and clarify what must become sufficiently
understood before implementation. Watt must preserve its own product paradigm.

## 3. Candidate principle

> Pattern constrains the AI's search space, not the Human's expression space.

The Human communicates naturally and should not normally need to know which
internal Pattern, workflow template, requirements/design ordering or production
recipe Watt is applying.

~~~text
Human Motive
    -> Open WIC Refinement
    -> Sufficient semantic signal
    -> Work Pattern Recognition
    -> Pattern-guided focused refinement
    -> Work Formation / governed production
~~~

The desired perception is: Watt understands the nature of my problem and knows
what matters next. It is not: Watt loaded Workflow Template #7.

## 4. Uncertainty and adaptation

This candidate is not:

~~~text
first message -> classifier -> fixed workflow
~~~

Initial interaction may remain OPEN / UNCLASSIFIED. A possible, non-frozen
lifecycle is:

~~~text
OPEN
    -> CANDIDATE_PATTERN
    -> PATTERN_CONFIDENCE_SUFFICIENT
    -> PATTERN_GUIDED_REFINEMENT
~~~

If later Reality contradicts the Pattern, Watt should reassess, adapt and
reroute. Pattern is guidance and must never silently override Human Intent.

## 5. Initial exploration set

Illustrative Pattern families include:

- NEW_PRODUCT;
- PRODUCT_FEATURE;
- BUG_FIX;
- REFACTOR;
- PERFORMANCE_OPTIMIZATION;
- UX_REDESIGN;
- MIGRATION;
- EXTERNAL_INTEGRATION;
- TECHNICAL_SPIKE;
- INCIDENT_RECOVERY;
- MAINTENANCE_CHANGE.

This is not a frozen taxonomy, and these are not necessarily future
user-visible names. They illustrate that different Motives benefit from
different professional reasoning structures.

## 6. Candidate Pattern contents

A Pattern should not primarily prescribe screens or fixed steps. It may express:

1. what Watt must understand before production can safely proceed;
2. which optional artifacts could reduce uncertainty;
3. what must be sufficiently resolved before Work advances;
4. where Human cognition or authority has high value;
5. what evidence normally matters;
6. which recurring failures deserve explicit attention.

Examples:

- BUG_FIX: current and expected behavior, reproduction, affected and unchanged
  scope, evidence and regression risk.
- PERFORMANCE_OPTIMIZATION: baseline, workload, target, bottleneck evidence,
  allowed trade-offs, measurement method and regression constraints.
- NEW_PRODUCT: users, Motive, desired outcome, primary scenarios, constraints,
  Human Journey, prototype/experience validation and delivery form.

Possible artifacts include Scenario Inventory, requirements, Human Journey,
prototype, architecture decision, benchmark, root-cause evidence and migration
plan. Artifacts are optional according to Reality; no Pattern requires every
artifact.

## 7. Adaptive Pattern versus fixed workflow

~~~text
FIXED WORKFLOW
    predefined steps must execute in order

ADAPTIVE WORK PATTERN
    defines obligations, useful artifacts, typical decisions and proven
    production practices, while Reality determines exact execution
~~~

An Adaptive Work Pattern should allow Watt to omit irrelevant steps, deepen
important steps, reorder work when Reality demands, add investigation, change
Pattern and combine Pattern mechanisms when justified. It supplies professional
structure without procedural bureaucracy.

## 8. Proportional process depth

> Process depth should scale with ambiguity, impact, risk and cost of being
> wrong.

~~~text
tiny deterministic bug
    -> lightweight bug pattern -> evidence -> fix -> regression

complex production defect
    -> reproduction -> root-cause investigation -> impact analysis
    -> design/fix plan -> production -> extended verification

small UI feature
    -> bounded journey or local prototype when useful

new product
    -> Human Journey -> Scenario Inventory -> Tension Register
    -> clickable prototype -> Human Experience Acceptance
~~~

One universal production workflow is therefore unlikely to be optimal.

## 9. Relationship to Experience-before-Production

The [Experience-before-Production candidate](experience-before-production-candidate.md)
defines a Human-reviewable experience baseline for sufficiently ambiguous or
high-impact product Work. Adaptive Work Patterns may eventually guide whether
that process is useful and how deeply it should be applied:

- NEW_PRODUCT: strong candidate for the full process;
- LARGE_PRODUCT_FEATURE: bounded Journey and prototype slice;
- BUG_FIX: usually no full product prototype;
- PERFORMANCE_OPTIMIZATION: benchmark and evidence-oriented refinement;
- UX_REDESIGN: strong Human Journey and prototype emphasis.

This memo promotes neither candidate into an implemented or frozen first-release
capability.

## 10. WIC and ownership boundaries

WIC retains responsibility for Human interaction and semantic interpretation.

~~~text
Human
  -> WIC
  -> Motive / current Work Reality
  -> Pattern Recognition
  -> Pattern Guidance
  -> WIC asks, recommends and refines more intelligently
~~~

Pattern Guidance may identify what matters now, which question has the highest
decision value, what not to ask, when enough is known and which artifact could
reduce uncertainty.

Pattern is not a Truth owner. Existing boundaries remain:

- Human Intent and Authority remain with the Human Governor;
- WIC owns interaction and semantic interpretation;
- Work Reality remains governed Reality;
- Steering owns what should happen next;
- Verification owns verification evidence;
- Executor owns how to execute an admitted production step.

The exact relationship to Guided Design and Steering remains undecided.

## 11. Perceived-intelligence hypothesis

A capable model may feel unintelligent if the surrounding system repeatedly
asks it to rediscover the problem type, relevant information, next question and
meaning of ready. A validated Pattern could provide prior professional
structure.

~~~text
Perceived Intelligence
approximately equals
Model Capability
x Relevant Context
x Correct Problem Frame
x Appropriate Production Pattern
~~~

This is a future dogfood hypothesis, not a fact or marketing claim. Better
orchestration may make the same model feel substantially more capable, but Watt
must validate that effect.

## 12. Production craft and learning direction

This candidate reconnects with Watt's production craft or route-library idea,
but rejects a static problem type -> fixed procedure mapping.

~~~text
Versioned Production Patterns
+ Reality-adaptive routing
+ Evidence from prior production
~~~

Patterns may eventually evolve from successful Works, failures, Guardian
findings, rework, Human corrections, cost, verification outcomes and production
performance. No learning implementation is authorized here.

If implemented later, Patterns should likely be versioned engineering facts
rather than hidden prompt fragments. Potential future traceability is:

~~~text
Work -> Pattern family -> Pattern revision -> adaptation rationale
-> artifacts -> Human decisions -> outcome -> verification -> lessons
~~~

This does not freeze a persistence design.

## 13. Future ECF relationship

~~~text
ECF
    provides decision-scoped Reality

Pattern
    identifies useful categories of Reality

WIC / Steering / Executor
    consume role-appropriate context
~~~

Pattern definitions do not replace ECF. This memo neither implements nor
redesigns ECF.

## 14. Sandbox reference boundary

Kiro's sandbox model is worth future study for cloud execution packaging,
Internet access expression, secret/environment boundaries, resource capability
exposure, short-lived credentials, user-facing permissions and isolated
execution lifecycle.

Watt-native Executor already owns workspace isolation, Tool Host, effect
semantics, fencing, checkpoint/recovery, multi-repository workspace, hostile
filesystem/network boundaries and UNKNOWN reconciliation. The external
sandbox reference is therefore mainly useful for productization and
capability/permission expression, not as a reason to reopen Executor
architecture.

## 15. Explicit non-decisions

This memo does not decide:

- exact Pattern taxonomy or count;
- code/data/config representation;
- persistence model;
- routing algorithm or confidence mechanism;
- automatic Pattern switching;
- UI presentation or Human override;
- commercial visibility;
- first-release inclusion;
- exact Guided Design relationship;
- exact Steering relationship.

No Work Pattern routing, WIC, Work lifecycle, Guided Design, Steering, Executor
or clickable-prototype change is authorized.

## 16. Revisit point and evaluation

First complete the current Human Governor clickable-prototype review. Preserve
observations about unfocused conversation, unnecessary questions, missed Work
type recognition, useful Pattern guidance, excessive rigidity, appropriate
Human Journey/prototype triggers and cases where production should proceed
directly.

After that review, perform one combined calibration of WIC interaction, Work
Formation, Adaptive Work Patterns, Human Journey, Experience-before-Production,
prototype behavior and architecture/data-model impacts. Avoid piecemeal
production changes before that review unless separately authorized.

Evaluate:

1. Does Pattern guidance make WIC materially more focused?
2. Does it reduce unnecessary dialogue turns?
3. Does it improve Work Formation quality?
4. Does it reduce Product Intent drift?
5. Does it reduce token, wall-clock and Human cost?
6. Can Watt recognize a Pattern without premature classification?
7. Can Watt safely reroute when the initial Pattern is wrong?
8. Does the Human feel Watt is smarter rather than more procedural?
9. Do Patterns constrain AI freedom only where useful?
10. Does quality improve without workflow bureaucracy?

After architecture synthesis, the calibrated status is:

~~~text
PATTERN_GUIDANCE_DIRECTION
    APPROVED

PATTERN_TAXONOMY
    NOT_FROZEN

IMPLEMENTATION
    NOT_STARTED

UX_DOGFOOD_REVIEW
    PENDING

PATTERN_DETAIL
    CANDIDATE / REQUIRES_DOGFOOD
~~~
