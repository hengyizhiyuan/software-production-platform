# WIC Progressive Intelligence Slice 2 Qualification

Date: 2026-09-15

Starting revision: `1c4b08bfec5271d455b0c2e5232e0e3b42da9cb6`

## Implementation

Slice 2 adds one progressively structured interpretation to each new
`InteractionAssessment`. Reception meaning, working understanding, typed deltas,
assumptions, unresolved Human decisions, advisory pattern signals, question
evaluations, governance disposition, and transition-specific readiness share one
exact basis fingerprint. They are not independent truth owners.

Migration `20260915_40` adds nullable JSONB to existing assessments. Historical
rows remain readable. The structure cannot call Work Formation, Work Revision,
Plan, or production services; existing `WorkEvolutionCandidateChange`, immutable
`WorkRealityRevision`, and `WorkTransitionRecord` remain governed integration.

Policy attribution is `wic-semantic-policy-v1`,
`wic-question-value-v1`, `wic-transition-readiness-v1`, and assessment schema
`wic-assessment-v4`.

## Deltas, corrections and constraints

`SemanticDelta` supports `ADDED`, `REVISED`, `SUPERSEDED`, `REMOVED`, and
`NO_CHANGE`, with category, source records, basis, prior assessment, old/new
value, confidence, rationale, and authority. Explicit corrections create a
`SUPERSEDED` Motive edge. History remains intact; repeated and reversing
corrections create new edges.

New constraints union with existing active-Work constraints. OW-D retains the
current Work and prior “一期不建设完整 CRM” obligation while adding location and
feature-preservation constraints. Deltas stay advisory until Human admission.

## Governance and readiness

Policy distinguishes reversible established presentation conventions from
Human-owned privacy, disclosure, retention, destructive, paid, irreversible,
and authority choices. Critical rules live in code, not Provider prompts.

Question policy considers decision dimensions, existing evidence,
reversibility, Watt authority, blocking effect, cognitive cost, and value. It
emits at most one `ASK_HUMAN_NOW`; lower-value gaps are inferred, deferred, or
non-material. Missing fields alone do not create a questionnaire.

OW-F yields `HUMAN_DECISION_REQUIRED`, one Human-owned delta and one combined
highest-value question. Work Formation is `NOT_READY`, while Design Progression
is `READY`, so harmless architecture exploration can continue.

Readiness profiles are `WORK_FORMATION`, `WORK_REVISION`, and
`DESIGN_PROGRESSION`. Each reports evidence, missing evidence, Human decisions,
assumptions, risks, useful-progress status, exact basis, and policy revision.
Readiness remains `ADVISORY_ONLY` and never grants authority.

Pattern signals are advisory and combinable: correction, bounded change,
constraint addition, direct question, recommendation request, new object,
high-impact ambiguity, and brownfield conflict. Artifact recommendation requires
a named consumer and protected obligation; otherwise it is absent.

## Frozen A–H qualification

Raw run: [`open-wic-progressive-runs/2026-09-15-deepseek-flash-low.json`](open-wic-progressive-runs/2026-09-15-deepseek-flash-low.json)

Separated policy evaluation: [`open-wic-progressive-runs/2026-09-15-policy-evaluation.json`](open-wic-progressive-runs/2026-09-15-policy-evaluation.json)

| Case | Real Deep WIC | Deterministic policy |
|---|---|---|
| OW-A | candidate | formation waits for one material answer; design can continue |
| OW-B | candidate | bounded Work revision ready; no unnecessary question |
| OW-C | two turns captured | correction supersedes activity Motive; history preserved |
| OW-D | retained validation failure | deterministic constraint-preservation tests pass |
| OW-E | candidate | `NEW_MOTIVE_CANDIDATE`; active Work unchanged |
| OW-F | prose authority violation | unsafe inference blocked; Human decides; design remains possible |
| OW-G | candidate | safe reversible inference; Work revision candidate |
| OW-H | factual misunderstanding | PostgreSQL Reality supersedes MySQL premise; Motive unchanged |

The real run used DeepSeek `deepseek-flash/low`, pre-Work coalescing, and no
retries. Seven of eight episodes and eight of nine turns produced candidates.
OW-D retained one contract failure. Candidate-ready time was 10.08–19.74
seconds, median 15.79 seconds. Successful evidence retained 12 Provider calls
and 62,312 tokens; failed usage and RMB cost were unavailable.

Provider adjudication recorded one authority violation (OW-F), one material
misunderstanding (OW-H), and one failure (OW-D). Policy results are reported
separately; failures were not rerun to improve the outcome.

## Adversarial evidence

[`slice2-corpus-v1.json`](../../benchmarks/open_wic/slice2-corpus-v1.json) has 12
cases covering repeated/reversed corrections, simultaneous constraints, safe
and unsafe inference, explicit/ambiguous new Motives, stale repository facts,
brownfield contradiction, low-value details, architecture ambiguity, and partial
progress. Focused tests pass for history, constraint retention, new-Motive
separation, authority, question selection, readiness, and factual reconciliation.

## Fast Reception, performance and findings

Slice 1 remains `PROVISIONAL_READ_ONLY`, `SHADOW_ONLY`, independent of Deep WIC,
and byte-locks the original OPEN_WIC artifacts. The hosted Fast profile remains
unqualified and disabled.

Slice 2 adds deterministic policy assembly and one JSONB value in the existing
assessment transaction. It adds no Provider call or dependency before Deep WIC.
No material regression appeared in tests; live production distribution remains
a Slice 3 rollout measurement.

Slice 3 can proceed in controlled mode. It must account for Deep Provider prose
that can still violate policy, OW-D schema instability, missing hosted Fast
coverage, and browser/server timing not yet being durably correlated. vNext
policy must run before any future visible provisional or final prose is accepted.

```text
SLICE_2_PROGRESSIVE_INTELLIGENCE COMPLETE
PROGRESSIVE_STRUCTURING IMPLEMENTED
SEMANTIC_DELTA IMPLEMENTED
CORRECTION_SUPERSESSION IMPLEMENTED
QUESTION_VALUE_POLICY IMPLEMENTED
SAFE_INFERENCE_POLICY IMPLEMENTED
ADAPTIVE_PATTERN_GUIDANCE IMPLEMENTED_ADVISORY
NEXT_STEP_READINESS IMPLEMENTED
HUMAN_AUTHORITY PRESERVED
WORK_IDENTITY MOTIVE_BOUND
FAST_RECEPTION NO_REGRESSION
HOSTED_FAST_PROVIDER STILL_UNQUALIFIED
OPEN_WIC_BASELINE UNCHANGED
SLICE_3_READINESS READY_WITH_FINDINGS
```
