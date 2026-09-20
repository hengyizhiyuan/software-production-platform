# Engineering Semantic Truth

Date: 2026-09-18

Status: focused qualification passed; ready for Human Review.

Engineering Semantic Truth is the governed, software-production-specific
meaning Watt currently knows or believes about Human intent. It prevents
Conversation, Steering, Production, and Verification from independently
reinterpreting the same source phrase after Work admission.

This architecture does not define what Watt should do next. Steering retains
`WHAT NEXT`; the future
[WIC Software Production SOP × LLM direction](wic-software-production-sop-and-llm-direction.md)
remains separate and not started.

## Boundary and flow

```text
Human expression
    -> neutral semantic extraction
    -> contextual product-semantic binding
    -> governed Engineering Semantic Facts
    -> Work Reality
       |-- Conversation
       |-- Steering
       |-- Production / PWU Completion Contract
       `-- Verification obligations and evidence lineage
```

Neutral extraction records observable syntax such as ordered values,
quantities, units, ranges, comparisons, references, behavior, state change, or
scope. It does not assign contextual roles that the Human did not state.

Contextual binding uses the current software/product context to create
Work-scoped subjects and reusable relations. For example, `8×5` may be
extracted as ordered values `[8, 5]`, then bound under a course-schedule context
to `schedule.period CARDINALITY 8` and `schedule.weekday CARDINALITY 5` as
working assumptions. No schedule-specific parser owns that interpretation.

## Fact representation

Each durable Engineering Semantic Fact carries:

- a stable fact identity;
- a Work-scoped subject and reusable semantic relation;
- a scalar or ordered value, optional unit, scope, and qualifiers;
- authority and epistemic status;
- exact Human source records and source text;
- neutral-extraction references and explicit/inferred role origin;
- supersession lineage; and
- the Work Reality revision that admitted it.

The reusable relation algebra covers cardinality, equality, ordered components,
bounds, comparisons, mappings, references, precedence, behavior, state
transition, scope, and acceptance assertions. Subjects remain contextual, such
as `image.width`, `api.response_time`, or `login.submit_button`; Watt does not
predefine a global ontology of every software object.

Free-form context and constraints remain supported when safe structured meaning
is unavailable. Structured facts do not need to exist for every sentence, and
legacy text cannot override a more authoritative current fact.

## Authority and epistemic status

Authority distinguishes `HUMAN_EXPLICIT` from `SYSTEM_INFERRED`. Epistemic
status distinguishes `CONFIRMED`, `WORKING_ASSUMPTION`, `UNRESOLVED`, and
`SUPERSEDED`.

A system inference cannot claim Human confirmation and cannot replace explicit
Human truth. A later explicit Human correction may supersede weaker facts.
Historical facts remain immutable evidence, while only non-superseded facts are
current Work semantic truth.

Ambiguity follows Progressive Admission. A reversible, low-risk, cheap-to-fix
interpretation may remain a labeled working assumption when it does not block
the current step. Ambiguity material to authority, safety, irreversibility,
cost, scope, acceptance meaning, or external mutation remains unresolved and
requires Human resolution.

## Product semantics and implementation semantics

Engineering Semantic Truth records product meaning rather than prematurely
freezing implementation shape.

```text
Product truth
    8 course periods across 5 weekdays

Possible implementation
    header + 8 period rows
    label + 5 weekday columns
```

Production may translate product facts into implementation structure. It may
not rewrite those product facts. Verification checks the same product-semantic
obligations through implementation-aware evidence; it does not infer an exact
DOM shape unless an admitted implementation contract requires one.

## Ownership and consumption

Interaction assessment persists neutral extraction and candidate fact evidence.
Human Work admission or Work-revision admission makes the fact ledger part of
the immutable Work Reality revision.

Conversation receives current admitted facts separately from advisory
candidates and must preserve authority and assumption labels. Steering receives
the current facts in its Plan Frame while remaining the owner of next-step
selection. Production receives exact fact references in the PWU Completion
Contract and Executor instruction. Verification receives those same references;
its evidence records the depended-on fact identities.

The existing chain from Work Reality revision to production binding, Work Unit,
Candidate, Verification, and authorization supplies lineage without duplicating
facts across every table.

## Supersession and invalidation

An admitted correction creates a new fact, marks replaced facts `SUPERSEDED`,
and advances Work Reality. Existing production bindings remain historical for
their exact older revision. Current-cycle, Candidate, Verification, and Human
authorization checks continue to reject stale lineage after a material Work
Reality change; historical evidence is not rewritten.

## Non-goals

Engineering Semantic Truth does not:

- formalize every Human sentence;
- create a universal ontology or world-knowledge language;
- use business-case parser registries;
- turn product facts into fixed implementation shapes;
- own next-step policy, Steering, Production, or Verification judgment;
- change the Progressive Admission sufficiency model; or
- implement the future WIC Software Production SOP × LLM redesign.
