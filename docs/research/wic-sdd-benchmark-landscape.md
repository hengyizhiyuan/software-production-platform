# WIC / SDD Benchmark and Evaluation Landscape

Date: 2026-09-15
Status: external benchmark study complete; Watt benchmark design and implementation remain pending.

This record separates four questions that must not collapse into one score:

1. **Specification Reasoning** — can a system find ambiguity, conflict, assumptions, and missing cases?
2. **Specification Adherence** — does an artifact or implementation satisfy a stated contract?
3. **Implementation Capability** — can an agent produce a working repository change from an already formed task?
4. **Workflow Effectiveness** — does the complete Human+AI strategy improve intent fidelity and production outcome enough to justify its cost?

Evidence anchors are in the [Source Evidence Ledger](wic-sdd-source-evidence.md).

## 1. Evaluation found in the seven repositories

| System / mechanism | Unit under evaluation | Ground Truth | Visible / hidden | Measures | Cost measured | Main blind spot | Watt relevance |
|---|---|---|---|---|---|---|---|
| Kiro sample correctness plan (K04–K05) | Planned properties/tests for one spec | Authored requirements and properties | Visible | Intended requirement/property/task traceability | No | Plan, not execution evidence; commercial harness absent | Candidate WIC-Bench C/D obligations. |
| Spec Kit tests (S01–S08) | CLI/workflow/template behavior | Repository assertions and snapshots | Visible | Structural determinism and config/extension regression | Runtime only | Not generated-spec quality, Human alignment, or ROI | Reproducible policy/config test pattern. |
| Spec Kit `analyze` | One spec/plan/tasks set | Constitution + requirements/stories | Visible | Inconsistency, underspecification, coverage | No | Keyword/ID coverage is not semantic satisfaction | WIC-Bench B/C input. |
| OpenSpec tests (O02–O07) | Deltas, stable specs, graph, archive | File/requirement/scenario expectations | Visible | Delta correctness, loss, path safety, lifecycle | No | Unrepresented Human intent is invisible | Strong C/D drift cases. |
| OpenSpec agent verify (O07) | Implementation vs change artifacts | Tasks/spec/design interpreted by agent | Visible | Completeness, correctness, coherence | No | Self-judgment is not independent assurance | Rubric shape only. |
| BMAD gates (B03–B06) | Architecture/spec/tracking/diff | Workflow rules, baseline diff, criteria | Visible | Readiness, consistency, review | No | Prompt behavior and Human burden unmeasured | Brownfield C/D cases. |
| BMAD A/B note (B07) | Two reviewer prompt framings | Residual-bug hit rate in uninspected pilot | Insufficient evidence | Persona-framing value | Not reported | Changelog claim without corpus/model/output evidence | Measurement norm, not reusable result. |
| Agent OS | Commands/profiles; no general eval harness established | N/A | N/A | Static behavior only | No | “Better specs” outcome unproven here | Requires Watt-owned evaluation. |
| Tessl weighted cases (T06–T08) | Agent output/workspace edits for seeded tasks | Handcrafted checklist | Criteria visible | Gap analysis, questions, drift, review, proportionality | No | Gameable; no holdout/Human/rework evidence | Best local seed for A–C rubrics. |
| Tessl link scripts (T02–T03) | Spec metadata and paths | Filesystem/format | Visible | Structural linkage | Execution only | Existence does not prove behavior | Cheap precondition, not final score. |
| KiroCrew multi-session harness (C04) | Memory across fresh provider sessions | Scenario assertions | Visible | Recall, lessons, context accumulation | Time estimate | Memory is not governed Work continuity | A/fresh-session subtests. |
| KiroCrew skill A/B (C05) | With-skill vs without-skill behavior | Case assertions/graders | Visible | Triggering, behavior, recall | Model cost implicit | Small samples; production intent absent | WIC Lab abstraction candidate. |
| KiroCrew provenance reports (C06) | Retrieval over frozen corpora | Labeled items/structural constraints | Visible | Recall/ranking/abstention/context bounds | Partial | Retrieval is not answer/workflow quality | Absorb attribution discipline. |

## 2. External primary benchmark families

### SWE-bench

Primary sources: [official repository](https://github.com/SWE-bench/SWE-bench), [ICLR paper](https://openreview.net/forum?id=VTF8yNQM66).

- **Unit:** repository at a historical state plus a real GitHub issue; output is a patch.
- **Ground Truth:** fail-to-pass and pass-to-pass tests; Verified adds Human-vetted solvability.
- **Visibility:** evaluation tests are withheld in the standard setup; repository tests may be visible.
- **Measures:** repository navigation and issue-resolution implementation capability in containers.
- **Blind spot:** assumes the issue is already the task; does not measure Motive discovery, correction, Work Formation, artifact ROI, or Human cognitive cost.
- **Watt use:** downstream WIC-Bench D component only, never a substitute for A/B/C.

### FeatureBench

Primary source: [FeatureBench paper](https://arxiv.org/abs/2602.10975).

- **Unit:** feature-level implementation with explicit interfaces in an existing repository or standalone module.
- **Ground Truth:** test-driven extraction with fail-to-pass/pass-to-pass tests and dependency-derived feature slices.
- **Ambiguity:** callable interfaces/import paths are intentionally specified to reduce evaluation ambiguity.
- **Ablation:** the paper varies visible unit tests and execution-step budgets.
- **Blind spot:** pre-resolving the interface removes much of the WIC problem Watt needs to measure.
- **Watt use:** stronger D substrate for feature work and a useful context/test ablation precedent.

### LongMemEval

Primary source: [LongMemEval paper](https://arxiv.org/abs/2410.10813).

- **Unit/Ground Truth:** 500 curated questions over scalable multi-session histories.
- **Measures:** extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention.
- **Blind spot:** a remembered conversation fact is not current Work Reality or authority.
- **Watt use:** correction, fresh-session consistency, temporal ordering, and abstention subtests for A.

### LoCoMo

Primary source: [LoCoMo paper](https://arxiv.org/abs/2402.17753).

- **Unit/Ground Truth:** long conversations grounded in personas/event graphs and Human-edited for consistency.
- **Measures:** question answering, event summarization, and multimodal dialogue across sessions.
- **Blind spot:** does not distinguish Human statement, interpretation candidate, admitted Work Reality, and production evidence.
- **Watt use:** conversation-history stress cases, not Work admission or overall WIC quality.

## 3. Ground Truth problem for WIC

WIC cannot treat the first Human message as ground truth. A valid episode may include incomplete or contradictory expression, later corrections, unstated preferences that must not be invented, multiple acceptable solutions, or a new Motive that must remain separate from current Work.

Each case therefore needs a Human-adjudicated Reference Intent Package rather than one expected response. It should version:

- facts known at each turn;
- acceptable inferences;
- assumptions that must be surfaced;
- decisions requiring Human cognition;
- forbidden inventions;
- Work-boundary expectations;
- sufficient outcomes and unacceptable drift;
- optional versus risk-required structure.

The package itself needs review and provenance; otherwise a benchmark only measures agreement with one hidden annotator preference.

## 4. Mapping to WIC-Bench A–D

### WIC-Bench A — Intent Understanding & Refinement

External support: Tessl vague-request/question cases; LongMemEval/LoCoMo correction and multi-session tasks; Agent OS/Spec Kit context-aware questioning.

Watt gaps: Motive fidelity across corrections, invented requirements, Work/new-Motive separation, decision value per question, Human cognitive effort, and reconstruction from governed facts.

### WIC-Bench B — Work Pattern & Readiness

External support: BMAD right-sizing, Tessl trivial exception, Spec Kit/OpenSpec readiness plumbing, and configurable workflows.

Watt gaps: open→candidate Pattern timing, premature lock-in, rerouting, blended obligations, false-ready versus over-refined rate, and readiness for the next step rather than the whole Work.

### WIC-Bench C — Specification / Experience Quality

External support: Kiro sample properties, Spec Kit analysis, OpenSpec delta/scenario-loss checks, Tessl spec/test links, and Watt's Experience-before-Production cases.

Watt gaps: visible uncertainty, named artifact consumer, decision improvement, duplicate-truth burden, over-specification penalty, Human review cost, and experience acceptance beyond tests.

### WIC-Bench D — End-to-End Production Effectiveness

External support: SWE-bench for bug resolution, FeatureBench for feature work, and OpenSpec/Tessl for adherence checks.

Watt gaps: Motive→Work→Plan/PWU→production→Verification→Runtime/Acceptance lineage, rework caused by misunderstanding, trusted outcome, total cost, and model/session replacement consistency.

## 5. Experimental controls

A valid comparison should hold constant or record:

- case and Reference Intent Package revision;
- repository/runtime baseline;
- model/provider/reasoning profile;
- capability-code and behavioral-Policy revisions;
- context-selection revision and exact supplied facts;
- tool/network capabilities;
- seed where supported;
- retry/resume and Human-intervention protocols;
- grader/rubric revision;
- tokens, calls, latency, tool activity, Human time, and rework.

Model output need not be deterministic. Compare distributions and material outcomes across paired repeated runs, not isolated anecdotes.

## 6. Replay, A/B, and ablation inputs

**Replay** must capture turn sequence and governed Reality visible at each decision. Chat-only replay tests transcript memory, not WIC over Reality.

Candidate **A/B** comparisons:

- OPEN_WIC vs PATTERN_GUIDED_WIC;
- one-question formatting vs highest-decision-value policy;
- full artifact set vs minimum-consumer artifact set;
- conversation-only context vs governed-frame context;
- fixed Pattern vs reroutable Pattern.

Candidate **ablations** remove one mechanism at a time: repository grounding, correction history, Pattern guidance, explicit assumptions, Human Work Formation review, scenario-loss checks, verification linkage, or fresh-session reconstruction.

Measure both quality loss and cost reduction. A mechanism has not earned its keep if removing it does not materially hurt outcomes or reduces total rework.

## 7. Evaluation gaps Watt must fill

No inspected benchmark jointly measures:

1. evolving Human intent and correction;
2. Work-boundary correctness;
3. readiness timing;
4. proportional structure;
5. Human cognitive cost;
6. downstream implementation and verification;
7. Runtime/product acceptance;
8. model/session replacement consistency;
9. policy attribution and rollback;
10. structural ROI.

Watt will likely need its own layered corpus and harness. This is a study conclusion, not implementation authority.

## 8. Benchmark risks and mitigations

| Risk | Mitigation |
|---|---|
| Visible-rubric gaming | Holdout cases, paraphrases, and behavior checks. |
| Reference Intent ambiguity | Acceptable/forbidden sets plus adjudicator disagreement. |
| Contamination | Time/version provenance and hidden cases. |
| Model variance | Repeated paired runs and uncertainty intervals. |
| Judge bias | Deterministic checks where possible; calibrated multiple judges. |
| Rewarding verbosity | Over-structure and Human-reading-cost penalties. |
| Test-only optimization | Experience/acceptance and unchanged-behavior obligations. |
| Invalid comparison | Corpus/model/policy/source fingerprints and comparability declaration. |
| Conversation leakage | Isolated cases without answer-bearing history. |
| Cost blindness | Track tokens, calls, latency, Human decisions, rework, and maintenance. |

## 9. Conclusion

Tessl is the clearest inspected reference for specification-reasoning/adherence cases; KiroCrew is the clearest supporting reference for replay/A-B/provenance; SWE-bench and FeatureBench are downstream implementation references. No external benchmark answers whether a WIC strategy improves the entire intent-to-trusted-outcome loop.

~~~text
EXTERNAL_BENCHMARK_STUDY COMPLETE
BENCHMARK_DESIGN          PENDING
BENCHMARK_IMPLEMENTATION  NOT_STARTED
WIC_LAB                   STILL_CANDIDATE
~~~
