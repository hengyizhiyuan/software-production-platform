# Watt WIC / SDD Architecture Study Plan
## Spec-driven Development, Intent Externalization & Adaptive Refinement

Date: 2026-09-14

~~~text
STUDY_STATUS
    PLANNED

EXECUTION
    NOT_STARTED

IMPLEMENTATION_AUTHORITY
    NONE

REVISIT_POINT
    AFTER_CLICKABLE_PROTOTYPE_REVIEW

ARCHITECTURE_DECISION
    NOT_FROZEN
~~~

This is a future architecture research plan, not current Watt architecture
truth. It authorizes no external repository study, cloning, implementation or
change to WIC, Work Formation, Guided Design, Steering or the clickable
prototype.

## 1. Why this study exists

Watt intentionally avoids this failure mode:

~~~text
Human says one sentence
-> AI assumes understanding
-> immediately creates Work or starts coding
~~~

Current principles remain valid:

- open conversational refinement;
- first utterance is not Work creation;
- Conversation is not Truth;
- explicit Work Admission;
- correction and clarification;
- active Work focus preservation;
- Human Authority.

Human dogfood exposed the opposite failure mode:

~~~text
too much openness
-> conversation keeps expanding
-> AI repeatedly rediscovers what matters
-> weak convergence and unclear readiness
-> Human perceives the system as less intelligent
~~~

The study asks how Watt can preserve natural Human expression while giving AI
enough professional structure to converge efficiently and reliably.

## 2. External signal: Spec-driven Development

Industry approaches including Kiro Specs, GitHub Spec Kit, OpenSpec, Tessl and
similar systems are increasingly discussed under Spec-driven Development
(SDD). The relevant idea is not merely writing requirements.md before coding.
The stronger idea is:

> Transient Human intent should become stable, inspectable, versionable and
> production-relevant artifacts before or during implementation.

This aligns with Watt's concern that AI production cannot depend entirely on
ephemeral Prompt or Conversation state. Watt must not assume that any existing
SDD implementation is the correct product form.

## 3. Human Governor position

The Human Governor broadly supports the SDD goal of making Human intent stable
and controllable enough to govern AI production. Watt independently reached
similar concerns through Motive, Work, versioned Work Reality, Conversation !=
Truth, Steering, governed production, Evidence and Human Authority.

The study is therefore not asking whether Watt should become SDD. It asks:

> Which SDD mechanisms solve problems Watt also has, and how should they be
> reinterpreted within Watt's own AI-native product paradigm?

## 4. Critical view

Many SDD products retain traditional assumptions: explicit Requirements,
Design and Tasks phases; repeated Human approval gates; file/document-centric
flows; and developer-visible workflow selection.

SDD and freer AI interaction need not be opposing philosophies:

- free interaction contributes flexibility, low friction and rapid iteration;
- SDD contributes stable intent, traceability and production control.

The candidate opportunity is to combine both: Human expression stays natural
and flexible while Watt progressively structures intent internally where
structure earns its cost. This is not yet a frozen architecture decision.

## 5. Key architecture question

> What is the minimum sufficient structure that makes AI software production
> focused, stable and traceable without recreating traditional
> software-process bureaucracy?

This question is more important than deciding whether Watt uses SDD.

## 6. Central study hypothesis

The study will challenge, not assume, this candidate principle:

> Pattern constrains the AI's search space, not the Human's expression space.

~~~text
Human natural expression
    -> Open WIC understanding
    -> Motive / current Reality
    -> Work Pattern Recognition
    -> Pattern-guided focused refinement
    -> Intent / Experience / Engineering artifacts
    -> Work Formation
    -> Governed Production
~~~

The Human should experience Watt as understanding the nature of the problem,
not as asking them to choose Workflow Template #4.

## 7. Why source-grounded study is needed

External projects may already contain useful mechanisms for:

- intent representation and specification lifecycle;
- structured refinement and ambiguity detection;
- versioning, change propagation and traceability;
- workflow or pattern routing;
- brownfield repository analysis;
- requirement-to-test linkage;
- spec-to-implementation handoff and reverse feedback;
- agent context assembly;
- iterative correction and Human review.

Watt should learn from these mechanisms without adopting their top-level
product metaphors by default.

## 8. Candidate study targets

The list is provisional. The Human Governor will approve the final repository
set before execution.

Primary source-available candidates:

- GitHub Spec Kit;
- OpenSpec.

Secondary comparative candidates:

- representative Kiro-inspired open-source implementations;
- other mature source-available intent/spec-driven agent systems found during
  study preparation.

Documentation or observable-behavior references:

- Kiro official documentation, published workflows and public behavior;
- Tessl public documentation or source where licensing and access permit.

Closed-product findings must be labeled documentation/behavior-based rather
than source-proven.

## 9. Study method

The study must be source-grounded, mechanism-oriented, evidence-linked and
Watt-question-driven. It must not become a generic competitor summary.

For source-available projects:

1. clone only after explicit authorization into an isolated study area;
2. inspect architecture documentation and actual source;
3. identify concrete implementation mechanisms;
4. record source evidence and observed invariants;
5. separate marketing terms from implementation Reality.

For closed products, use official documentation and observable public behavior,
and label the evidence boundary clearly.

## 10. Core research questions

### A. Intent representation

- How is Human intent represented after conversation: Markdown, schema, typed
  domain objects, graph, files, database facts or agent state?
- What becomes authoritative?

### B. Specification ownership and Truth

- Who owns the authoritative specification?
- What happens when Conversation, specification, repository, implementation,
  tests and Runtime disagree?
- Does the system create duplicate Truth?

### C. Evolution and drift

- How is intent updated after Human correction, invalid implementation
  assumptions, repository change, verification contradiction or production
  discovery?
- Can stale specification remain active accidentally?

### D. Readiness

- How does the system decide that enough is known to proceed?
- Is readiness a fixed checklist, model judgment, deterministic validation,
  Human approval or a combination?

### E. Ambiguity and conflict analysis

- How are ambiguity, conflicting requirements, missing edge cases, unstated
  assumptions and incompatible constraints found and resolved?
- Does the Human receive high-value questions or a questionnaire?

### F. Work-type specialization

- Are Feature, Bug Fix, Refactor, Migration, Performance and UX handled
  differently?
- Does the system use one universal workflow or multiple work patterns?

### G. Pattern selection

- Does the Human, model, classifier or deterministic policy select a Pattern?
- Can Patterns combine or change when later Reality contradicts the first
  classification?

### H. Brownfield Reality

- Does the system trust the specification, reconstruct understanding from code,
  reconcile code/spec, or retain historical intent?

### I. Specification-to-implementation lineage

- Can the system identify which implementation satisfies each requirement,
  scenario or decision?
- How is that lineage represented and preserved?

### J. Implementation feedback

- Is the flow one-way from specification to code, or bidirectional?
- How does implementation discovery refine intent without uncontrolled drift?

### K. Specification-to-verification

- How are intent artifacts converted into tests, properties, acceptance
  criteria, verification obligations and Runtime checks?
- Is this relationship explicit and traceable?

### L. Human role

- Where does Human cognition add material value?
- Where are Humans used as repetitive approval ceremony rather than high-value
  decision makers?

### M. Context assembly

- What is always loaded, task-scoped, phase-scoped or semantically selected?
- How do systems avoid full-history and specification bloat?

### N. Cost and complexity

- What ongoing cost comes from extra model Turns, regeneration, duplicate
  documents, maintenance, synchronization and review?
- What mechanisms reduce that cost?

## 11. WIC / Spec System Experimentability

WIC is expected to be a long-lived optimization surface. Where safe, its
interaction intelligence should eventually be testable and evolvable without
requiring an ordinary full main-application release for every strategy change.

An engineering UI with independent checkboxes such as Pattern Recognition,
Requirements Analysis or Extra Conflict Analysis is only one candidate
experiment interaction. Checkbox-based, single-variable ablation is not frozen
as Watt's design. The study must first examine mature mechanisms including
capability toggles, strategy profiles, configuration bundles, instruction
versions, experiment variants, replay, shadow evaluation, canary activation,
dynamic configuration, rollback and policy/version management.

For every relevant external system, investigate:

### A. Behavioral-layer configuration

- Can requirement analysis, Pattern routing, planning, context selection,
  structured output, validation, readiness, artifact generation and prompt
  strategies vary independently?
- Are they hard-coded, configuration-driven, plugin-driven, policy-driven or
  dynamically selectable?

### B. Formal experiment abstraction

- Does the system expose experiment, variant, profile, mode, strategy, policy,
  preset, pipeline, recipe or feature-flag concepts?
- Are experiments first-class or improvised through configuration?

### C. Same-input comparison

Can the same input, repository and context be evaluated through Strategy A, B
and C? Look for deterministic replay, recorded conversations, fixtures,
benchmark corpora, scenario replay, golden cases and evaluation suites.

### D. Ablation

Can a mechanism be removed or replaced to measure marginal contribution, for
example baseline versus spec analysis, Pattern routing or context optimization?
Study dependencies and interaction effects; do not assume single-variable
testing is sufficient.

### E. Strategy bundles

Investigate coherent profiles such as OPEN_BASELINE, PATTERN_LIGHT, SPEC_LIGHT
or HIGH_STRUCTURE. Compare individual flags, bundles/presets, composable
policies, pipeline definitions and hierarchical configuration.

### F. Online and offline evaluation

Inspect offline replay, interactive sandbox testing, shadow execution,
production A/B, canary and gradual rollout. Identify which mechanisms are safe
for intent/refinement systems and which risk inconsistent Human experience.

### G. Metrics

Relevant measures may include refinement turns, time to readiness, Human
corrections, relevant/unnecessary question ratios, Work Formation completeness,
intent drift, Pattern errors/rerouting, token cost, latency, artifact count,
implementation rework, Human acceptance and perceived intelligence. External
metrics are evidence, not automatically sufficient for Watt.

The external study must also identify what is hard-coded and difficult to
optimize, how variants/prompts/policies are versioned, whether activation and
rollback exist, whether behavior is attributable to a revision, how config is
prevented from becoming Truth, and which experiment mechanisms add more
platform complexity than value.

## 12. Future capability candidate: WIC Lab

WIC Lab is a candidate isolated internal environment for testing and optimizing
Watt interaction intelligence independently from production product UX. It is
not approved for implementation.

Candidate areas for post-study design:

- **Interactive Lab:** converse with WIC under a selected strategy or Policy
  revision. Engineering-only diagnostics may show selected Pattern and routing
  evidence, satisfied/missing semantic obligations, selected context,
  readiness, model/profile, Provider latency, token use, Policy revision and
  intermediate structured results. These diagnostics must remain separate from
  customer-facing UX.
- **Replay Lab:** replay frozen interactions against multiple strategies while
  preserving exact input evidence where possible.
- **Comparative evaluation:** side-by-side or blind Human review, semantic
  diff, metrics, scenario evaluation and batch-corpus execution.
- **Ablation:** assess whether Pattern Recognition, conflict analysis, context
  strategy, readiness logic, model profile, instruction revision or coalesced
  versus staged inference earns its cost.

WIC Lab must account for interaction effects and must not create an uncontrolled
combinatorial matrix. Exact UI and evaluation methodology remain open.

## 13. Future architecture candidate: WIC Policy

WIC Policy / Interaction Policy is a candidate separation between frequently
optimized interaction strategy and slower capability-code releases.

~~~text
Production Watt
    -> WIC capability runtime
    -> active immutable WIC Policy revision
~~~

A future Policy might describe some subset of Provider/model profile,
instructions, Pattern definitions, routing configuration, semantic obligations,
readiness strategy, context policy, artifact triggers, response strategy and
experiment metadata. Its exact contents are not frozen.

Policy may influence how Watt interprets, what it asks, which context it
selects, which Pattern it recommends and when it believes refinement is
sufficient. It does not own Human Intent, Work Reality, Human Authority,
Steering truth, Verification or Repository Reality. Policy is behavior and
configuration, not Product Truth.

Strategy/config changes might later ship as immutable Policy revisions.
Capability-code changes such as a new inference engine, parser, context
provider, domain type or Runtime capability still require ordinary code release
and technical qualification.

> Dynamic Policy release must never become dynamic arbitrary-code injection.

The future study should examine immutable versions, attribution, qualification,
activation and rollback, for example candidate -> Lab evaluation ->
qualification -> dogfood/canary -> activation, with a safe rollback from v19 to
v18. Historical interactions should ideally remain attributable to the exact
Policy revision used; no persistence design is frozen here.

Shadow research should separate the production response from a candidate
evaluation-only result. Canary research should cover internal dogfood, limited
cohort, broader cohort and default activation. Both must consider consistency,
attribution, rollback, Human experience discontinuity, privacy and cost. No
shadow, canary, feature flag or Policy Runtime is implemented by this plan.

## 14. Failure modes to investigate

The study must actively seek evidence of:

- **Spec drift:** documented intent no longer matches Reality.
- **Duplicate Truth:** multiple artifacts independently claim current truth.
- **Fake precision:** detailed specifications conceal unresolved uncertainty.
- **Documentation bureaucracy:** artifacts exist because a process requires
  them rather than because they improve decisions.
- **Human approval bureaucracy:** Humans approve steps that do not benefit from
  Human judgment.
- **Template lock-in:** an early wrong classification forces an inappropriate
  process.
- **Context bloat:** specifications accumulate and reduce model efficiency.
- **One-way waterfall:** implementation Reality cannot challenge earlier
  intent.

## 15. Watt guardrail: every artifact must earn its keep

> Every production artifact must earn its keep.

Any future Spec, Scenario Inventory, Architecture Tension Register, Prototype,
Pattern, Review Gate or Evidence Package must materially improve at least one
of:

- intent clarity or decision quality;
- implementation accuracy or feature coverage;
- risk reduction or verification;
- traceability or recovery;
- rework reduction;
- token/compute efficiency;
- Human cognitive efficiency.

If it does not, simplify or remove it. More artifacts do not automatically mean
better governance.

## 16. Learn mechanisms, not product metaphors

For each external mechanism, classify it from evidence as:

~~~text
ABSORB
ADAPT
REJECT
DEFER
~~~

Possible absorb/adapt candidates include stable intent representation,
requirement conflict analysis, versioning, diff-based intent updates,
traceability, work-type semantic obligations and requirement-to-verification
linkage.

Potential conflicts with Watt include user-selected workflow types, a fixed
Requirements -> Design -> Tasks sequence for every Work, Task as the central
production object, repository/project as universal identity, repeated approval
gates and chat/session as Truth. These classifications must not be assumed
before evidence is gathered.

## 17. Required comparison matrix

The future study should compare systems across:

| Dimension | System A | System B | System C | Watt implication |
|---|---|---|---|---|
| Intent object | | | | |
| Truth ownership | | | | |
| Work-type patterns and selection | | | | |
| Readiness and ambiguity analysis | | | | |
| Change propagation | | | | |
| Brownfield support | | | | |
| Human gates | | | | |
| Implementation feedback | | | | |
| Verification linkage | | | | |
| Versioning and context strategy | | | | |
| Cost/bureaucracy control | | | | |
| Experiment abstraction | | | | |
| Strategy configuration | | | | |
| Feature/mechanism toggles | | | | |
| Bundle/profile support | | | | |
| Replay and evaluation corpus | | | | |
| Ablation | | | | |
| A/B, shadow and canary | | | | |
| Policy versioning | | | | |
| Dynamic activation and rollback | | | | |
| Behavior attribution | | | | |
| Experiment metrics | | | | |
| Operational complexity | | | | |

The matrix supports mechanism analysis; it is not a feature checklist.

## 18. Required source evidence

For every significant mechanism, record:

- repository or documentation source;
- path/module when source-available;
- mechanism description and observed invariant;
- limitations;
- why it matters to Watt.

Marketing claims must remain separate from source-proven Reality.

## 19. Expected future deliverables

Only after explicit study authorization:

1. **External SDD Architecture Study:** narrative mechanism analysis.
2. **SDD Mechanism Matrix:** cross-project comparison.
3. **Source Evidence Index:** concrete source/document evidence.
4. **Watt WIC / Work Formation Implication Review:** evidence that confirms or
   changes Watt assumptions.
5. **Candidate WIC Architecture Amendment:** only after study completion and
   independent review.
6. **Experimentability Mechanism Review:** evidence about profiles, replay,
   ablation, Policy versioning, activation, rollback and operational cost.

This mission does not create the final architecture amendment.

## 20. Adaptive Work Patterns relationship

The [Adaptive Work Patterns candidate](watt-adaptive-work-patterns-candidate.md)
is a hypothesis to test, not a presumed answer. The study should ask:

- Is a Pattern layer useful?
- Should Patterns define steps or semantic obligations?
- How automatic should selection be, and how should rerouting work?
- What belongs to Pattern, WIC, Guided Design and Steering?
- How should versions and production-evidence learning be represented?

## 21. Experience-before-Production relationship

The [Experience-before-Production candidate](experience-before-production-candidate.md)
uses Scenario Inventory, Architecture Tension Register, Prototype Scenario
Packs, Reviewer Mode and Human Experience Acceptance.

An open question is whether Watt needs a conventional Spec artifact at all, or
whether versioned Work facts, scenarios, prototype and design/engineering facts
collectively form a stronger AI-native specification. Markdown specification
files are not assumed to be Watt's desired end state.

## 22. Future ECF relationship

SDD systems often use specifications as persistent context. Watt's future ECF
instead aims to assemble decision-scoped engineering Reality. The study should
determine whether Spec is a first-class fact, a projection of richer facts, or
one source among Work, Scenario, Decision and Repository Reality.

This plan does not implement ECF.

## 23. Guardian and Verification boundary

The existing principle remains:

~~~text
Executor != Verification != Guardian != Human Acceptance
~~~

Future intent/spec artifacts may define verification obligations, expected
behavior, scenario coverage and acceptance boundaries. They do not make the
Executor self-verifying.

## 24. Future WIC Optimization phase

If external evidence supports the direction, a later WIC Optimization / WIC Lab
phase should design two goals together.

### Goal 1: WIC intelligence calibration

Revisit open refinement, Adaptive Work Patterns, SDD mechanisms, Work
Formation, readiness, context selection, Human Journey/prototype triggers and
perceived intelligence.

### Goal 2: experiment and release infrastructure

Design an appropriately small WIC Lab, replay/evaluation harness, candidate
Policy model, strategy comparison workflow, immutable versioning and
activation/rollback seam. These goals should evolve together so Watt can
improve WIC without repeatedly restructuring the main product.

> The goal is to make WIC easier to improve, not to create a second complex
> product for configuring WIC.

Every layer must earn its keep. Experiment and Policy machinery must justify
itself through faster iteration, better evaluation, safer release, lower
main-application coupling, clearer attribution or lower rollback risk. If its
flags, configuration or tooling become more complex than the interaction
behavior being optimized, simplify it.

The intended program order is:

~~~text
clickable prototype review
    -> collect UX / WIC findings
    -> external SDD / WIC architecture study
    -> study external experimentation mechanisms
    -> Architecture Lead synthesis
    -> decide Adaptive Work Pattern / WIC architecture
    -> design WIC Lab + Policy architecture
    -> bounded implementation
    -> dogfood / benchmark
    -> production activation
~~~

WIC Lab implementation must not jump ahead of the external study.

## 25. Study timing

The Human Governor explicitly does not authorize this study now. The sequence
remains:

1. complete the current clickable-prototype Human review;
2. collect UX, WIC and Work Formation findings;
3. review those findings together;
4. decide whether to launch this study;
5. Human Governor approves/selects the external repositories;
6. Codex performs source-grounded study;
7. Architecture Lead independently reviews findings;
8. only then consider WIC or Work Formation architecture changes.

The plan must not interrupt the current prototype-review sequence.

## 26. Future dogfood and benchmark

If later study results lead to architecture changes, evaluate real Human
experience and production economics, not design elegance alone:

- refinement turns and time to meaningful Work Formation;
- Human corrections and Work Formation completeness;
- relevant-question and unnecessary-question ratios;
- Pattern misclassification and rerouting;
- Product Intent drift and scenario omissions;
- implementation rework;
- token cost and wall-clock time;
- Human cognitive effort;
- perceived intelligence and focus.

Where practical compare current open refinement with pattern-guided refinement.
Do not claim improvement without evidence.

## 27. Explicit non-goals and non-decisions

This plan does not:

- perform the architecture study or clone repositories;
- select a final external repository set;
- endorse SDD as Watt's product paradigm;
- freeze Adaptive Work Patterns;
- define a Spec, Pattern or persistence model;
- alter WIC, Work Formation, Guided Design or Steering;
- implement ECF or change Guardian/Verification;
- implement WIC Lab, WIC Policy, Runtime feature flags, shadow or canary;
- modify the clickable prototype.

## 28. Revisit point

~~~text
REVISIT_POINT
    AFTER_CLICKABLE_PROTOTYPE_REVIEW
~~~

At that point, the Human Governor will decide whether accumulated dogfood
evidence justifies launching the external study.

## 29. Current plan status

~~~text
STUDY_STATUS
    PLANNED

EXECUTION
    NOT_STARTED

IMPLEMENTATION_AUTHORITY
    NONE

REVISIT_POINT
    AFTER_CLICKABLE_PROTOTYPE_REVIEW

ARCHITECTURE_DECISION
    NOT_FROZEN
~~~

No implementation or external repository study has started.
