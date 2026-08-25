# MVP Architecture

The current SPG Lite domain objects and logical capability contracts are consolidated in [SPG Lite Domain Model and Contract Boundary Baseline](spg-lite-domain-contract-baseline.md). That baseline guides semantic alignment; it does not add MVP modules, APIs, schemas, or integrations.

This document records the intended MVP architecture. It is an architecture baseline, not a runtime implementation specification.

## Continuous Engineering Iteration Loop

The MVP is organized around the AI-native Software Production Loop, a continuous feedback-driven loop:

```text
Human Intent → Production Planner → Planning / VS / Task Generation
    → Executor → Workspace Execution → Verification → Reality Feedback
    → Design Refinement → Next Iteration
```

Design is not permanently frozen after development starts. Implementation feedback can challenge design assumptions, and verification can trigger design refinement. Human intervention focuses on important decisions rather than every execution step.


## Origin and MVP Goal

### Origin

The MVP design originates from real ChatGPT + Codex collaboration practice. That practice exposed context synchronization, manual task orchestration, multi-environment execution state, and the separation between AI execution and engineering governance.

### MVP Goal

The MVP is not defined as moving ChatGPT + Codex into a new platform. Its goal is to build a minimum viable AI-native Software Production Loop in which AI can, based on project goals, perform planning, task decomposition, execution coordination, result verification, and iteration advancement.

The MVP validates whether:

- AI can drive the engineering rhythm
- AI can continuously understand project state
- AI can adjust the next path based on execution results
- Humans can move from executors to governors

## Production Planner: MVP Intelligence Mode

The MVP uses **Single Intelligence Mode**:

```text
Human Goal
    ↓
Production Planner
    ↓
Design / Planning / Task Decomposition
    ↓
Execution Loop
```

This mode exists to quickly validate the AI-native software production loop. It does not define Production Planner as a permanently fixed super Agent.
## Engineering Hierarchy

```text
Project
└── Capability / Feature
    └── Vertical Slice (VS)
        └── Task
            └── Execution Unit
                └── Executor Run
```

### Vertical Slice (VS)

A VS is a minimum independently verifiable value delivery unit. It is not the smallest execution unit and should contain enough scope to validate a complete capability.

### Task

A Task is a meaningful engineering decomposition unit inside a VS.

### Execution Unit

An Execution Unit is the smallest unit directly assigned to an Executor: a specific authorized execution action with clear input and expected output. Typical input includes a Task Contract, Context, and Workspace. Typical output includes a code change, execution result, logs, and verification information.

## Engineering Iteration

The current ChatGPT + Codex collaboration pattern is abstracted as:

```text
Reasoning → Generate Execution Instruction → Executor Run
    → Result Feedback → Evaluation → Continue or Correct
```

An Iteration is one complete production cycle in which AI understands the goal, plans, executes, observes, reflects, and adjusts the path until it approaches a trusted target state. It is distinct from the VS lifecycle, Task lifecycle, and code lifecycle.

## MVP Core Components

### Role Runtime

Supports AI roles participating in software production. The initial role is Production Planner; the architecture permits future Product AI, Architecture AI, QA AI, and DevOps AI roles.

### Production Planner

Production Planner is the SPG capability responsible for transforming approved production intent into adaptive software production blueprints and production plans. It is not Production Planner AI: AI is only one possible implementation approach.

It is responsible for:

- Understanding project goals and long-term direction
- Maintaining the overall design intent
- Understanding capability boundaries and architecture constraints
- Tracking key design decisions
- Judging whether a Task or change has deviated from approved goals
- Driving the Design → Implementation → Verification loop

Its authority is expressed through:

- Why
- What
- Direction
- Boundary

It does not:

- Preserve all code-level details
- Replace the Coding Executor
- Replace Guardian
- Become the sole source of truth

It remains a governed engineering role, not a generic chatbot.


### Production Planner Responsibilities

#### Blueprint Generation

Generates a Software Production Blueprint containing:

- Architecture Impact
- Value Slice
- Work Breakdown
- Required Capability
- Verification Strategy
- Risk Boundary

#### Production Plan Generation

Transforms:

```text
Software Production Blueprint → Production Plan → Iteration → Work Item
```

#### Plan Adaptation

Adapts the plan based on production reality:

```text
Execution Evidence → Impact Analysis → Plan Update
```

Production Planner does not own Business Decision, Product Strategy, Value Judgment, whether a product should exist, or General Decision Intelligence.
### Context Layer

Provides lightweight context management for project understanding, current baseline, important decisions, documentation references, and historical artifacts. It uses a Context Provider abstraction so roles do not remain permanently coupled to raw files. Future ECF integration is reserved but not implemented here.

### Workflow / Iteration Engine

Manages lifecycle states, drives iteration loops, tracks transitions, and permits returning to previous states. It does not enforce rigid waterfall stages; verification may lead to a design challenge, design refinement, and re-execution.


### Engineering State Management

Engineering State Management is AI-native software production state awareness and governance capability. It is not traditional Project Management, a Gantt chart maintenance tool, a static plan tracking tool, or a system for manually entering progress.

Its purpose is to keep the Human Governor and AI Production System aware of:

- The project's current real state
- What is currently happening
- Which capabilities are complete
- Which Tasks are executing
- Which issues block progress
- What should happen next

The MVP provides a minimum viable software production state view across:

- Project state
- Capability / Module state
- Vertical Slice state
- Work Item state
- Execution state
- Current work in progress
- Basic progress presentation

This state view supports understanding and governance; it does not introduce AI delay prediction, automatic resource optimization, enterprise Portfolio management, complex portfolio analysis, or advanced production economics analysis.
### Task / VS Management

Maintains VSs, Tasks, execution status, and associated artifacts. This is engineering production state management, not traditional project management.

### Executor Framework

Provides a unified, pool-based execution abstraction. The MVP may use one executor instance; the architecture remains open to multiple Codex instances, models, and execution providers.

### Development Workspace

Provides repository management, code checkout, environment preparation, command execution, and result collection. Executor and workspace lifecycles remain separate.

### Verification Framework

Provides a lightweight feedback loop—not full CI/CD—with build checks, basic tests, and applicable runtime validation. Future Guardian assurance is reserved as an extension point.

### Human Control Center

Provides the Human Governor interface to observe project state, AI activities, and execution progress; approve, reject, redirect, or override; and configure models, executors, and policies. The human remains a governor rather than a manual operator.

## Reversible Production and Recovery

AI-native software production must be reversible. As AI increases production speed, the system needs equally strong recovery capability.

### Engineering Snapshot

A snapshot is a trusted or recoverable engineering state. It may include a design artifact version, context state, task state, workspace/code reference, verification result, and decisions.

### Timeline

The platform should maintain engineering history across iterations, and users should be able to restore previous states.

```text
Iteration 1 → Iteration 2 → Iteration 3 → Iteration 4
```

## MVP Scope Boundary

The MVP does not include full CI/CD, automated deployment, production monitoring, full Guardian or ECF implementations, model routing, benchmarking, intelligent branching or merge, or complete SaaS multi-tenancy.


## Evolution Governance Boundary in the MVP

The following capabilities are long-term architecture directions, not MVP implementations:

- Software Evolution Governance
- Engineering Change Intelligence
- Feature Consistency automation
- Architecture Drift Detection
- Engineering Branching
- Intelligent Executor Routing

During the MVP, the Human Governor temporarily performs Feature Consistency Check, Architecture Direction Judgment, and High-impact Change Review.

The MVP focus remains:

- Production Planner
- Project / Work Management
- Executor
- Workspace
- Verification Loop
- Human Governance

The ChatGPT + Codex collaboration pattern is the origin of the MVP, while the objective is to validate an AI-driven software production process for real projects.




## Decision Capability Boundary

Decision Capability is an external intelligence capability in the software production system. Its responsibility is to answer:

> What should we do?

At the architecture-contract level, a Decision Request may contain:

- Question
- Context
- Constraints
- Options
- Required Outcome
- Risk Level

At the architecture-contract level, a Decision Artifact may contain:

- Recommendation
- Reasoning Summary
- Alternatives
- Risks
- Assumptions
- Confidence
- Human Review Requirement

### MVP Provider Principle

The MVP does not directly depend on YiJue. YiJue remains an independently evolving product. To avoid coupling the MVP to an unfinished external system, the architecture may use a **Minimal Decision Capability Provider** as a temporary, lightweight capability boundary. A bootstrap implementation may use an LLM, Governed Prompt, and Limited Context Assembly.

This provider must not replicate or replace YiJue, build a Decision Room, define a complete Decision Schema, or build a multi-role decision system. Its purpose is only to bootstrap the SPG loop, validate that the Production Planner workflow can consume the Decision Artifact Contract, and reveal capability gaps through production evidence. It remains replaceable by a future YiJue or other provider.

No YiJue adapter, concrete API, or YiJue implementation is defined here.

## MVP Capability Boundary

The MVP supports the basic Production Planner production loop, Project State, Iteration, VS, Work Item, Artifact recording, Executor invocation, Human Console, basic Production Reality View, and Capability Boundary.

The MVP does not implement:

- Real YiJue integration
- Multi-user parallel development
- Engineering Branching
- Complete Software Production Pattern Library
- Automatic Model Routing
- Complete Guardian
- Complete ECF

All other capability evolution described in the architecture documents is a Future Capability, Architecture Direction, and Not Implemented in the MVP unless explicitly stated above.
