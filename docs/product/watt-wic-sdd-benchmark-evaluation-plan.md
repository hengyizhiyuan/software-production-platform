# Watt WIC / SDD Benchmark & Evaluation Plan
## Intent Refinement, Work Formation & Workflow Effectiveness

Date: 2026-09-14

~~~text
STATUS
    CANDIDATE

BENCHMARK_IMPLEMENTATION
    NOT_STARTED

EXTERNAL_BENCHMARK_STUDY
    COMPLETE

WIC_LAB_INTEGRATION
    FUTURE

ARCHITECTURE_DECISION
    NOT_FROZEN

REVISIT_POINT
    AFTER_CLICKABLE_PROTOTYPE_REVIEW
    AND DURING WIC/SDD ARCHITECTURE STUDY
~~~

This is a future evaluation plan, not current architecture truth. It authorizes
no benchmark implementation, WIC Lab, Provider experiment, production WIC or
Work Formation change, prototype change, or external repository clone.

Related candidate records:

- [WIC / SDD Architecture Study Plan](watt-wic-sdd-architecture-study-plan.md)
- [Adaptive Work Patterns](watt-adaptive-work-patterns-candidate.md)
- [Experience-before-Production](experience-before-production-candidate.md)

Completed study input:

- [WIC / SDD Benchmark Landscape](../research/wic-sdd-benchmark-landscape.md)
- [External Source Evidence Ledger](../research/wic-sdd-source-evidence.md)

Benchmark design and implementation remain pending. The completed external
study does not activate WIC Lab or freeze an evaluation architecture.

## 1. Why benchmarking is needed

Watt is considering Adaptive Work Patterns, structured refinement,
requirements/conflict analysis, Work Formation improvements, context strategy,
experience triggers, WIC Policy and WIC Lab. These may sound attractive while
adding model Turns, artifacts, Human friction, latency, token cost, duplicate
Truth, maintenance and workflow bureaucracy.

Watt must not adopt a mechanism merely because another product uses it, it is
called SDD, it looks rigorous, it generates more documentation or it appears
architecturally elegant.

> Every layer must earn its keep.

The benchmark exists to ask whether added structure creates enough real
production value to justify its total cost.

## 2. External benchmark landscape

The future architecture study should investigate:

### A. Specification reasoning

Can AI identify ambiguity, missing requirements, contradictions, unstated
assumptions, invalid architecture assumptions and missing edge cases before
implementation?

### B. Specification adherence

Does implementation satisfy intent rather than only visible tests or a narrow
interpretation? Study visible tests, hidden tests, held-out behavior and
specification compliance.

### C. Software implementation capability

SWE-bench-style systems are useful downstream references for the question:
given a sufficiently formed problem, can the agent implement it? They do not
fully test whether Human intent was correctly understood and refined.

### D. Workflow effectiveness

Compare complete strategies such as OPEN_WIC, PATTERN_GUIDED_WIC, SDD_LIGHT,
SDD_HEAVY and EXPERIENCE_FIRST. The central question is whether structure
improves the whole production outcome enough to justify process cost.

## 3. Primary unit: Intent-to-Work Episode

The primary unit is not one Prompt. A candidate episode contains:

~~~text
initial Human Motive
-> Human additions and corrections
-> WIC questions or recommendations
-> convergence
-> Work Formation
-> optional artifacts
-> readiness decision
~~~

It supports evaluation of problem understanding, useful questioning,
convergence, invented requirements, missed constraints and Work-boundary
correctness.

## 4. Governing evaluation principle

> Watt should optimize for the minimum sufficient structure required to achieve
> reliable intent understanding and trustworthy production, not maximum
> specification completeness.

Quality gains must always be evaluated against total production cost.

## 5. Benchmark corpus

The future corpus should combine:

### A. Real Watt dogfood

Highest-value cases come from development history: vague new-product Motive,
active Work correction, explicit constraint, new Motive versus active Work,
UX redesign, performance optimization, environment defects and repository
Reality contradicting Human assumptions. Preserve useful historical failures.

### B. Pattern-oriented cases

Candidate families include NEW_PRODUCT, PRODUCT_FEATURE, BUG_FIX, REFACTOR,
PERFORMANCE_OPTIMIZATION, MIGRATION, EXTERNAL_INTEGRATION, UX_REDESIGN,
TECHNICAL_SPIKE and INCIDENT_RECOVERY. This taxonomy is not frozen.

### C. Adversarial cases

Include ambiguous first messages, later Human contradiction, unrelated side
questions, two plausible Patterns, repository conflicts, simple requests that
must not trigger heavy SDD, internally contradictory specifications and stale
previous understanding.

### D. Brownfield cases

Test systems where code and prior design already exist, documentation differs
from implementation, and Work evolves rather than creates software.

## 6. Human-adjudicated Reference Intent Package

Intent rarely has one exact textual answer. Exact model-output matching must not
be Ground Truth.

Each case should have a versioned Reference Intent Package containing:

- true Motive;
- required facts and constraints;
- important scenarios;
- forbidden or invented assumptions;
- correct Work boundary;
- important ambiguity;
- facts that must remain unchanged;
- known later corrections;
- reasonable Pattern candidates where relevant.

Evaluation judges semantic fidelity, not identical wording.

## 7. Versioned benchmark Reality

Each case must identify:

- case revision;
- Reference Intent revision;
- evaluation-rubric revision;
- repository and Runtime fixture revision.

A Benchmark v3 result must not be silently compared with materially different
Benchmark v4. Normalize or rerun explicitly. Benchmark evolution is engineering
Reality.

## 8. Paired and controlled evaluation

Prefer paired comparison over isolated absolute scores. For the same case, hold
constant where practical:

- Human input and response script;
- model, version, Provider and reasoning effort;
- context and repository fixture;
- Runtime revision;
- temperature/sampling configuration where applicable.

Change primarily the WIC/refinement strategy:

~~~text
Case X
    A = OPEN_BASELINE
    B = PATTERN_GUIDED
    C = SDD_LIGHT
~~~

This improves attribution without pretending that model output is deterministic.

## 9. Benchmark tracks

### WIC-Bench A: Intent Understanding & Refinement

Measures Motive fidelity, facts, constraints, corrections, Work boundary,
invented requirements, scope drift and new-Motive separation.

### WIC-Bench B: Work Pattern & Readiness

Measures problem-type recognition, question focus, early/late readiness,
rerouting, unnecessary refinement and correct Work Formation.

### WIC-Bench C: Specification / Experience Quality

Evaluates requirements, scenarios, Human Journey, prototype scope,
architecture tensions and acceptance criteria where useful. The question is
whether artifacts expose uncertainty and improve decisions, not their length.

### WIC-Bench D: End-to-End Production Effectiveness

Selected cases continue through refinement, Work Formation, implementation,
verification and delivery. This is the most valuable and most expensive track.

## 10. Intent Fidelity gate

Intent Fidelity is a high-priority quality gate. Observe whether Motive, facts,
constraints, corrections, scope and Work relationships are preserved without
invented material requirements.

Critical errors include:

- CRITICAL_INTENT_LOSS;
- INVENTED_REQUIREMENT;
- MATERIAL_CONSTRAINT_LOSS;
- WRONG_WORK_BOUNDARY;
- STALE_CORRECTION_RETAINED.

Lower cost or fewer dialogue Turns cannot compensate for a critical intent
error.

## 11. Refinement Efficiency

Candidate measures include dialogue and Human Turns, Watt questions,
relevant/unnecessary question ratio, repetition, Human corrections, time to
readiness and Work Formation, model calls, input/output tokens, first meaningful
response latency and total latency.

The goal is sufficient understanding with minimum unnecessary interaction, not
minimum Turns at all costs.

## 12. Structure ROI

Track artifacts, generation cost, Human review cost, updates, and whether each
artifact affected a decision, implementation, verification, risk discovery or
rework prevention.

Candidate concept:

~~~text
Useful Structure Ratio
    useful structure that changed or protected production
    ------------------------------------------------------
    total structure and process cost
~~~

No numeric formula is frozen. More specification is not automatically better.

## 13. Over-structuring penalty

Explicitly detect full product requirements for trivial bugs, redundant
artifacts, unnecessary approvals or model Turns, repeated known facts,
refinement after readiness, unused specifications and unnecessary prototypes.

> Minimum Sufficient Structure.

A strategy loses value when it solves a simple problem with unjustifiably heavy
process.

## 14. Downstream production outcome

For selected cases measure implementation rework, discarded implementation,
changed-file churn, failed verification, reopened scope, Human intervention,
architecture correction, token usage, wall-clock time, Provider cost and total
production cost.

Trusted Delivery Cost is a future economic metric candidate. Ask whether small
upstream refinement cost prevented much larger downstream rework.

## 15. Multi-level benchmark cost model

Do not run end-to-end implementation for every case:

- **Level 1 - large/cheap:** Intent, refinement and Work Formation.
- **Level 2 - medium:** representative artifacts, Pattern, readiness and
  scenario/spec quality.
- **Level 3 - expensive:** selected cases proceed through implementation.
- **Level 4 - highest-cost:** a small strategic set reaches Verification,
  Delivery, Runtime and Human review.

The benchmark must not become its own production-cost problem.

## 16. Human Perceived Intelligence

Human experience is first-class evidence. Prefer blind pairwise review where
practical: show Conversation A and B without Policy/Pattern identity, then ask
which understood faster, asked higher-value questions, felt more professional,
felt procedural or annoying, was preferable to continue with, and preserved
intent more accurately.

Avoid artificial precision such as an 8.37 intelligence score unless later
evidence establishes a calibrated scale.

## 17. Human Cognitive Cost

Observe decisions requested, approvals, reading burden, repeated explanation,
clarification burden and artifact-review time. Watt must not lower AI token cost
by dramatically increasing Human cognitive cost.

## 18. Hidden and holdout evaluation

Distinguish development/calibration cases, visible benchmark cases and hidden
holdout cases where practical. Policy candidates must generalize; hidden cases
must not become routine Prompt-tuning inputs.

## 19. Contamination and leakage

When real interactions become benchmark cases, freeze historical input,
sanitize sensitive data, record provenance and avoid feeding benchmark answers
back into normal instructions in ways that invalidate comparison. The corpus is
for evaluation, not a giant hidden Prompt library.

## 20. Model variance

Distinguish workflow improvement from model improvement. Compare WIC strategies
with the same Provider/model/profile where possible. If model interaction is
the variable, label it separately. Do not credit Pattern guidance for gains
caused by a stronger model.

## 21. Replay and reproducibility

Future evidence should preserve frozen input, Work/repository fixture, Policy
revision, model/profile identity, timing, structured outputs, usage/cost and
results. When model nondeterminism prevents exact replay, preserve enough
evidence for comparable repeated trials.

## 22. Statistical treatment

Do not over-engineer statistics in the first version, but do not conclude from
one lucky run. For noisy metrics, use repeated runs or enough cases to inspect
central tendency, variance and outliers. Tiny local samples do not establish
production SLAs or universal conclusions.

## 23. Relationship to WIC Lab

Future WIC Lab should become the primary benchmark execution environment where
practical:

~~~text
Benchmark Case
    -> Replay / Interactive Lab
    -> WIC Policy A / B / C
    -> metrics and semantic outcomes
    -> Human / automated evaluation
~~~

Candidate Lab support includes replay, side-by-side and blind Human review,
batch corpus execution, semantic diff, cost/latency comparison and mechanism
ablation. None is implemented here.

## 24. Relationship to WIC Policy

Each result should ideally be attributable to an immutable Policy revision,
model profile, Benchmark revision and Case revision. This supports comparison,
regression, rollback and long-term optimization without freezing a storage
schema now.

## 25. Release-gate strategy

Benchmarking must not become heavy ceremony for every small WIC change:

- **Low-risk strategy/content change:** focused semantic regression and a small
  case subset.
- **Medium WIC Policy change:** WIC-Bench A/B and selected C cases.
- **Major Pattern/routing/SDD change:** broad A/B/C and selected D end-to-end
  cases.

Do not mechanically rerun the most expensive track for every edit.

## 26. External benchmark study questions

The external WIC/SDD study should determine:

- which specification reasoning/adherence, SWE-bench-family and SDD framework
  evaluations exist;
- what each measures and explicitly does not measure;
- how Ground Truth is formed and whether the specification is assumed correct;
- whether hidden tests, ambiguity and Human judgment are represented;
- whether workflow and artifact costs, over-specification and downstream rework
  are measured;
- whether model/Provider variables are controlled;
- whether results are reproducible and versioned;
- which mechanisms Watt can reuse and which gaps need Watt-specific evaluation.

Initial families are not exhaustive and must be studied from evidence.

## 27. Required external evaluation map

| Benchmark | Measures | Unit | Ground Truth | Strength | Blind spot | Watt relevance |
|---|---|---|---|---|---|---|
| Candidate A | Spec reasoning | TBD | TBD | TBD | TBD | TBD |
| Candidate B | Spec adherence | TBD | TBD | TBD | TBD | TBD |
| Candidate C | Implementation | TBD | TBD | TBD | TBD | TBD |

The map identifies coverage and blind spots; it does not rank popularity.

## 28. Required Watt benchmark design output

After the external study, produce a reviewed Watt-specific design covering:

- benchmark corpus and Reference Intent Packages;
- Tracks A-D and paired evaluation;
- automatic metrics and Human review;
- versioning, holdout cases and cost tiers;
- WIC Lab integration and Policy attribution;
- release-gate strategy.

Do not implement that design before review.

## 29. Benchmark success criterion

The benchmark succeeds only if it helps answer whether Pattern guidance improves
focus, Requirements Analysis reduces material ambiguity, artifacts prevent
rework, structure lowers Trusted Delivery Cost, Watt asks fewer but better
questions, Humans feel understood, and correctness improves without
bureaucracy.

Producing one aggregate score is not success.

## 30. Watt philosophy boundary

~~~text
Human defines intent.
AI amplifies capability.
System ensures trust.
~~~

Benchmarking should improve Watt's fidelity to Human Intent, not convert Human
collaboration into benchmark optimization.

## 31. Future implementation philosophy

The first benchmark implementation need not be perfect:

~~~text
bounded first version
-> real Watt dogfood
-> Human outcome review
-> simplify, strengthen or reject mechanisms
-> evolve
~~~

The Human Governor contributes outcome judgment, identifies when the system
does not feel right, provides sufficient experiment/production budget and makes
major Product Intent decisions. Architecture and implementation remain the
responsibility of the Architecture Lead AI and repo-grounded Executor within
approved boundaries.

## 32. Explicit non-decisions

This plan does not freeze:

- benchmark case count, scoring formula or weights;
- Pattern taxonomy;
- Human scoring UI or statistical method;
- persistence schema or WIC Lab UI;
- release thresholds;
- repeated-trial count or holdout ratio;
- whether an aggregate score exists.

These decisions require external study and first dogfood.

## 33. Program timing

~~~text
clickable-prototype review
    -> collect WIC / UX findings
    -> external WIC / SDD architecture study
    -> Benchmark & Evaluation Landscape
    -> Architecture Lead synthesis
    -> WIC / Adaptive Work Pattern architecture
    -> WIC Lab + Policy + Benchmark design
    -> bounded implementation
    -> dogfood and comparison
    -> Human feedback
    -> production activation
~~~

Benchmark implementation must not start early.

## 34. Current status and revisit point

~~~text
STATUS
    CANDIDATE

BENCHMARK_IMPLEMENTATION
    NOT_STARTED

EXTERNAL_BENCHMARK_STUDY
    PLANNED

WIC_LAB_INTEGRATION
    FUTURE

ARCHITECTURE_DECISION
    NOT_FROZEN

REVISIT_POINT
    AFTER_CLICKABLE_PROTOTYPE_REVIEW
    AND DURING WIC/SDD ARCHITECTURE STUDY
~~~

No benchmark, WIC Lab, Provider experiment or external benchmark study has
started.
