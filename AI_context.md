# AI-Native Software Production Platform

## Project Identity

- **Project:** AI-Native Software Production Platform
- **Repository:** `software-production-platform`
- **Internal Program:** TNGA Program

TNGA is an internal strategic research and development program code. It is not the repository name, package name, or external product name.

## Project Purpose

This repository is the Source of Truth for the AI-Native Software Production Platform: a platform for the full lifecycle of AI-native software production.

The platform is an AI-native Software Production System, not an AI Coding tool, ChatGPT replacement, or Coding Agent integration platform. Its objective is to build an AI-native Software Production Loop in which AI can use goals, engineering context, and governance constraints to drive planning, execution coordination, verification, feedback analysis, iteration adjustment, and baseline evolution.

## Current Stage

**Runtime Architecture Refinement — CLOSED**

Architecture Baseline remains **v0.1**. Runtime Architecture Refinement is CLOSED and Runtime Architecture Readiness is PASS. [SPG Lite Runtime Implementation Contract](docs/architecture/spg-lite-runtime-implementation-contract.md) records I1/I2/I3 CLOSED, I4 PASSED, and Coding Readiness PASS. The [FVS-1 Implementation Contract](docs/architecture/spg-fvs-1-implementation-contract.md) is ADMITTED; F3-D is CLOSED and FVS-1 is **AUTHORIZED FOR CONTROLLED IMPLEMENTATION**. S1 Runtime Foundation & Persistent Spine, S2 Governed Artifact Production, S3 Completion, Verification & Candidate Governance, S4 Repository Integration & Runtime Commit, and S5 Failure / Recovery Hardening are **CLOSED / PASS**. S6 Real Codex Dogfood & FVS Closure is **IN PROGRESS**. S6-B1 remains **CLOSED / PARTIAL**. S6-B2 Dedicated Executor & Real Provider Boundary, S6-B2-A, and S6-B2-B1 are **CLOSED / PASS** after final deterministic closure hardening. The S6-B2-B2 historical real probe remains **COMPLETE / PARTIAL** with authenticated Provider execution proven and `Provider SUCCESS + Production Reality NONE` preserved. S6-C is **NOT STARTED**.

| Architecture workflow item | Status |
|---|---|
| Runtime Flow Tabletop Exercise | CLOSED |
| Runtime Failure-Mode Discovery | CLOSED |
| Issue Discovery Scope | FROZEN |
| Runtime Architecture Refinement | CLOSED |
| A. State Foundation | CLOSED |
| A1. Core State Semantics | CLOSED — reviewed |
| A2. Transition & Commit Semantics | CLOSED — reviewed |
| A3. State Foundation Closure Review | PASSED |
| B. Reconciliation & Recovery | CLOSED |
| B1. Divergence & Recovery Semantics | CLOSED |
| B2. Execution Recovery | CLOSED |
| B3. Reconciliation & Replanning | CLOSED |
| B4. Recovery Closure | PASSED |
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
| SPG Lite Runtime — Implementation Contract / Runtime MVP Design | CLOSED |
| I1. Minimal Runtime Contract & Domain Spine | CLOSED |
| I2. State Transition & Persistence Design | CLOSED |
| I3. Capability Interfaces & End-to-End MVP Loop | CLOSED |
| I4. Coding Readiness Closure | PASSED |
| Coding Readiness | PASS |
| Implementation Governance | AUTHORIZED FOR CONTROLLED IMPLEMENTATION |
| FVS-1 Implementation Contract | ADMITTED |
| F1. Slice Goal & Governance Contract | REVIEWED / ADMITTED |
| F2. Minimal Technical Foundation | REVIEWED / ADMITTED |
| F3-A. Runtime Slice Boundary & Physical Spine | REVIEWED / ADMITTED |
| F3-B. Repository Integration / Commit Semantics | REVIEWED / ADMITTED |
| F3-C. Executable Test & Failure Contract | REVIEWED / ADMITTED |
| F3-D. FVS Coding Authorization Closure | CLOSED — FVS-1 AUTHORIZED FOR CONTROLLED IMPLEMENTATION |
| S1 — Runtime Foundation & Persistent Spine | CLOSED / PASS |
| S1-A. Runtime Project Foundation | CLOSED / PASS |
| S1-B. Persistent Runtime Foundation | CLOSED / PASS |
| S1-C. Bootstrap Baseline & Minimal Durable Runtime Spine | CLOSED / PASS |
| S2 — Governed Artifact Production | CLOSED / PASS |
| S2-A — Context & Execution Preparation Foundation | CLOSED / PASS |
| S2-B — Isolated Execution & Independent Artifact Observation | CLOSED / PASS |
| S3 — Completion, Verification & Candidate Governance | CLOSED / PASS |
| S3-A — Completion Evaluation & Produced Semantics | CLOSED / PASS |
| S3-B — Verification Qualification & Satisfaction | CLOSED / PASS |
| S3-C — Candidate Sealing & Human Governance | CLOSED / PASS |
| S4 — Repository Integration & Runtime Commit | CLOSED / PASS |
| S4-A — Authorized Repository Integration | CLOSED / PASS |
| S4-B — Runtime Commit | CLOSED / PASS |
| S5 — Failure / Recovery Hardening | CLOSED / PASS |
| S5-A — Recovery Classification & Reconciliation Foundation | CLOSED / PASS |
| S5-B — Repository Integration & Runtime Commit Reconciliation | CLOSED / PASS |
| S5-C — Execution Attempt & Workspace Recovery Hardening | CLOSED / PASS |
| S6 — Real Codex Dogfood & FVS Closure | IN PROGRESS |
| S6-B1 — Real Codex SDK Host Integration Spike | CLOSED / PARTIAL |
| S6-B1-R — Provider Terminal & Identity Correlation Spike | PARTIAL — LIFECYCLE CAPABILITY PROVEN / DURABLE REAL EVIDENCE INCOMPLETE |
| S6-B1-R2 — Durable Provider Evidence Capture Hardening | CLOSED / PASS |
| S6-B2 — Dedicated Executor & Real Provider Boundary | CLOSED / PASS |
| S6-B2-A — Dedicated Executor Boundary Deterministic Spike | CLOSED / PASS |
| S6-B2-B1 — Codex Adapter Binding & Authentication Boundary Preflight | CLOSED / PASS |
| S6-B2-B2 Historical Real Probe — Single Real Codex Through Dedicated Executor Boundary | COMPLETE / PARTIAL |

The [FVS-1 Implementation Contract](docs/architecture/spg-fvs-1-implementation-contract.md#54-s6-b1-real-codex-sdk-host-integration-spike-reality) records the bounded S6-B1 Reality and its S6-B1-R/R2 follow-ups. Historical probes remain immutable. **No additional S6-B1 or S6-B2-B2 real Provider probe is authorized**. S6-B2 is **CLOSED / PASS** after deterministic closure hardening: provider neutrality is now asserted from the governed request structure, unauthorized Provider/credential fields are rejected by the closed transport model, B2CLOSE-01–08 pass, the complete B2 deterministic module passes 38/38 with its real test deselected, affected S6-B1/R/R2 tests pass 45/45 with their real test deselected, and the current-tree deterministic regression passes 428/428 with two real tests deselected. The historical B2-B2 probe remains **COMPLETE / PARTIAL** and still records the exact benchmark `Provider SUCCESS + Production Reality NONE`; it is not relabeled. S6-C is not started.

The completed refinement order is **A. State Foundation → B. Reconciliation & Recovery → C. Completion & Trust → D. Side-effect Governance → Final Readiness Review**. Runtime Failure Discovery remains CLOSED and its 12-area scope remains frozen; reopen it only when implementation, dogfood, or Reality Check evidence requires it.

The [Runtime Findings Review](docs/architecture/spg-runtime-findings-review.md) preserves the frozen discovery scope. [State Foundation](docs/architecture/spg-state-foundation.md), [Reconciliation & Recovery](docs/architecture/spg-reconciliation-recovery.md), [Completion & Trust](docs/architecture/spg-completion-trust.md), and [Side-effect Governance](docs/architecture/spg-side-effect-governance.md) preserve the closed A/B/C/D semantics and their respective 20-invariant sets. The broader [Runtime Verification and Benchmark Strategy](docs/architecture/spg-runtime-verification-benchmarks.md) remains future work; FVS-1 now admits only its bounded T01–T18 and 12/12 executable obligations, which are not yet implemented or passed. Architecture readiness means enough semantics are stable for the next governed iteration, not that all future architecture or implementation is complete.

## Program-level Architecture Source of Truth

The current system-level architecture baseline is:

- [AI Native Software Production System Architecture Baseline v0.1](docs/architecture/system-architecture-baseline-v0.1.md)
- [SPG Lite Domain Model and Contract Boundary Baseline](docs/architecture/spg-lite-domain-contract-baseline.md)
- [SPG Runtime Architecture Final Closure and Readiness](docs/architecture/spg-runtime-architecture-readiness.md)
- [SPG Lite Runtime Implementation Contract](docs/architecture/spg-lite-runtime-implementation-contract.md)
- [Runtime Profile, Provider Placement, and Containerized Deployment](docs/architecture/runtime-profile-provider-deployment.md)
- [SPG FVS-1 — Governed Documentation Production Loop Implementation Contract](docs/architecture/spg-fvs-1-implementation-contract.md)

The system baseline governs mission and system boundaries. The SPG Lite baseline consolidates the current SPG domain objects and capability contracts under those boundaries. Detailed documents refine their own scope without silently changing these program-level decisions.

## Core Principles

- Human Agency First — meaningful Human authority, not unrestricted runtime privilege
- Human Authority Does Not Imply Runtime Bypass
- Governed Participants — shared governance rules, different Responsibility / Authority
- No Actor Owns Production Truth Alone
- Distributed Responsibility, Governed Adjudication — not majority voting
- Provider Consolidation Does Not Collapse Authority Boundaries
- Replaceable Intelligence, Durable Governance
- One Product Architecture, Multiple Runtime Profiles
- Provider / Model Selection Is Configuration, Not Domain Logic
- Model Provider and Executor Provider Are Distinct
- Containerization Is Packaging / Infrastructure, Not Domain Semantics
- Context before Execution
- Evidence before Acceptance
- Completion Semantics Are Layered
- Validity Is Relational
- Trust Is Obligation Satisfaction Before It Is a Score
- Execution Capability Does Not Imply Side-effect Authority
- Observed External Reality Does Not Automatically Become Trusted Reality
- Governed Integration Atomicity over Assumed Physical Atomicity
- Role over Agent
- Executor Independence
- Platform Capability over Application Duplication
- Capability Contract Before Capability Implementation
- Dependency Direction Follows Capability Ownership
- Production Work Unit Generalization
- Ownership Before Integration
- Generated Does Not Equal Trusted
- Contract Before Implementation
- Source of Truth over Conversation History
- Conversation-to-Contract — raw conversation is never authoritative execution input
- Controlled Autonomy
- AI Capability Evolution Independence

## Current Major Components

The future platform will form a system with the following capabilities:

- Consumer Projects, for example 易决
- Guardian — Engineering Assurance System
- Engineering Context Fabric

This document describes their relationship only; it does not define their internal subsystem designs.


## Origin and MVP Goal

The current design originates from real ChatGPT + Codex collaboration practice. The MVP goal is not to copy that workflow into a new platform; it is to validate a minimum AI-native Software Production Loop for real projects.

The MVP prioritizes running the production loop, serving real projects, accumulating engineering data, and validating AI-driven research and development. The long-term direction may evolve toward an AI Software Production Operating System.


## Formal Platform Positioning

The platform is not an AI Coding tool, a ChatGPT replacement, or a simple model API integration layer. It is an AI-native Software Production System that treats AI as a core production capability and first-class production factor, while organizing human intent, engineering judgment, and machine intelligence into a governed, verifiable, and continuously evolving system.

The long-term challenge is to organize intelligence for complex software production, not merely to make AI smarter or call stronger models. The current MVP remains limited to rapid validation, real internal projects, small-step iteration, and experimentation.

## Core Positioning Principle

Human defines intent. AI amplifies capability. System ensures trust.

The platform's first-class abstraction is Role, not Agent. Its core concerns are Responsibility, Authority, Context, Artifact, and Gate.
