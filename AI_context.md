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

**Runtime Architecture Refinement — IN PROGRESS**

Architecture Baseline remains **v0.1**. A. State Foundation is CLOSED: A1 / A2 are CLOSED; A3 Closure Review PASSED. B. Reconciliation & Recovery is CLOSED: B1 / B2 / B3 are CLOSED; B4 Recovery Closure PASSED. These are supplied architecture review conclusions, not implemented capabilities or newly executed Runtime tests.

| Architecture workflow item | Status |
|---|---|
| Runtime Flow Tabletop Exercise | CLOSED |
| Runtime Failure-Mode Discovery | CLOSED |
| Issue Discovery Scope | FROZEN |
| Runtime Architecture Refinement | IN PROGRESS |
| A. State Foundation | CLOSED |
| A1. Core State Semantics | CLOSED — reviewed |
| A2. Transition & Commit Semantics | CLOSED — reviewed |
| A3. State Foundation Closure Review | PASSED |
| B. Reconciliation & Recovery | CLOSED |
| B1. Divergence & Recovery Semantics | CLOSED |
| B2. Execution Recovery | CLOSED |
| B3. Reconciliation & Replanning | CLOSED |
| B4. Recovery Closure | PASSED |
| C. Completion & Trust | NEXT — NOT STARTED |
| D. Side-effect Governance | NOT STARTED |
| NEXT | C. Completion & Trust |

The next valid design transition is exactly **Runtime Architecture Refinement → C. Completion & Trust**. A generic instruction such as "continue" resolves to this transition, not coding, database schema, API design, runtime implementation, Runtime Flow expansion, or Coding Readiness Review. C is NEXT but NOT STARTED; this B-closure documentation task does not begin C or D.

Refinement proceeds in order: **A. State Foundation → B. Reconciliation & Recovery → C. Completion & Trust → D. Side-effect Governance**. The 12-area discovery scope is frozen; reopen discovery only when real new evidence requires it.

The [Runtime Findings Review](docs/architecture/spg-runtime-findings-review.md) records findings and the remaining agenda. The [State Foundation Closure](docs/architecture/spg-state-foundation.md) preserves 20 A-level invariants. The [Reconciliation & Recovery Closure](docs/architecture/spg-reconciliation-recovery.md) records confirmed B semantics and all 20 B-level principles, including Execution Lease, fencing, isolation, validity, and Recovery Barrier. These are logical semantics, not selected infrastructure mechanisms. The [Runtime Verification and Benchmark Strategy](docs/architecture/spg-runtime-verification-benchmarks.md) records future verification requirements and benchmark candidates, not implemented tests. Other explicitly labeled candidates and detailed C/D questions remain unresolved.

## Program-level Architecture Source of Truth

The current system-level architecture baseline is:

- [AI Native Software Production System Architecture Baseline v0.1](docs/architecture/system-architecture-baseline-v0.1.md)
- [SPG Lite Domain Model and Contract Boundary Baseline](docs/architecture/spg-lite-domain-contract-baseline.md)

The system baseline governs mission and system boundaries. The SPG Lite baseline consolidates the current SPG domain objects and capability contracts under those boundaries. Detailed documents refine their own scope without silently changing these program-level decisions.

## Core Principles

- Human Agency First — meaningful Human authority, not unrestricted runtime privilege
- Human Authority Does Not Imply Runtime Bypass
- Governed Participants — shared governance rules, different Responsibility / Authority
- No Actor Owns Production Truth Alone
- Distributed Responsibility, Governed Adjudication — not majority voting
- Provider Consolidation Does Not Collapse Authority Boundaries
- Replaceable Intelligence, Durable Governance
- Context before Execution
- Evidence before Acceptance
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
