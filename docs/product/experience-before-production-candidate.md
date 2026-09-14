# Experience-before-Production
## Watt Prototype Review & Human Cognitive Governance — Candidate Production Pattern

Status:

```text
CANDIDATE
DOGFOOD_PENDING
NOT YET FROZEN AS PRODUCT REQUIREMENT
```

This document records a product/production-pattern candidate discovered during
Watt's own Human Journey / UX reconstruction dogfood.

It must not yet be treated as a frozen first-release requirement.

The pattern should be promoted only after the current Watt prototype-first UX
dogfood demonstrates material value in reducing intent drift, feature omission,
rework, implementation waste, and Human misunderstanding.

---

## 1. Core idea

For high-ambiguity, high-impact or product-level software Work, Watt should not
move directly from conversational requirement refinement into formal software
production.

Instead, Watt should externalize the intended product into a Human-reviewable
experience baseline before expensive implementation begins.

Candidate production chain:

Human Motive
→ Conversational Refinement
→ Work Intent
→ Human Journey
→ Scenario Inventory
→ Architecture Tension Register
→ Prototype Scenario Packs
→ Clickable Experience Prototype
→ Reviewer Mode
→ Human Experience Calibration
→ Approved Human Experience Baseline
→ Architecture / Data Model Reconciliation
→ Formal Production
→ Verification / Assurance
→ Runtime Fidelity Acceptance
→ Delivery
→ Verified Capability Documentation

The principle is:

> Expensive implementation should begin only after sufficiently important
> Product Intent has been made concrete enough for the Human to experience,
> challenge and approve.

---

## 2. Why this exists

Conversational refinement and prototype refinement solve different problems.

### Conversational refinement

Answers:

> “Have we understood what the Human says they want?”

It refines:

- Motive;
- facts;
- constraints;
- scope;
- expectations;
- unresolved decisions.

### Experience refinement

Answers:

> “When those words become a real product experience, is this still what the
> Human actually wants?”

A Human may agree with a written requirement but reject the software once its
navigation, flow, information hierarchy, decisions and edge cases become
concrete.

Therefore prototype review is a second Product Intent calibration layer.

---

## 3. Scenario Inventory

The prototype should not primarily be measured by page count.

Its more important coverage contract is the set of Human scenarios that the
product must support.

Scenario Inventory may include:

- primary value-delivery paths;
- branches;
- exceptions;
- recovery;
- management operations;
- return/re-entry;
- Human decision points.

The intended value is:

> Feature coverage becomes explicit and reviewable rather than assumed.

Future product experience may show coverage such as:

- required scenarios;
- prototype-covered scenarios;
- Human-accepted scenarios;
- calibration-required scenarios;
- intentionally deferred scenarios.

Scenario Inventory is therefore both:

1. a prototype coverage contract;
2. a future implementation and verification traceability source.

---

## 4. Architecture Tension Register

Architecture Tension Register records unresolved differences between:

> Desired Human Experience

and

> Current Product / Architecture / Repository Reality.

A tension is not automatically a bug or a risk.

It represents a case where the desired experience and present engineering
Reality have not yet been reconciled.

Each tension should make explicit:

- desired Human experience;
- current Reality;
- mismatch;
- whether the target experience may safely be simulated in prototype;
- likely future impact:
  - UI;
  - Projection;
  - API;
  - Data;
  - Domain;
  - Architecture Decision.

The purpose is to prevent two failure modes:

### Reality captures Product Intent

“The current backend does not support this, therefore the user experience must
be designed around the current implementation.”

### Prototype ignores Reality

“This looks good in the prototype; implementation will somehow work later.”

Architecture Tension Register preserves both Product Intent and Engineering
Reality until they are consciously reconciled.

Candidate lifecycle:

Tension discovered
→ Reality investigation
→ design alternatives
→ Architecture/Human decision
→ ADR where required
→ implementation
→ verification
→ tension closed or explicitly deferred.

---

## 5. Prototype Scenario Packs

A Watt prototype should not be only a collection of pages.

It should contain replayable Human stories.

A Prototype Scenario Pack represents a meaningful journey such as:

- vague Motive → refinement → Work Formation;
- production queue → execution → interruption → recovery;
- verification failure → autonomous correction;
- result preview → Human change request → exact authorization;
- completed Work → later refinement.

The purpose is to allow the Human to review behavior and continuity rather than
individual screens in isolation.

Scenario Packs may later become reusable Experience Contracts between:

- intended prototype behavior;
- production implementation;
- Runtime verification;
- documentation.

---

## 6. Reviewer Mode

Reviewer Mode is a Human-facing experience-governance surface associated with
the prototype.

It is not merely a developer debug panel.

Candidate reviewer context may include:

- current User Story;
- Scenario / Scene identity;
- related requirement;
- related Architecture Tensions;
- acceptance focus;
- prototype revision;
- Human observations;
- calibration required;
- Human Experience Acceptance status.

Typical actions:

- select scenario pack;
- select scene;
- reset;
- replay;
- advance simulation;
- inspect traceability;
- record Human feedback;
- deep-link to an exact prototype state.

The customer-facing prototype and Reviewer Mode should remain distinguishable.

The Human should be able to experience the product normally and then inspect
why that experience exists.

---

## 7. Three core AI-software-production problems addressed

### 7.1 Controlling model hallucination

The goal is not to assume that stronger models will stop hallucinating.

Instead, Watt externalizes model interpretation into reviewable artifacts:

- understood requirements;
- scenarios;
- journey;
- tensions;
- prototype behavior;
- decisions.

Incorrect model assumptions become visible before they propagate deeply into
production code.

### 7.2 Deconstructing the AI black box

An AI-produced artifact should not remain an unexplained final object.

Desired traceability:

Requirement / Human Intent
→ Scenario
→ Prototype Scene
→ Architecture Tension / Decision
→ Human Acceptance
→ Implementation
→ Verification Evidence
→ Delivery
→ Product Capability Documentation

This lets a Human understand:

- why a feature exists;
- which need it satisfies;
- which experience was approved;
- what engineering change implemented it;
- whether it was verified;
- whether it exists in the delivered version.

### 7.3 Human as Cognitive Governor

Watt should not reduce Human-in-the-loop to:

> Human approves / rejects at the end.

Candidate principle:

> Human-in-the-loop != Human-as-approval-gate.

The higher-value role is:

> Human-as-Cognitive-Governor.

Human cognition should be used where Human judgment has the greatest leverage:

- Is this actually what I want?
- Is the experience natural?
- Is a scenario missing?
- Is this trade-off acceptable?
- Did the AI misunderstand an important distinction?
- Does the product feel coherent?
- Is the result worth authorizing?

AI should carry more of:

- coverage enumeration;
- context organization;
- implementation;
- consistency tracking;
- verification;
- regression;
- traceability.

The Human should intervene when the work is still relatively cheap and
reversible but already concrete enough for high-quality judgment.

---

## 8. Production Gate

For sufficiently large or ambiguous Work, prototype approval may become a
formal production-readiness condition.

Possible future gate:

REQUIRED_SCENARIO_COVERAGE
    SATISFIED

REQUIRED_HUMAN_EXPERIENCE_SCENES
    ACCEPTED

CRITICAL_ARCHITECTURE_TENSIONS
    RESOLVED_OR_EXPLICITLY_ADMITTED

APPROVED_HUMAN_EXPERIENCE_BASELINE
    ESTABLISHED

Only then does formal production proceed.

This must be adaptive rather than bureaucratic.

Examples:

### Small deterministic change

Lightweight confirmation
→ production

### Medium feature

User Story / Journey Slice
→ bounded prototype
→ production

### New product / large feature / high ambiguity

Human Journey
→ Scenario Inventory
→ Tension Register
→ Clickable Prototype
→ Human Experience Acceptance
→ production.

---

## 9. External prototypes and design assets

Externally supplied prototypes are Assets, not automatically Product Truth.

Examples:

- Figma;
- Axure;
- screenshots;
- PDF;
- HTML prototype;
- existing application;
- wireframes;
- design system;
- competitor references.

Possible Human intent classifications may later include:

REFERENCE

PREFERRED_DIRECTION

REQUIRED_EXPERIENCE

EXACT_VISUAL_BASELINE

Watt should combine external prototype evidence with:

- Motive;
- Work Intent;
- constraints;
- Human Journey;
- Scenario Inventory;
- architecture;
- repository Reality;
- existing code;
- other Assets;
- product decisions.

The resulting Watt prototype should therefore be a synthesis of the complete
available Product and Engineering Reality, not merely a redraw or parser output
of the uploaded prototype.

Candidate concept:

> Prototype Compilation

Multiple heterogeneous Product/Engineering facts are compiled into one
Human-runnable experience baseline.

---

## 10. Implementation traceability

Approved prototype scenes should later map into formal production.

Candidate traceability:

Scenario
→ Prototype Scene
→ Human Experience Revision
→ Implementation Work
→ Verification
→ Runtime Reality
→ Delivered Capability

Example:

Scenario J65
Prototype:
    HUMAN_EXPERIENCE_ACCEPTED

Implementation:
    IMPLEMENTED

Verification:
    PASS

Release:
    v1.x

Delivered capability:
    YES

Documentation:
    INCLUDED

The prototype is not production Truth.

Repository / Runtime Reality may reveal that an accepted prototype contains an
invalid assumption.

In that case:

Reality
→ Architecture Review
→ Prototype Calibration
→ renewed Human approval where material
→ Implementation continues.

Production must not blindly imitate an invalid prototype.

---

## 11. Delivery-time software documentation

The final software manual must NOT be generated directly from prototype intent.

Correct source chain:

Accepted Scenario
→ Formal Implementation
→ Verification
→ Runtime / Delivery Reality
→ Verified Capability Map
→ Software Manual / AI Handoff Package

The resulting documentation can serve both Humans and future AI systems.

### Human value

Explains:

- what the software can do;
- how to use each capability;
- applicable scenarios;
- branches;
- exceptions;
- recovery;
- limitations.

### AI / engineering value

Explains:

- current product capabilities;
- associated Human scenarios;
- required behavioral invariants;
- why a capability exists;
- relevant decisions and tensions;
- implementation ownership;
- verification evidence;
- delivered version.

This may become high-value input to future ECF/context assembly.

---

## 12. Candidate production package

A future formal package may combine:

- Human Journey;
- Scenario Inventory;
- Architecture Tension Register;
- Prototype Scenario Packs;
- Reviewer feedback;
- Human Experience Acceptance;
- Approved Experience Baseline;
- Implementation Traceability.

Working names only:

- Experience Construction Package;
- Production Readiness Package;
- Product Experience Baseline Package.

No name is frozen.

---

## 13. Differentiation hypothesis

The intended differentiation is NOT:

> “Watt can also generate a prototype.”

The stronger hypothesis is:

> Before expensive software production begins, Watt compiles Product Intent,
> engineering facts and scenario coverage into a complete Human-reviewable
> experience; the Human confirms that experience, and every accepted scenario
> remains traceable through implementation, verification and final delivery.

Possible Human-facing expression:

> 先把软件给你“看懂”，再把软件真正造出来。

This capability may reduce:

- Product Intent drift;
- missing features;
- expensive implementation rework;
- AI-generated black-box behavior;
- unnecessary token/compute consumption;
- Human uncertainty about what the AI is building.

---

## 14. Current status

This pattern was discovered during Watt's own UX reconstruction dogfood.

Evidence currently available:

- Human Journey planning;
- Scenario Inventory;
- Architecture Tension Register;
- Prototype Scenario Packs;
- Reviewer Mode;
- first clickable Watt experience prototype.

The current dogfood has not yet proven the complete economic or quality value of
the pattern.

Before promotion to a frozen Watt production capability, evaluate:

- whether scenario coverage materially reduces omissions;
- whether prototype review reveals intent errors before implementation;
- whether Architecture Tension tracking prevents UX/Reality drift;
- whether Human Experience Acceptance reduces production rework;
- whether formal implementation can faithfully follow the accepted prototype;
- whether total Token / compute / wall-clock / Human cost decreases;
- whether delivered documentation can be reliably generated from verified
  capability traceability.

Until then:

CANDIDATE
DOGFOOD_PENDING

Related candidate: [Adaptive Work Patterns](watt-adaptive-work-patterns-candidate.md)
may later guide whether this process is needed for a particular Work and how
deeply it should be applied. That relationship remains unimplemented and is not
yet an architecture decision.
