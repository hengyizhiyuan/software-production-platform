# Governed AI Engineering Loop

## Human Governor

Responsible for:

- Goal
- Direction
- Constraint
- Acceptance
- Major Trade-off

## Production Planner

Production Planner is the core coordination capability in the AI-native software production process.

Responsible for:

- Understanding project goals and long-term direction
- Maintaining overall design intent
- Understanding capability boundaries and architecture constraints
- Tracking key design decisions
- Judging deviation from approved goals
- Driving the Design → Implementation → Verification loop

Its authority is focused on Why, What, Direction, and Boundary. It does not preserve all code details, replace the Coding Executor, replace Guardian, or become the sole source of truth.

## Repo-grounded Executor

Responsible for:

- Repository reality
- Implementation
- Verification execution

## Evidence / Artifact

Evidence and artifacts are the long-term source of facts. Conversation history is not the Source of Truth.


## Human Governor in the MVP

During the MVP, the Human Governor temporarily performs part of the Evolution Governance work:

- Feature Consistency Check
- Architecture Direction Judgment
- High-impact Change Review

As the platform matures, lower-value manual checks may be assisted or replaced by Production Planner, ECF, Guardian, and Engineering Change Intelligence.

## Human and AI Responsibility Boundary

The governed loop uses Controlled Autonomy. AI coordinates understanding, planning, decomposition, execution, feedback analysis, and adjustment. The Human Governor retains Goal Authority, Strategic Direction, Major Trade-off, Risk Acceptance, and Final Governance.

## Program invariant and model capability review

The fixed [Program ADR-0002](../architecture/program-architecture-decisions.md#stochastic-native-engineering--program-adr-0002)
is the authoritative stochastic-native engineering constraint. Substantial tasks
producing, consuming, validating or relaying probabilistic intelligent products
use the existing
[Mission Contract review](../architecture/ai-native-development-execution-principles.md#stochastic-native-capability-review).
Role ownership, independent Assurance and Acceptance Authority remain unchanged.
Documentation adoption is separate from Runtime conformance qualification.

## Module adaptation in development and maintenance

The sole Watt normative body is [Development Principles §§13–14](../architecture/ai-native-development-execution-principles.md#14-ai-native-module-adaptation-and-development-review).
Task admission, architecture/implementation review, maintenance diagnosis and
qualification/closure use its [existing-process checks](../architecture/ai-native-development-execution-principles.md#145-default-development-and-maintenance-process),
including deterministic consumers without LLM calls. Record applicable answers
in the existing Mission Contract/review; ordinary deterministic tasks need no
full checklist. The Human Governor and AI collaborator retain existing authority
boundaries. No new approval workflow, governance Owner or compliance engine is
created, and existing modules receive no conformance PASS from this adoption.
