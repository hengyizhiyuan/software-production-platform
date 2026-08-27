# SPG Completion & Trust Closure

- **Record date:** 2026-08-27
- **Status:** C. Completion & Trust — CLOSED
- **Sub-review status:** C1 / C2 / C3 — CLOSED; C4 Closure Review — PASSED
- **Governing architecture:** [Architecture Baseline v0.1](system-architecture-baseline-v0.1.md)
- **Prior layers:** [A. State Foundation](spg-state-foundation.md) and [B. Reconciliation & Recovery](spg-reconciliation-recovery.md)
- **Scope:** Confirmed logical Runtime, Contract, trust, and authority semantics; not implementation design

This document records the supplied C closure under Architecture Baseline **v0.1**. The subsequent [D Side-effect Governance closure](spg-side-effect-governance.md) is CLOSED (D1/D2/D3 CLOSED; D4 PASSED). The [Final Closure and Readiness Review](spg-runtime-architecture-readiness.md) is PASSED; Runtime Architecture Refinement is CLOSED and Runtime Architecture Readiness is PASS.

## 1. C1 — Layered Completion Semantics

### Completion remains layered

```text
Execution Attempt Finished
        !=
Work Product Produced
        !=
PWU Satisfied
        !=
Production Plan Complete
        !=
Trusted Completion
        !=
Committed Trusted Production Change
```

**Confirmed Runtime Principle:** Completion semantics must remain layered. A generic `completed = true` flag cannot substitute for execution, production, verification, trust, authorization, and Commit semantics.

### Execution Attempt completion

A successfully finished Execution Attempt establishes only the result of that specific attempt. It does not establish correct task identity, required artifact production, PWU Satisfaction, Verification success, Trusted Completion, or Commit Eligibility.

Executor self-report is an input fact. It is not authoritative PWU completion and cannot directly mutate production state.

### Produced versus Satisfied

- **Produced:** the required Work Product outputs defined by the PWU have been produced.
- **Satisfied:** the full PWU Completion Contract has been satisfied.

```text
Required code artifact       produced
Required test artifact       produced
Verification                 failed

PWU Produced                 YES
PWU Satisfied                NO
```

Produced and Satisfied are distinct semantics.

## 2. Output Obligation Manifest — Confirmed Runtime Semantic

> Output Obligation Manifest is a governed description of the production outputs a PWU is expected to produce.

**Artifact Manifest** was the earlier working term. **Output Obligation Manifest** is the preferred term because the concept represents production-output obligations, not merely a list of changed files.

At minimum, the logical obligation classes are:

| Obligation | Meaning | Example |
|---|---|---|
| REQUIRED | Absence prevents PWU Satisfaction | Code Artifact; Test Artifact |
| CONDITIONAL | Required when its governed condition applies | Migration Artifact when schema changes |
| OPTIONAL | Absence does not by itself block Satisfaction | Performance analysis report |

This is confirmed semantic structure, not a DSL, schema, or file-discovery implementation.

### Partial production

Partial production preserves valid Work Product Artifacts without falsely satisfying the PWU.

```text
Code           produced
Tests          produced
Migration      missing
Documentation  produced
```

The produced artifacts remain production history. If a required obligation is missing, the PWU remains unsatisfied. Partial production should not be collapsed into generic failure when more precise semantics exist.

## 3. Completion Contracts — Confirmed Contract Semantics

### PWU Completion Contract

> PWU Completion Contract is the governed, versioned definition of what must be true for a PWU to be Satisfied.

Its logical contents include:

1. Output Obligations.
2. Verification Obligations.
3. Required Conditions.
4. Blocking Conditions.

```text
Produced outputs
+ Required verification satisfied
+ Required conditions satisfied
+ No blocking condition
        ↓
PWU SATISFIED
```

Production Governance Runtime adjudicates Satisfaction against the Contract using domain-owned facts and Evidence. Executor self-report cannot establish Satisfaction.

### Completion is defined before it is claimed

Before an executable PWU begins, sufficiently explicit completion obligations must exist. Definition of Done cannot be weakened after the fact merely to match incomplete output.

### Completion Contract versioning

Material changes to Completion Contract semantics must be explicit, governed, versioned, and historically preserved. A Contract must not be silently overwritten after execution begins. Material changes may require existing outputs or Verification Evidence to be reassessed against C2 freshness semantics.

The representation, storage model, and versioning mechanism are not selected here.

### Plan Completion Contract

Production Plan completion is governed by Plan-level completion semantics, not by every task row appearing green.

A Plan Completion Contract may logically include:

- Required PWUs.
- Required Work Product classes.
- Required integration conditions.
- Required Verification coverage.
- No unresolved blocking Production Issues.

This confirms Contract semantics without defining a physical schema.

### Production Completion Candidate boundary

Production completion produces a candidate result that may enter trust evaluation. The semantic boundary is confirmed; a permanent first-class **Production Completion Candidate** entity is not.

Possible future representations remain:

```text
Plan Complete → Baseline Candidate
```

or:

```text
Production Completion Candidate → Sealing → Baseline Candidate
```

The object model remains deferred.

### Production Completion versus Business Outcome

Production Completion is distinct from Business Outcome Achievement. SPG may complete a software production objective while the real-world business result remains unknown or later proves disappointing. Later outcome measurement does not retroactively redefine whether production obligations were completed.

## 4. C2 — Verification Basis and Evidence

### Verification Basis — Confirmed Runtime Semantic

Every Verification Result and usable Evidence item is scoped to an explicit Verification Basis. The logical basis may include:

- Verification Subject.
- Subject Revision.
- Verification Scope.
- Source Baseline.
- Relevant dependencies.
- Environment / toolchain.
- Verification Method.
- Verification Requirement / Policy revision.
- Timestamp / observed time.

> Verification PASS is scoped and contextual, not timeless truth.

This list is semantic, not a frozen Evidence schema.

### Verification Artifact versus Verification Evidence

- **Verification Artifact:** raw output of verification activity, such as a test result, coverage report, static-analysis report, or runtime observation.
- **Verification Evidence:** governed evidence interpreted and qualified for use in production trust decisions.

Guardian / Verification Capability owns assurance truth, Evidence interpretation, Findings, Qualification, Gate results, and assurance confidence / coverage semantics. SPG consumes Evidence through contracts and governs its use in state-transition eligibility. SPG must not independently reinterpret raw Verification Artifacts into assurance truth.

### Evidence is relational

> Evidence is contextual proof, not a permanent property of an Artifact.

```text
Artifact / Subject
+ Revision
+ Baseline
+ Dependencies
+ Environment
+ Requirement
+ Method
+ Scope
        ↓
Evidence
```

Semantics equivalent to `artifact.verified = true forever` are invalid.

## 5. Evidence Freshness — Confirmed Runtime Semantic

The logical freshness conclusions are:

| Freshness conclusion | Meaning |
|---|---|
| VALID | Evidence remains sufficient for the current production reality |
| REVALIDATION_REQUIRED | Relevant reality changed and impact is not yet safely determined |
| INVALIDATED | Material assumptions required by the Evidence are no longer valid |

These are logical conclusions, not frozen database enums.

INVALIDATED does not mean historical verification was incorrect. It means prior Evidence is no longer sufficient for the current claim.

Evidence may require revalidation or invalidation after material change to its Subject, Subject Revision, relevant dependency, Trusted Production Baseline, Contract / requirement, environment / runtime, toolchain, Verification Method, or Verification Policy.

**Baseline advancement triggers impact evaluation, not automatic global Evidence invalidation.** Preserve the maximum amount of still-valid Evidence through explicit relevant dependency relationships. No Evidence dependency graph is implemented or required by this closure.

### Evidence Quality versus Evidence Freshness

Evidence Quality and Evidence Freshness are separate dimensions. Evidence may be high-quality but stale, or fresh with weak coverage. They must not collapse into one generic score.

### Verification coverage

Verification obligations are scoped coverage obligations, not one `verified = true` Boolean.

```text
Functional Verification     PASS
Regression Verification     PASS
Security Verification       PENDING
```

Advancement depends on the applicable Completion / Trust Contract. This closure does not define a full coverage ontology.

### Evidence scope and provenance

Usable Evidence preserves enough provenance to answer:

- Who or what produced it?
- What was verified?
- Which subject revision?
- Which Baseline / Context?
- Which method and environment?
- Which requirement?
- Which supporting Verification Artifacts?
- Which claim and scope does it support?

Evidence must support the actual Completion or Trust obligation claimed, not merely something measurable.

## 6. Logical Verification Independence

Logical independence matters even when execution and verification use the same physical model or provider. The same provider may supply both capabilities, but the system preserves distinct Responsibility, Contract, provenance, assurance scope, and policy treatment.

Policy may require additional independent Verification for higher-risk changes. This extends **Provider Consolidation Does Not Collapse Authority Boundaries** without requiring a different physical provider for every role. Provider-independence scoring is deferred.

Human Review may contribute Evidence, an Authority Decision, or both, depending on context. A Human product review may establish product-behavior acceptance; it does not automatically establish security, performance, or regression assurance. Human Review semantics must remain scoped.

## 7. C3 — Production Completion to Trusted Completion

### Production Completion does not imply Trusted Completion

- **Production Completion:** planned production obligations are fulfilled.
- **Trusted Completion:** the exact governed candidate satisfies all required completion, verification, Evidence freshness / admissibility, policy gate, Authority, and blocking-condition obligations.

### Exact Baseline Candidate is the trust target

Final Trust / Acceptance targets an exact sealed Baseline Candidate revision. Authorization of `BC-38/R2` does not authorize materially changed `BC-38/R3`.

This preserves A's exact Candidate and Commit semantics.

## 8. Commit Eligibility and Commit Authorization

### Commit Eligibility

A Production Governance Runtime conclusion that the exact Candidate satisfies required objective production conditions. Inputs may include Completion Contract satisfaction, required Evidence, Evidence freshness, lineage completeness, blocking Production Issues, Hard Gates, and Candidate validity.

### Commit Authorization

A governance / Authority conclusion that the exact Candidate has permission to become Trusted Production Reality. Inputs may include Human Decision Records, policy-based automatic authorization, risk acceptance, exception authorization, and domain-specific Authority.

**Commit Eligibility ≠ Commit Authorization.** Both must be satisfied according to governance policy before Commit.

### Policy-driven Human Final Acceptance

Human Final Acceptance is an Authority Policy option, not a universally mandatory Runtime step.

- A high-risk architecture change may require Human Authority.
- A low-risk documentation change may be auto-authorized by policy.

The stable rule is: **Required Authority must be satisfied.**

Human Agency First means Humans define and retain authority boundaries; it does not mean Humans manually approve every production action.

### Authority Requirements

A Baseline Candidate may carry explicit Authority Requirements determined by governance policy, risk, scope, and impact. They may include Product Scope Authority, Architecture Authority, Security / Risk Authority, Final Production Acceptance, or other domain-specific Authority.

This is a confirmed semantic concept, not a generalized approval engine.

## 9. Risk Acceptance and Governed Exception

### Risk Acceptance

Risk Acceptance changes governance permission, not observed facts or Evidence.

A present Guardian Finding and Security Risk remain present when an authorized Human accepts the risk. Policy may then permit an exception and Commit Authorization may become satisfied. The Finding must not be rewritten as PASS.

### Exception

> Exception is an explicit governed path for proceeding when a normal governance obligation is not satisfied but policy permits an authorized deviation.

An Exception conceptually identifies:

- The exact obligation waived or substituted.
- The applicable Candidate.
- Authorized actor / authority domain.
- Rationale and scope.
- Freshness / validity.
- Follow-up obligation, when applicable.

Exception is itself governed. Human Authority must not become a hidden Runtime bypass.

Risk Acceptance is explicit acceptance of a known risk. Exception is the broader governed deviation from a normal rule or obligation. Risk Acceptance may be an Authority input to an Exception; the two are not synonymous.

### Authorization / Acceptance freshness

Authority decisions are scoped to governed reality. They may become stale when the exact Candidate, Policy, or material basis changes.

```text
Human accepts BC/R2
        ↓
Candidate materially changes
        ↓
BC/R3
```

The old Acceptance does not automatically apply. Future Materiality / Policy rules may permit explicit carry-forward; it must never be silently assumed.

## 10. Trust Semantics

### Trust Is Obligation Satisfaction Before It Is a Score

```text
Required Completion Obligations       satisfied
Required Verification Obligations     satisfied
Evidence Freshness                    valid
Hard Gates                            satisfied / authorized exception
Required Authorities                  satisfied
Blocking Production Issues            absent / resolved
        ↓
Trusted Completion
```

Trusted Completion primarily means required obligations are satisfied. A future confidence or Trust Score may support prioritization, Human decision support, additional Verification selection, or Autonomy Policy. It cannot replace hard governance contracts or become the authoritative gate.

### Hard Gates versus Soft Signals

- **Hard Gate:** blocks Commit Eligibility unless an explicitly governed Exception path is allowed.
- **Soft Signal:** may influence confidence, risk visibility, Verification intensity, Human review priority, autonomy, or routing; it does not automatically block Commit.

No score, weighting, or Trust aggregation system is selected.

### Trusted Completion

> Trusted Completion is the governed state in which an exact Baseline Candidate satisfies all required Completion, Verification, Policy, and Authority obligations and is eligible and authorized to proceed to Commit according to Runtime governance.

Trusted Completion is not itself the new Trusted Production Baseline.

```text
Production Complete
        ↓
Trusted Completion
        ↓
Commit
        ↓
Trusted Production Change
        ↓
New Trusted Production Baseline
```

Only successful Commit changes Trusted Production Reality.

## 11. Validity Is Relational

**Confirmed Architecture Principle:**

> Validity is not a permanent intrinsic property carried by an object. It is a governed conclusion that holds relative to specific production reality, versions, Context, dependencies, policies, and constraints.

Examples:

| Validity conclusion | Relative basis |
|---|---|
| PWU Validity | Production Validity Basis |
| Evidence Freshness | Verification Basis |
| Authority Decision Validity | Exact Candidate / Policy |
| Commit Eligibility | Current Baseline and required obligations |

This extends A's exact-revision semantics and B's Production Validity Basis. It rejects permanent-state anti-patterns such as `verified = true forever`, `approved = true forever`, `accepted = true forever`, and `valid = true forever`.

## 12. Distributed Governance and Ownership

**No Actor Owns Production Truth Alone.**

| Participant | C-layer contribution |
|---|---|
| Executor | Execution facts and Work Products |
| Guardian / Verification | Evidence, Findings, Qualification, assurance truth |
| Human / Domain Authorities | Authorized decisions, risk acceptance, scope decisions |
| Production Governance Runtime | Adjudicates whether obligations permit authoritative state transition |

Runtime is not creator or owner of all facts. Guardian cannot Commit. Executor cannot self-complete a PWU. Human Authority cannot rewrite failed Evidence into PASS. No super-model may bypass Contract or Authority boundaries.

### SPG / Guardian ownership

SPG owns:

- Required Verification obligations.
- State-transition eligibility.
- Candidate freshness / admissibility use.
- Completion Contracts.
- Policy / Authority requirement coordination.
- Commit governance.

Guardian / Verification owns:

- Evidence interpretation.
- Findings.
- Assurance truth.
- Qualification.
- Gate result.
- Assurance confidence / coverage semantics.

SPG does not reinterpret raw Verification Artifacts into assurance truth. Guardian does not mutate SPG production state directly.

## 13. MVP Complexity Boundary

These C-layer semantics do not require SPG Lite MVP to implement:

- Trust Graph.
- Generalized Evidence ontology.
- Policy DSL.
- Full Guardian.
- Complex multi-authority approval engine.
- Cryptographic provenance.
- Generalized dependency graph.
- Automatic semantic Materiality engine.
- Full Verification orchestration.
- Trust-scoring system.

SPG Lite may use ordinary persistent records, Git references, and simple explicit Completion, Verification, and Authorization fields while preserving the architecture semantics.

> Architecture semantics strong; MVP mechanisms simple.

## 14. Deferred Mechanisms

The following remain deferred and are not completed architecture, current capabilities, or MVP commitments:

- Trust Score / confidence aggregation algorithm.
- Full Evidence schema / ontology.
- Guardian Gate implementation.
- Policy DSL.
- Exception workflow engine.
- Multi-authority quorum mechanics.
- Approval UI.
- Evidence dependency graph engine.
- Automatic Materiality reasoning.
- Provider-independence scoring.
- Full Verification orchestration.
- Adaptive Trust policy implementation.
- Production Completion Candidate physical/domain representation.
- Output Obligation Manifest DSL or schema.
- PWU / Plan Completion Contract physical schema.

## 15. C-Level Invariants — CLOSED

### Completion

1. Execution Attempt completion does not imply PWU completion.
2. Produced and Satisfied are distinct production semantics.
3. Expected production outputs are governed by explicit output obligations.
4. PWU Satisfaction is determined by a versioned Completion Contract.
5. Executor self-report cannot establish PWU Satisfaction.
6. Partial production preserves valid Work Product Artifacts without falsely satisfying the PWU.
7. Production Completion and Business Outcome Achievement are distinct.

### Verification

8. Verification PASS is scoped to an explicit Verification Basis.
9. Evidence is contextual proof, not a permanent property of an Artifact.
10. Evidence Quality and Evidence Freshness are distinct.
11. Material change may require Evidence revalidation or invalidate prior Evidence.
12. Baseline advancement triggers impact evaluation, not global Evidence invalidation.
13. Verification obligations are coverage obligations rather than one generic Boolean.
14. Evidence must have explicit scope and provenance.

### Trust / Authority

15. Production Completion does not imply Trusted Completion.
16. Trusted Completion targets an exact governed Baseline Candidate.
17. Commit Eligibility and Commit Authorization are distinct.
18. Trust is primarily established through satisfied obligations, not an opaque score.
19. Risk Acceptance / Exception may change governance permission but cannot rewrite Evidence or production facts.
20. Only successful Commit turns Trusted Completion into new Trusted Production Reality.

## 16. Closure Review Result

The supplied C4 review result is **PASSED** across Completion semantics, Output Obligation semantics, Completion Contracts, partial production, Plan completion, Verification scope, Evidence provenance and freshness, Evidence Quality / Freshness separation, B-level staleness interaction, Guardian ownership, Authority, Risk Acceptance, Exception, Human Agency, distributed governance, exact Candidate Acceptance, A-level Commit compatibility, provider independence, and MVP complexity control.

This is architecture closure, not implementation or test completion.

## 17. Runtime Architecture State and Next Step

| Runtime Architecture Refinement item | Status |
|---|---|
| A. State Foundation | CLOSED |
| B. Reconciliation & Recovery | CLOSED |
| C. Completion & Trust | CLOSED |
| C1. Completion Semantics | CLOSED — reviewed |
| C2. Verification & Trust Freshness | CLOSED — reviewed |
| C3. Acceptance & Trusted Completion | CLOSED — reviewed |
| C4. Completion & Trust Closure | PASSED |
| D. Side-effect Governance | CLOSED |
| D1. Side-effect Semantics & Boundary | CLOSED — reviewed |
| D2. Side-effect Authority & Execution Safety | CLOSED — reviewed |
| D3. Compensation & External Reality | CLOSED — reviewed |
| D4. Side-effect Governance Closure | PASSED |
| Final Closure / Architecture Readiness Review | PASSED |
| Runtime Architecture Readiness | PASS |

The subsequently admitted [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md) is CLOSED with Coding Readiness PASS. The [FVS-1 Contract](spg-fvs-1-implementation-contract.md) records F3-D CLOSED, but S1-A implements no Completion, Verification, Candidate, or Trusted Baseline behavior. The FVS executable proof remains not implemented or passed.

The Final Review and Implementation Contract preserve C's semantics and all 20 C-level invariants. The original discovery scope remains FROZEN. This C-closure record did not itself design or implement schemas, APIs, tests, or code.
