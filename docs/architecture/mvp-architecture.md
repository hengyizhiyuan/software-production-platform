# MVP Architecture

This document records the intended MVP architecture. It is an architecture baseline, not a runtime implementation specification.

## Continuous Engineering Iteration Loop

The MVP is organized around a continuous feedback-driven loop:

```text
Human Intent → Design Lead AI → Planning / VS / Task Generation
    → Executor → Workspace Execution → Verification → Reality Feedback
    → Design Refinement → Next Iteration
```

Design is not permanently frozen after development starts. Implementation feedback can challenge design assumptions, and verification can trigger design refinement. Human intervention focuses on important decisions rather than every execution step.

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

An Iteration is one complete reasoning-execution-feedback cycle. It is distinct from the VS lifecycle, Task lifecycle, and code lifecycle.

## MVP Core Components

### Role Runtime

Supports AI roles participating in software production. The initial role is Design Lead AI; the architecture permits future Product AI, Architecture AI, QA AI, and DevOps AI roles.

### Design Lead AI

Understands project goals, maintains focus, produces product and architecture design, decomposes VSs and Tasks, generates execution instructions, reviews results, and decides whether to continue or revise. It is a governed engineering role, not a generic chatbot.

### Context Layer

Provides lightweight context management for project understanding, current baseline, important decisions, documentation references, and historical artifacts. It uses a Context Provider abstraction so roles do not remain permanently coupled to raw files. Future ECF integration is reserved but not implemented here.

### Workflow / Iteration Engine

Manages lifecycle states, drives iteration loops, tracks transitions, and permits returning to previous states. It does not enforce rigid waterfall stages; verification may lead to a design challenge, design refinement, and re-execution.

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
