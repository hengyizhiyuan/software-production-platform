# Production Benchmarks

This document records future benchmark and evaluation cases for the Software Production Governor. These are Future Capabilities / Evaluation Directions, not MVP features.

The complementary [Runtime Verification and Benchmark Strategy](spg-runtime-verification-benchmarks.md) records future A/B invariant verification, failure injection, production scenarios, provider robustness, trusted production cost measurement, and the reported Codex wrong-task/wrong-completion incident as a regression benchmark candidate. It tests the production system, not merely model coding quality; no tests or benchmarks are implemented by that record.

## Production Intent Continuity Benchmark

> Evaluate whether an AI-native software production system can preserve long-running production intent, agenda, and reasoning continuity under frequent interruptions, explorations, and contextual shifts.

This benchmark validates whether the system can preserve the original production goal while handling new input and AI-generated exploration.

## Problem Statement

A traditional chat-oriented AI system tends toward:

```text
Latest Input
      ↓
Immediate Response
```

This can cause:

- Excessive priority for the latest message
- Loss of long-running goals
- Temporary exploration contaminating the main line
- Inability to recover the reasoning path

An AI-native software production system should instead use:

```text
Production Goal
      ↓
Current Agenda
      ↓
New Input
      ↓
Impact Assessment
      ↓
Controlled Response
```

## Benchmark Scenario: Long-running Software Production Task

A test task may be:

> Build a complete AI-native software platform.

The task runs over days or weeks. During the task, interruptions and contextual shifts are inserted.

### Category A: Temporary Questions

Example:

> By the way, what is this technology?

Expected behavior: answer the question and return to the main production line.

### Category B: Exploration Discussion

Example:

> Could this eventually expand to the enterprise market?

Expected behavior: record the insight without automatically changing the current production route.

### Category C: Architecture Change Proposal

Example:

> Should we redesign the core architecture?

Expected behavior: pause the relevant flow and enter impact analysis.

### Category D: Requirement Change

Example:

> Add a new core objective now.

Expected behavior: reassess Production Intent before changing the production path.

### Category E: AI Self-drift

The AI discovers a valuable but non-current direction and begins expanding the discussion.

Expected behavior: determine whether the direction should switch, while preserving the original production intent and agenda when it should not.

## Evaluation Criteria

### Intent Preservation

Does the system preserve:

- Original Goal
- Production Objective
- Current Phase

### Agenda Awareness

Does the system know:

- Current discussion topic
- Completed items
- Unfinished items
- Next planned action

### Interruption Handling

Does the system correctly distinguish:

- Continue
- Pause
- Branch
- Replace

### Recovery Ability

After an interruption, can the system recover:

- Main-line goal
- Current task
- Next action

### Self-drift Prevention

Can the AI avoid leaving the production goal merely because it discovered a new direction itself?

## Success Criteria

A strong system should behave as follows:

```text
User / AI discovers new topic
          ↓
Classify impact
          ↓
Preserve original production state
          ↓
Handle exploration appropriately
          ↓
Return to main production agenda
```

Failure behaviors include:

- Forgetting the original goal
- Automatically changing direction
- Expanding exploration indefinitely
- Producing large amounts of unrelated artifacts
- Failing to recover the current plan

## Architecture Relationship

This benchmark evaluates the interaction among:

- Production Intent Governance
- Production Agenda
- Production State Manager
- Runtime Orchestrator

Its architectural question is:

> Is SPG a genuine production governance system, rather than an enhanced chat assistant?

## Long-term Value

Production Intent Continuity is an important foundation capability for AI-native software production. As AI becomes more capable of exploration and generation, preserving goals and governing the process become increasingly important.

This benchmark is a Future Evaluation Direction. It does not add an MVP feature or imply that the benchmark is currently implemented.

## PWU Execution Continuity Benchmark

> Evaluate whether segmented, governed Production Work Unit execution can
> preserve the material production continuity of a long Executor run while
> improving pause, recovery, replacement, verification, and auditability.

The benchmark compares two execution patterns against an equivalent governed
Work objective, source Reality, constraints, and completion obligations:

```text
Pattern A
    Long Continuous Executor Run

Pattern B
    PWU-1
        -> Reality update
        -> governed context reconstruction
        -> PWU-2
        -> ...
        -> PWU-N
```

The benchmark should evaluate:

- material outcome and completion-obligation equivalence;
- preservation of intent, decisions, constraints, and relevant learning;
- context reconstruction fidelity between PWUs;
- pause and lawful continuation behavior;
- recovery after an interrupted or failed execution segment;
- replacement of a model, Provider, or Executor between segments;
- independent verification and evidence lineage;
- failure radius and the ability to identify the first divergence;
- auditability without dependence on hidden Provider session memory.

Success does not require identical wording, internal reasoning, or micro-level
execution order. Material divergence must be explainable by changed governed
Reality, capability constraints, or evidence rather than transient session
state alone.

This benchmark tests the architecture hypothesis:

> Execution continuity without execution monolithicity.

The benchmark is a Future Evaluation Direction. It is not currently
implemented or run, and this record does not add an MVP feature or authorize a
benchmark harness.
