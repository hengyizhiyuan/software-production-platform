# Production Intelligence Architecture

## Production Planner: AI Native Software Production Governor

Production Planner is an AI Role responsible for keeping the software production process continuously convergent. It maintains Production Intent and Project Intelligence, drives the Production Iteration Loop, maintains Engineering Coherence, and coordinates Capability Execution.

It is not a Coding Agent, Project Management Tool, Super Agent, or Chatbot.

## Internal Capability Model

Production Planner does not directly own every intelligence capability. Its conceptual capabilities include:

- **Intent Understanding Capability:** Human Goal → Production Intent; identifies Goal, Constraint, Expected Outcome, and Ambiguity.
- **Production Planning Capability:** Production Intent → Iteration / VS / Work Item.
- **Production State Evaluation Capability:** evaluates Current State, goal attainment, and next action.
- **Impact Analysis Capability:** evaluates potential Change impact on Features, Architecture, and Existing Capability. This is a Future Capability and Architecture Direction for cases where code does not conflict but the system is harmed.
- **Human Governance Capability:** determines when to proceed automatically, request a human, or invoke an external Decision Capability.
- **Capability Router:** selects Executor, Guardian, Decision Intelligence Provider, or other future capabilities according to problem type.

These are architecture concepts, not implementation commitments.

## Capability-Based Architecture

```text
Human Governor
        ↓
Production Planner Role
        ↓
Capability Contract Layer
  Decision Intelligence Capability (replaceable provider; concrete integration is Future)
  Production Execution (Executor)
  Assurance Intelligence (Guardian — Future)
  Context Intelligence (ECF)
```

Each capability preserves independent responsibility, Source of Truth, Authority Boundary, and input/output Contract.

Production Planner consumes the Decision Intelligence Interface and Decision Artifact Contract. It does not depend on YiJue, a provider-specific API, or provider internals.

## Production Iteration Cycle (PIC)

PIC is the basic cycle of AI-native software production:

```text
Observe → Understand → Plan → Execute → Verify
    → Evaluate → Update Baseline → Next Iteration
```

The cycle is not a frozen Requirements → Development → Testing sequence. It is continuous design, execution, verification, and correction.

## Production State Model

Production State must be explicit and must not depend on Chat History, one Agent's Memory, or one person's experience.

It includes:

- Project Intent
- Current Baseline
- Active Iteration
- VS
- Work Item
- Artifact
- Evidence
- Decision Record
- Risk

Production Planner consumes Project State and ECF / Context capabilities; it does not own the factual state.

## Production Object Hierarchy

```text
Project
    ↓
Production Objective
    ↓
Iteration
    ↓
Vertical Slice (VS)
    ↓
Work Item
    ↓
Execution Step
```

VS is not the smallest execution unit. Work Item is closer to execution granularity. Artifacts and Evidence attach to Work Item and Iteration lifecycles.

## Workflow Philosophy

The long-term workflow uses:

```text
Production Policy + Production Pattern + AI Adaptive Planning
```

Policy defines non-violable rules. Pattern preserves a verified production route. AI Adaptive Planning adjusts according to Project Context, Risk, and Current State.

This is a Future Capability and Architecture Direction, Not Implemented in the MVP.

## Engineering Conflict Evolution

Future conflict understanding may include:

```text
Conflict
├── Text Conflict
├── Code Conflict
├── Contract Conflict
├── Architecture Conflict
├── Behavior Conflict
└── Intent Conflict
```

The long-term concern is semantic engineering consistency beyond Git Merge Conflict. This is a Future Capability and Architecture Direction, Not Implemented in the MVP.

## Scope Boundary

MVP remains focused on the basic Production Planner loop, Project State, Iteration, VS, Work Item, Artifact recording, Executor invocation, Human Console, basic Production Reality View, and Capability Boundary.

YiJue integration, multi-user parallel development, Engineering Branching, complete Pattern Library, automatic Model Routing, complete Guardian, and complete ECF are Future Capabilities and Architecture Directions, Not Implemented in the MVP.


## SPG Capability Model

```text
Software Production Governor (SPG)
├── Production Planner
│   ├── Generate Blueprint
│   ├── Generate Plan
│   └── Adapt Plan
├── Workflow Orchestrator
│   └── Coordinate Execution
├── Production State Manager
│   └── Maintain Reality
├── Impact Analyzer
│   └── Analyze Change Impact
├── Progress Intelligence
│   └── Project Visibility
└── Capability Router
```

This is a capability model and does not require each item to be a separate runtime module.

## Naming Rationale

The formal name **Production Planner** replaces Design Lead AI because:

1. “Design” can be confused with Decision Intelligence Capability and Architecture Decision.
2. “Lead” can imply that an AI owns final judgment authority.
3. SPG uses Capability-oriented Architecture rather than AI Employee Architecture.
4. Production Planner better describes the responsibility of transforming approved production intent into adaptive production plans.

The name deliberately omits “AI” because AI is an implementation method, not the capability definition.

