# Watt WIC / SDD External Architecture Study

Date: 2026-09-15
Status: external source study complete; Watt architecture synthesis pending; implementation not authorized.

Related records:

- [Source Evidence Ledger](wic-sdd-source-evidence.md)
- [Mechanism Matrix](wic-sdd-mechanism-matrix.md)
- [Benchmark Landscape](wic-sdd-benchmark-landscape.md)
- [Architecture Study Plan](../product/watt-wic-sdd-architecture-study-plan.md)
- [Adaptive Work Patterns Candidate](../product/watt-adaptive-work-patterns-candidate.md)

## 1. Executive findings

The seven systems do not implement one common SDD architecture. They combine different mechanisms under similar language:

- **Spec Kit** externalizes intent into a constitution-constrained artifact pipeline and performs explicit cross-artifact analysis.
- **OpenSpec** treats an in-flight change as deltas against stable capability specs, then synchronizes and archives it.
- **BMAD** uses role-specific, right-sized instructional workflows and preserves baseline/context artifacts across delivery.
- **Agent OS** captures product context and codebase standards, then selects relevant standards for a shaped spec.
- **Tessl SDD Tile** makes requirement interviewing, spec/test links, drift review, and weighted behavior evals explicit.
- **Kiro documentation and its repository sample** show requirements/design/tasks and property links, but the clone does not contain Kiro's commercial core runtime.
- **KiroCrew** supplies useful continuity and experiment mechanisms—durable ledgers, multi-session scenarios, A/B lanes, and provenance—but is a supporting sample rather than an SDD authority.

No inspected system establishes Watt's complete target: natural Human expression, Motive-bound Work formation, explicit authority transfer, Reality-driven direction, governed production, and trusted Runtime outcome. The useful result is therefore a mechanism portfolio, not a framework selection.

The strongest provisional recommendations are:

| Classification | Mechanisms |
|---|---|
| **ABSORB** | Evidence classification; delta/change history; explicit contradiction and scenario-loss checks; requirement-to-verification links; brownfield code inspection; replayable cases with frozen provenance; proportionality tests. |
| **ADAPT** | Pattern/right-sizing, artifact dependency graphs, one-question refinement, standards/context indexes, specification drift reconciliation, configurable workflows, cross-session ledgers. |
| **REJECT** | First-message fixed routing; artifact existence as semantic readiness; universal Requirements→Design→Tasks UI; spec or repository as Work identity; Executor-authored spec changes silently redefining Human intent; repetitive Human checkbox approval; generic test pass as trust. |
| **DEFER** | Final Pattern taxonomy, Policy schema, automatic pattern switching, full WIC Lab, ECF design, Production Passport integration, commercial scheduling/rollout mechanisms. |

## 2. Evidence boundary

Every significant claim is tied to the [Source Evidence Ledger](wic-sdd-source-evidence.md) and classified as SOURCE_PROVEN, DOCUMENTATION_PROVEN, OBSERVABLE_BEHAVIOR_ONLY, or INFERENCE.

Important constraints:

1. Templates and skills prove requested behavior, not reliable model compliance.
2. Tests prove the tested mechanism at the pinned revision, not workflow benefit in Human use.
3. Repository documentation is not promoted to source proof.
4. Kiro's own README says the product source is not in the inspected clone; only its documentation and sample artifacts are admissible here.
5. The study did not execute model-dependent external workflows. No effectiveness claim is derived from a README demo.

## 3. Per-system architecture findings

### 3.1 Kiro

The inspected repository provides two evidence layers. The README documents Specs, requirements analysis, property-based correctness, steering, permissions, checkpoints, and cloud sessions (K01–K02). A concrete repository-owned sample contains user stories and WHEN/THE/SHALL criteria, design properties linked to requirement numbers, requirement-linked tasks, optional property tests, and checkpoints (K03–K05).

Useful structure: explicit requirement/property/task linkage can make verification obligations inspectable. The sample also separates universal properties from example tests.

Residual risk: the commercial implementation, artifact state machine, Human gates, Quick Spec/Bug Fix routing, persistence, and rerouting are not source-proven by this clone. Treating the sample as the product architecture would be an evidence error.

Watt input: **ADAPT** requirement-to-property lineage; **DEFER** Kiro-specific flow and sandbox claims pending source/observable evidence; **REJECT** copying a three-document UI as Watt's default Human experience.

### 3.2 GitHub Spec Kit

Spec Kit has the most explicit phase pipeline among the inspected sources. Specify transforms natural language into a testable feature spec and checklist; Clarify asks a bounded sequence of high-impact questions and writes answers into the spec; Plan applies a constitution gate and research phase; Tasks creates dependency-ordered work; Analyze checks consistency and coverage; Implement uses checklist state as a gate (S01–S06).

Its current workflow engine and extension system provide genuine configurability—steps, gates, prompts, commands, loops, switches, fan-out/fan-in, presets, and overlays (S07–S08). That is useful evidence for a future WIC Lab seam: capability code and behavioral workflow can be separated.

Useful structure: a non-negotiable constitution, read-only cross-artifact analysis, bounded clarification, explicit coverage inventory, and optional extension ownership.

Residual risk: the default experience exposes artifacts/phases, and checklist or file completion can be mistaken for semantic readiness. Requirements, plan, tasks, and implementation can become duplicate truth. Core analysis maps some coverage by keywords/IDs rather than authoritative lineage. The system is strong at executing an already feature-shaped request and weaker evidence for Motive discovery.

Watt input: **ABSORB** consistency analysis and principle gates; **ADAPT** workflow configuration and artifact dependencies behind a natural WIC surface; **REJECT** making the pipeline itself the Work lifecycle.

### 3.3 OpenSpec

OpenSpec's distinctive mechanism is the separation between stable capability specs and in-flight change deltas. Proposal establishes why; delta specs describe behavioral change; design and tasks supply implementation context; archive synchronizes deltas into main specs and retains the completed change (O01–O06).

The artifact graph is implemented, but completion is initially inferred from output existence (O02–O03). Validation is materially stronger than existence: it detects unsafe paths, malformed deltas, archive conflicts, and scenario loss. Verify-change adds requirement/scenario/design/task review, partly through agent judgment (O07).

Useful structure: change-local deltas prevent every revision from rewriting the full stable spec; archive preserves a change record; scenario-loss checks make one class of semantic drift deterministic; brownfield can start with the next change rather than requiring exhaustive backfill (O08).

Residual risk: change deltas and main specs are coordinated truth surfaces. Synchronization can fail or misapply intent, and stable specs can become stale relative to repository/runtime Reality. Artifact existence is a weak readiness signal. Cross-repository planning is documented but not equivalent to Watt's governed multi-resource production.

Watt input: **ABSORB** delta/revision semantics and deterministic loss detection; **ADAPT** stable spec/change relationship into Work Reality provenance; **REJECT** “repo is source of truth” as a replacement for Watt's layered authority model.

### 3.4 BMAD Method

BMAD explicitly advocates right-sized process and durable context (B01). Source-visible skills route simple changes differently from large plans, inspect brownfield code before architecture decisions, preserve draft state, gate readiness, generate/repair tracking, and review the actual baseline diff (B02–B06).

The adaptation mechanism is mostly embodied in skills, step files, frontmatter, and scripts rather than a central typed policy runtime. This makes it flexible and inspectable, but behavior depends heavily on instruction following.

Useful structure: proportional depth, specialized perspectives, brownfield-first Reality inspection, explicit deferred/open decisions, and diff-based review rather than trust in an agent summary.

Residual risk: many named roles, modes, planning artifacts, and tracking states can increase Human/navigation cost. “Right-sized” is partly model judgment and can vary across sessions. A documented A/B pilot is encouraging but does not establish a general evaluation platform (B07).

Watt input: **ABSORB** proportionality and baseline-grounded review; **ADAPT** role lenses as internal capabilities, not user-selected agents; **REJECT** exposing the whole method as mandatory product workflow.

### 3.5 Agent OS

Agent OS externalizes product mission, roadmap, and stack, discovers codebase conventions, indexes them, shapes a feature spec with references/visuals/product alignment, and injects selected standards (A01–A05).

Its standards index is a useful context-cost mechanism: selection can occur from short descriptions before full standards are loaded. It also requires Human explanation of why discovered patterns should become standards, reducing the chance that code alone becomes intent.

Useful structure: separate durable product context, concise standards, code/reference discovery, and scoped context selection.

Residual risk: fixed interview questions and placeholders can create fake completeness. Repeated per-standard confirmation makes the Human a workflow operator. Selection is model-driven and the repository does not establish immutable selection/policy attribution or an effectiveness benchmark.

Watt input: **ADAPT** the compact index and decision-scoped loading for future ECF; **ABSORB** Human confirmation before promoting observed convention; **REJECT** equating product files with Work truth.

### 3.6 Tessl Spec Driven Development Tile

Tessl provides the clearest small evaluation corpus for requirements behavior. Its skills require gap-based interviewing, one question at a time, explicit Human confirmation, behavior specs linked to target files and tests, and post-implementation drift review (T01–T05).

The evals use visible weighted criteria for vague-request decomposition, question quality, seeded drift, work review, and a trivial-change exception (T06–T08). This is source-proven evaluation structure, not proof of model performance because no run result was relied on.

Useful structure: evaluate the interaction behavior itself, test over-structuring with a trivial-change case, require existing-spec awareness, and make drift failures concrete.

Residual risk: “zero ambiguous requirements” and “spec before code” are too absolute for exploratory or evolving Motives. Updating a spec to match discovered implementation can let Executor behavior redefine intent. File/glob lineage is fragile. Self-review is not Watt Verification.

Watt input: **ABSORB** case/criterion patterns for WIC-Bench A–C; **ADAPT** one-question behavior into highest-decision-value questioning; **REJECT** universal spec approval and automatic spec-to-code truth reversal.

### 3.7 KiroCrew

KiroCrew demonstrates durable task/session continuity and evaluation mechanics. Its task runner derives steps from arbitrary text, tracks progress, and restarts from a saved plan. Its session ledger persists goal, phase, next step, rejected approaches, artifacts, and bounded events separately from transcript. Goal conduction binds ledger items to sessions and checks worker claims with a world-state evaluator (C01–C03).

Its multi-session eval creates fresh provider instances so continuity must come from persisted state; skill evals distinguish deterministic checks from A/B model runs. Its memory report carefully records corpus/model/source fingerprints and refuses invalid score comparisons (C04–C06).

Useful structure: transcript-independent resumable state, explicit evidence limits, fresh-session replay, A/B lanes, bounded context, and claim-versus-world-state separation.

Residual risk: task/session goals are not Motive-bound Work; saved plan is not governed Plan; its evaluations emphasize memory and skills, not Human intent formation. It must remain a supporting mechanism source.

Watt input: **ABSORB** provenance discipline; **ADAPT** replay and policy comparison into a WIC Lab; **REJECT** session/task state as Work truth.

## 4. Intent representation and truth ownership

All systems externalize more than chat, but they externalize different objects:

| System | Durable representation | Effective truth tendency | Watt concern |
|---|---|---|---|
| Kiro sample | requirements/design/tasks | requirements lead design/tasks | Core reconciliation not established. |
| Spec Kit | constitution + spec/plan/tasks | constitution is hard constraint; spec drives downstream | Multiple artifacts can disagree; Work authority absent. |
| OpenSpec | stable specs + change deltas | repository artifacts are explicit source | Delta/main-spec synchronization creates dual surfaces. |
| BMAD | briefs/specs/architecture/stories/context | workflow artifact appropriate to phase | Authority is mostly instructional and distributed. |
| Agent OS | mission/roadmap/stack/standards/spec | repository context guides agent | Observed conventions may be promoted too eagerly. |
| Tessl | `.spec.md` + targets/test links | approved spec is normative | Implementation-driven spec updates need authority control. |
| KiroCrew | transcript + memory + task/ledger state | state separated by store/purpose | Session continuity is useful but not production truth. |

For Watt, Conversation remains provenance, candidate interpretation remains advisory, admitted Work Reality is governed, Plan owns direction, and Verification/Runtime own their facts. **ADAPT**, not copy, every external truth model.

## 5. Refinement, ambiguity, and readiness

Three mechanism families emerged:

1. **Bounded question loops** — Spec Kit and Tessl prioritize high-impact ambiguities and ask one question at a time. Agent OS also uses one-at-a-time interviews. This reduces bundled-question failure but can become procedural if every uncertainty becomes a Human question.
2. **Artifact/schema gates** — Spec Kit and OpenSpec use dependency/completeness structures; BMAD readiness checks whether developers would need to invent decisions. Deterministic structure is valuable, but file existence is not semantic readiness.
3. **Human confirmation** — all prominent SDD flows retain review/approval. This protects intent but risks approval bureaucracy when Humans only stamp generated documents.

Watt should test a different objective: ask the question with the highest expected decision value; infer reversible details; surface assumptions; stop when remaining uncertainty is tolerable for the next governed step. This is an **ADAPT** recommendation, not a frozen algorithm.

## 6. Work specialization and adaptive patterns

Evidence supports the value of specialization but not a fixed taxonomy:

- BMAD has clear versus complex paths and role-specific workflows.
- Spec Kit has extensions such as bug/assessment paths and configurable workflow definitions.
- Tessl explicitly exempts trivial changes from full SDD.
- Agent OS shapes significant work but remains a largely fixed interview.
- Kiro documentation references Specs/analysis, while Quick Spec/Bug Fix internals are not source-proven here.

Evidence **for** the candidate “Pattern constrains AI search space, not Human expression space”:

- Right-sized and trivial-change paths show that one universal depth is wasteful.
- Gap-based questions are better when they use existing specs/repository context.
- Separate bug, feature, architecture, and assessment mechanisms encode different semantic obligations.

Evidence **against or unresolved**:

- Several systems expose modes/commands, shifting classification and navigation to the Human.
- No inspected system proves robust open→candidate→reroute behavior under changing Motive.
- Pattern blending, confidence, and correction costs remain unmeasured.

Conclusion: Adaptive Work Patterns remain **CANDIDATE**. The mechanism is **ADAPT**; first-message classification and fixed workflow lock-in are **REJECT**.

## 7. Artifact lifecycle, drift, and feedback

OpenSpec supplies the strongest explicit change-propagation mechanism: deltas are validated, merged, rechecked, and archived. Spec Kit supplies strong cross-artifact consistency checks. Tessl supplies direct spec-target-test drift cases. BMAD preserves baseline diffs and tracking state.

No mechanism fully resolves the authority question when implementation discovery contradicts intent. Three distinct updates must remain separate:

1. Repository Reality changed or revealed a constraint.
2. The interpreted requirement/spec should be revised.
3. Human Motive or governed Work should change.

External systems often allow the same agent to update specs after observing code. Watt must **ADAPT** this into a candidate finding/revision path; Executor discovery cannot silently redefine Human intent.

## 8. Brownfield Reality

OpenSpec permits starting with a new change and accumulating stable specs rather than backfilling everything. BMAD explicitly requires brownfield code investigation and project context. Agent OS discovers standards from representative code and asks Human for rationale. Spec Kit's constitution/context and extensions can help, but the default artifact pipeline is more feature-shaped than legacy-reconciliation-shaped.

Useful principle to **ABSORB**: old specs are evidence, not automatically current truth. First establish repository/runtime Reality, then reconcile. Avoid exhaustive documentation backfill without a current decision consumer.

## 9. Lineage and verification

The strongest explicit links are:

- Kiro sample: requirement → property/task.
- Spec Kit: requirement/story → task plus analysis coverage.
- OpenSpec: delta requirement/scenario → merged stable spec plus verification review.
- Tessl: spec → target file/glob and `[@test]` path.
- BMAD: spec/story → baseline diff and review.

These links improve auditability but remain fragile when they are textual, path-based, model-inferred, or detached from exact commits. None replaces Watt's exact Candidate/Verification/Runtime bindings. **ABSORB** intent-to-obligation identifiers; **ADAPT** them to immutable revisions and evidence; **REJECT** generic test-suite pass as proof of intent satisfaction.

## 10. Context strategy and future ECF relevance

Mechanisms that earn their keep:

- compact index before full load (Agent OS);
- phase/context files selected by artifact dependency (Spec Kit/OpenSpec);
- codebase scan before brownfield decisions (BMAD);
- bounded durable state separate from transcript (KiroCrew);
- existing-spec inventory before new requirements (OpenSpec/Tessl).

Risks:

- copying full standards into every spec;
- accumulating all historical specs/tasks in prompts;
- using conversation/session memory as authority;
- phase-based loading without content freshness/provenance;
- indexes that drift from source.

Future ECF should study decision-scoped selection, source revision/fingerprint, freshness, provenance, and reproducible package composition. ECF design remains **DEFER**.

## 11. Human role and structural cost

The systems correctly retain Human review, but many flows ask Humans to approve artifacts because the workflow produced them. Watt's target is Human-as-Cognitive-Governor:

- Human judgment for Motive, irreversible scope, major trade-offs, risk acceptance, and authority transfer.
- AI autonomy for repository inspection, reversible detail, consistency analysis, and bounded production.

Every document, turn, gate, and model call must justify itself through reduced ambiguity/rework/risk or improved verification. Tessl's trivial-change eval is the clearest explicit anti-bureaucracy test. BMAD's right-sizing is promising but mostly conventional rather than experimentally proven. Cost, latency, and Human cognitive load are largely absent from external evals.

## 12. Experimentability, replay, and policy

External evidence supports a bounded future architecture hypothesis:

~~~text
stable WIC capability code
+ versioned behavioral policy/workflow
+ replayable episodes
+ evaluation corpus and graders
~~~

Support:

- Spec Kit has configurable workflow/preset/extension plumbing.
- OpenSpec separates schema-defined artifact graphs from core execution.
- BMAD and Agent OS package behavior in versionable instruction/skill files.
- Tessl stores explicit cases and weighted criteria.
- KiroCrew separates deterministic checks, model A/B runs, fresh-session scenarios, and provenance-rich reports.

Likely policy candidates: question selection strategy, inference/ask threshold, pattern guidance, readiness criteria, explanation style, artifact recommendation, and escalation thresholds.

Likely capability code: identity/authority, immutable revisions, Work boundaries, persistence, security, provider transport, evidence capture, replay isolation, and invariant enforcement.

Challenges: prompt/workflow revisions lack common immutable activation attribution; model variance can dominate small samples; replayed conversations can leak expected answers; policy can become hidden architecture; and same-input output need not be deterministic.

WIC Policy/Lab remains **CANDIDATE**. Final schema, activation, rollout, and governance are **DEFER**.

## 13. Failure modes

| Failure mode | Evidence / trigger | Mitigation observed | Residual Watt concern |
|---|---|---|---|
| SPEC_DRIFT | OpenSpec scenario-loss test; Tessl seeded refactor drift | Delta validation, target/test checks, archive sync | Represented intent can still be wrong or stale. |
| DUPLICATE_TRUTH | Spec/plan/tasks/code; stable spec/change delta | Analyze/sync/review | No universal conflict authority; Watt needs owner-specific revisions. |
| FAKE_PRECISION | Fixed templates, “zero ambiguity,” generated checklists | Clarification and Human review | More fields can hide unresolved Motive uncertainty. |
| DOCUMENTATION_BUREAUCRACY | Mandatory multi-file pipelines | Trivial-change exceptions/right-sizing | Human and context cost mostly unmeasured. |
| HUMAN_APPROVAL_BUREAUCRACY | Approval per spec/checklist/standard | Selective modes and gates | Human can become a stamping service. |
| TEMPLATE_LOCK_IN | Requirements→Design→Tasks default graphs | Extensions, fluid edits | Early shape may constrain discovery and rerouting. |
| CONTEXT_BLOAT | Full standards/artifact accumulation | Indexes, scoped context, bounded ledger | Freshness and reproducible selection remain weak. |
| ONE_WAY_WATERFALL | Spec-first fixed progression | OpenSpec deltas, BMAD correction, Tessl drift | Discovery-to-governed-intent feedback remains under-specified. |
| PREMATURE_CLASSIFICATION | User-selected modes or early route | BMAD clarification; candidate patterns | No source-proven robust reroute loop across systems. |
| OVER_STRUCTURING | Full ceremony for tiny change | Tessl trivial exception; BMAD right-sizing | Proportionality policy needs evaluation. |
| UNDER_STRUCTURING | Vague prompt jumps to implementation | Gap analysis, constitution, spec gates | Gates can pass structurally while semantics remain weak. |
| STALE_SPEC_REUSE | Brownfield docs differ from code | Code inspection, delta validation, drift scan | Runtime truth and rationale may still be missing. |
| ARTIFACT_WITHOUT_CONSUMER | Workflow-generated documents | Explicit downstream context lists/links | Watt must require a named decision or verification consumer. |

## 14. Minimum Sufficient Structure decision inputs

Structure appears to earn its keep when it:

- captures a material Human decision or unresolved assumption;
- prevents scenario/constraint loss;
- selects context for a named decision;
- binds a verification obligation;
- preserves a change/revision and its rationale;
- allows fresh-session reconstruction;
- reduces downstream rework measurably.

Structure appears excessive when it:

- exists only to satisfy a fixed phase;
- duplicates another authority without reconciliation;
- requires Human approval of low-risk AI-generated detail;
- expands context without a current consumer;
- treats all work as the same depth;
- reports completion from file existence.

## 15. Watt decision inputs

### ABSORB

1. Evidence-class boundaries and pinned source attribution.
2. Delta/revision records with deterministic loss checks.
3. Read-only contradiction, ambiguity, and coverage analysis.
4. Requirement/scenario → verification-obligation linkage.
5. Brownfield Reality inspection before intent/spec promotion.
6. Trivial/proportionality cases and structural-cost measurement.
7. Replay fixtures with policy/model/source/corpus fingerprints.

### ADAPT

1. One-question refinement → highest-decision-value questioning with inference and assumption visibility.
2. Artifact DAGs → internal guidance, not Work lifecycle or Human navigation.
3. Right-sizing/patterns → tentative, reroutable, risk/ambiguity-scaled guidance.
4. Standards indexes → decision-scoped ECF candidates with freshness/provenance.
5. Spec drift repair → governed candidate revision, never silent intent rewrite.
6. Workflow configuration → versioned policy with invariant-enforcing capability code.
7. Durable session ledgers → reconstructable WIC state that remains subordinate to Work Reality.

### REJECT

1. Project/repository/spec as Work identity.
2. First-message fixed classifier and permanent workflow lock-in.
3. Universal visible Requirements→Design→Tasks workflow.
4. Artifact existence or checkbox completion as semantic readiness.
5. Executor-authored implementation facts silently becoming Human intent.
6. Repetitive Human approval of reversible technical detail.
7. Self-review or generic tests as trusted production verification.

### DEFER

1. Pattern taxonomy, persistence, blending, confidence, and UI.
2. WIC Policy schema, activation pointer, canary, and rollback design.
3. Full WIC Lab and benchmark implementation.
4. ECF and Production Execution Package integration.
5. Cross-provider production experiments and commercial policy distribution.

## 16. Open architecture questions

1. What is the smallest governed Intent/Work Frame that survives conversation without freezing discovery?
2. Which ambiguities require Human cognition, and which can be carried as explicit assumptions?
3. What semantic signal justifies a candidate Pattern, and what Reality invalidates it?
4. How should implementation discoveries propose upstream revision without gaining Goal Authority?
5. Which artifact classes have named consumers in Steering, SPG, Verification, or Human review?
6. What constitutes readiness for the next step rather than readiness for the whole Work?
7. How are policy revision, model, provider, context package, and result attributed in replay?
8. How should WIC-Bench measure Human cognitive cost, rework, over-structuring, and intent drift together?

## 17. Study conclusion

The study supports an evidence-backed direction toward Minimum Sufficient Structure, tentative pattern guidance, governed revisions, and experimentable WIC behavior. It does not authorize implementation or freeze Watt architecture.

~~~text
WIC_SDD_EXTERNAL_STUDY      COMPLETE
SOURCE_EVIDENCE             CAPTURED
MECHANISM_MATRIX            COMPLETE
BENCHMARK_LANDSCAPE         COMPLETE
ADAPTIVE_WORK_PATTERNS      STILL_CANDIDATE
WIC_POLICY_LAB              STILL_CANDIDATE
WATT_ARCHITECTURE_SYNTHESIS PENDING
WIC_SDD_IMPLEMENTATION      NOT_AUTHORIZED
~~~
