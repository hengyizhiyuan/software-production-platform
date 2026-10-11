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

## Model uncertainty and mission execution review

Use the canonical
[AI Non-Determinism Principle](../architecture/ai-native-development-execution-principles.md#13-ai-non-determinism-principle-and-execution-discipline)
when adding or materially changing a model-mediated capability. A Mission
Contract must identify allowed variance, immutable facts and authority, the
existing validation/recovery Owner and budget, termination rules, static
special-case risk, and representative real/negative evidence.

Classify a current failure as runtime variance, proven system capability defect
or governance blocker before choosing recovery or engineering evolution.
Prioritize the blocked production journey (P0) and necessary common capability
gaps (P1); defer optional quality/cosmetic work (P2/P3). Use local validation
for local edits, focused regression for grouped changes and broader regression
for architecture changes or required final qualification. The Human Governor
and AI collaborator perform this review within the existing mission; it adds
no separate approval actor or runtime compliance engine.


