# Watt AI Software Production Evaluation Framework

Date: 2026-09-21

Status: **ARCHITECTURE BASELINE / EVALUATION PLATFORM PENDING**. This document
defines the evaluation dimensions, evidence boundaries, corpus strategy, and
improvement loop for Watt as an AI-native software production system. It does
not implement a benchmark platform, leaderboard, public ranking, or automated
evaluation infrastructure.

## 1. Purpose

Watt needs both the ability to produce software and a durable way to evaluate
and improve that ability.

Traditional software delivery evaluation commonly asks whether the software
compiled, tests passed, and an artifact was delivered. Those checks remain
necessary, but an AI-native software production system must also evaluate:

- whether it understood the Human's intent;
- whether it completed the production task well; and
- whether it can demonstrate that the result is trustworthy.

This document establishes the **AI Software Production Evaluation Framework**
for those three concerns. Evaluation is a cross-cutting capability: it observes
the production chain and turns attributable outcomes into improvement input. It
does not become a new owner of Work Reality, Semantic Truth, production
authority, or Human Acceptance.

## 2. Core principle

Watt must not optimize its software production capability against one score.
The capability being evaluated is the balanced system outcome:

```text
Understand well
      +
Produce well
      +
Assure well
```

The framework therefore has three dimensions:

```text
AI Software Production Evaluation Framework
        |
        +-- Interaction Intelligence Evaluation
        |
        +-- Production Capability Evaluation
        |
        +-- Assurance Capability Evaluation
```

No dimension can substitute for another. Correct code produced from the wrong
meaning is not success. A convincing explanation without a valid product is not
success. A working artifact without sufficient evidence remains an assurance
risk.

## 3. Evaluation boundary and authority

The framework evaluates governed Reality; it does not create that Reality.

It may consume versioned references to:

- Human Intent and Human corrections;
- Response Contract and Interaction outcomes;
- Engineering Semantic Truth and Work Reality;
- ECF projections and repository/runtime observations;
- SOP and Task Contract lineage;
- Executor results;
- Guardian findings and Assurance Evidence; and
- Human Acceptance outcomes.

Evaluation results are measurements, classifications, and improvement signals.
They are not permission to admit Work, change current Semantic Truth, execute a
side effect, waive a gate, authorize a Candidate, or declare Human Acceptance.

Every material evaluation result should identify:

- the exact subject and version evaluated;
- the scenario or corpus item;
- the source evidence and its provenance;
- the evaluation method and framework version;
- unavailable or ambiguous evidence; and
- the Human or system authority behind any judgment.

Historical evaluation results remain historical when the underlying Work,
artifact, or framework changes. They must not be silently rewritten to match a
new version.

## 4. Interaction Intelligence Evaluation

### Purpose

Evaluate whether Watt genuinely understands the Human and collaborates
effectively. This dimension corresponds primarily to WIC and the Response
Contract.

### Evaluation scope

#### Intent understanding

Evaluate whether Watt:

- identifies the actual goal and relevant constraints;
- binds ambiguous language to governed meaning before downstream use;
- distinguishes an interpretation from a Human-explicit fact; and
- avoids confident misunderstanding.

#### Collaboration behavior

Evaluate whether Watt:

- matches the current Interaction Mode;
- leaves appropriate space during exploration;
- converges efficiently during execution;
- asks only questions that materially affect the outcome; and
- advances when sufficient information and authority exist.

#### Judgment consistency

Evaluate whether Watt:

- maintains evidence-based judgment rather than unsupported agreement;
- states uncertainty truthfully;
- updates its conclusion when new governed facts appear; and
- does not present superseded meaning as current.

#### Multi-turn stability

Evaluate whether Watt:

- preserves the active objective across a long conversation;
- avoids semantic drift;
- retains relevant decisions and corrections; and
- restores the correct collaboration state after refresh, retry, or recovery.

### Data sources

Candidate sources include:

- a versioned WIC Golden Interaction Corpus;
- Watt Dogfood cases;
- expert-designed interaction scenarios; and
- attributable Human review outcomes.

The corpus is an evaluation input, not an authority source. Its cases must state
the expected invariant, relevant context, permissible variation, and review
authority. This document defines that corpus strategy but does not implement
the corpus platform.

## 5. Production Capability Evaluation

### Purpose

Evaluate whether Watt can complete software production tasks with high quality.
This dimension corresponds primarily to Domain Grounding, Software Production
SOP, Task Contract, PWU, and Executor behavior.

### Evaluation scope

#### Task understanding

Evaluate whether Watt understands:

- the production objective;
- scope and boundaries;
- acceptance criteria;
- required evidence; and
- applicable authority constraints.

#### Repository understanding

Evaluate whether Watt can:

- understand the existing code and architecture;
- locate the correct change surface;
- preserve unrelated Human-owned work; and
- follow repository-specific conventions and constraints.

#### Implementation capability

Evaluate:

- functional correctness;
- code quality and maintainability;
- architectural consistency;
- change-scope discipline; and
- execution efficiency appropriate to the task.

#### Verification capability

Evaluate whether Watt:

- derives verification from the accepted requirement and contract;
- runs the cheapest sufficient checks before broader qualification;
- classifies failures before changing implementation or expectations;
- repairs genuine defects without hiding them; and
- identifies important omissions and residual risk.

#### Regression resistance

Evaluate whether a new capability preserves existing accepted invariants. Use
the adopted regression-governance model: protect invariants at the lowest-cost
reliable layer and consolidate cross-layer behavior into Golden Journeys rather
than adding one end-to-end test for every historical bug.

See [Watt Regression Protection and Golden Journey
Governance](watt-regression-protection-and-golden-journey-governance.md).

### Data sources

Candidate sources include:

- public software-engineering tasks such as SWE-bench-style cases;
- agent-system benchmark patterns associated with systems such as SWE-agent or
  OpenHands;
- Watt's own governed production cases;
- repository and runtime evidence; and
- existing Production Benchmarks and Production Measurement projections.

Public benchmarks are comparison inputs, not complete definitions of Watt's
capability. They must be mapped to Watt's authority, Reality, execution, and
Assurance invariants before their results are interpreted.

See [Production Benchmarks](production-benchmarks.md) and [Production
Measurement v0](production-measurement-v0.md).

## 6. Assurance Capability Evaluation

### Purpose

Evaluate whether Watt can demonstrate that its production result is
trustworthy. This dimension corresponds primarily to Guardian and the Evidence
Architecture.

### Evaluation scope

#### Requirement compliance

Evaluate whether the result satisfies the current:

- Human Intent;
- Engineering Semantic Truth;
- Task Contract; and
- applicable acceptance and authority boundaries.

#### Evidence quality

Evaluate whether claims are supported by attributable:

- Human Evidence;
- Engineering Evidence;
- Runtime Evidence; and
- Assurance Evidence.

Evidence quality includes identity, provenance, freshness, scope, integrity,
and relevance. Evidence volume alone is not quality.

#### Risk detection

Evaluate whether Guardian and the production system can identify:

- potential defects;
- architecture and boundary violations;
- regression risk;
- missing or stale evidence; and
- uncertainty that prevents a trustworthy conclusion.

#### Assurance effectiveness

Evaluate whether Assurance:

- finds material problems before delivery or authorization;
- reduces the Human's verification burden without taking Human authority;
- avoids false confidence and ceremonial gates; and
- increases the trustworthiness of delivery decisions.

See [Watt Decision and Evidence
Architecture](watt-decision-evidence-architecture.md) and [Guardian
Integration](../assurance/guardian-integration.md).

## 7. Evaluation feedback loop

Evaluation is an improvement entry point, not a terminal score:

```text
Production Reality
        ↓
Evaluation
        ↓
Failure Classification
        ↓
Architecture / Pattern / SOP Improvement
        ↓
New Version
        ↓
Re-evaluation
```

The initial routing model is:

| Failure class | Primary improvement destination | Example concern |
|---|---|---|
| Interaction failure | Response Contract / WIC | Intent misunderstanding, collaboration mismatch, semantic drift |
| Production failure | Domain Grounding / SOP / Task Contract / Executor | Wrong change surface, incomplete implementation, invalid execution |
| Assurance failure | Guardian / Evidence Architecture | Missing proof, undetected risk, unjustified confidence |

Routing identifies the most likely improvement owner; it does not pre-judge the
root cause. Cross-layer failures may require evidence from several owners before
classification.

Evaluation failures should be converted into one of the following only when the
evidence warrants it:

- a corrected architecture invariant;
- a reusable Domain Pattern;
- an SOP or Task Contract refinement;
- a lowest-cost regression assertion;
- a consolidated Golden Journey; or
- a documented future capability.

## 8. Relationship with Watt architecture

The framework evaluates the core production chain:

```text
Human Intent
      ↓
Response Contract
      ↓
Context Intelligence
      ↓
Domain Grounding
      ↓
Software Production SOP
      ↓
Task Contract
      ↓
Executor
      ↓
Guardian
      ↓
Evidence
```

It is cross-cutting rather than a new stage inserted into that chain. Evaluation
may examine intermediate and end-to-end outcomes without becoming the owner of
those outcomes.

## 9. Current scope

The current architecture scope establishes:

- the framework definition;
- the three evaluation dimensions;
- authority and evidence boundaries;
- failure-classification and feedback routing; and
- the corpus strategy.

The current scope does **not** implement:

- a Benchmark Platform;
- a leaderboard or public ranking;
- automated evaluation infrastructure;
- a new Evaluation service, database, or UI;
- autonomous architecture, Pattern, or SOP mutation; or
- replacement of Full Regression, Guardian, or Human Acceptance.

## 10. Future evolution

### Internal quality system

The first intended use is Watt's own quality system, to:

- detect capability degradation;
- prevent major regressions;
- compare version-to-version improvement; and
- expose recurring failure patterns for governed improvement.

### External evaluation framework

A later exploration may determine whether the framework can contribute to a
broader evaluation system for AI-native software production. That direction is
not a current product or milestone objective.

## 11. Design principles

### No single-metric optimization

Coding score or task success rate alone cannot represent AI-native software
production quality. Aggregate reporting must keep the three dimensions visible
and must not conceal a material failure behind a composite score.

### Reality-based evaluation

Evaluation should derive from actual tasks, governed production, runtime
behavior, attributable evidence, and real Human experience. Synthetic cases are
useful when they isolate an invariant, but must not replace Reality evidence.

### Capability balance

High-quality AI software production requires Watt to understand well, produce
well, and assure well. Improvement in one dimension must not silently weaken
another.

### Versioned and reproducible judgment

The evaluated system version, scenario, configuration, evidence basis, and
evaluation method must be reproducible. Local overrides and unavailable inputs
must be explicit.

### No benchmark gaming

Evaluation must reward durable capability and governed outcomes rather than
case-specific prompts, fixture loopholes, or assertions weakened to match an
implementation.

## 12. Roadmap placement

```text
Core Architecture
  Response Contract
  Semantic Truth
  ECF
  Domain Grounding
  Software Production SOP
  Task Contract
  Guardian

Cross-cutting Capability
  AI Software Production Evaluation Framework

Future
  Pattern Evolution
  Pattern Studio
  Evaluation Platform
```

The framework is an architecture baseline now. An Evaluation Platform remains
future work and requires separate objective, authority, data, privacy,
operational, and implementation design.
