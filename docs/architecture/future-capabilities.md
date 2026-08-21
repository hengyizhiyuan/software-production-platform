# Future Capabilities

## Engineering Branching

Engineering Branching is a long-term direction, not an MVP feature. Traditional Git manages code branching; AI-native production may require broader branching across design, decisions, tasks, context, code, verification, and evidence.

```text
Baseline
  ├── Branch A
  └── Branch B
```

The intended evolution is Stage 1: Snapshot + Restore; Stage 2: Branch Creation; Stage 3: AI-assisted Merge.

## Intelligent Executor Routing

The platform may eventually select suitable executors based on task type, risk, cost, latency, and quality requirements. This is capability-based executor routing, not only model routing.

Examples include stronger reasoning for architecture tasks, lower-cost execution for simple coding, and stronger models plus stronger assurance for high-risk changes.


## AI Software Production Benchmark

AI Software Production Benchmark is a long-term capability direction. This document does not define its implementation details.

Its purpose is to measure how different AI models and executors perform inside the software production system, evaluating the complete production outcome rather than model capability alone.

### Executor Capability Benchmark

Future evaluation may compare coding and design executors using dimensions such as:

- Completion quality
- Success rate
- Execution time
- Token/resource consumption
- Rework frequency

### Workflow Benchmark

The benchmark may evaluate the impact of the AI-native production workflow by comparing:

```text
Traditional: User → Prompt → Model → Output

Platform: Intent → Context → Role → Task → Executor → Verification → Assurance → Accepted Artifact
```

Potential dimensions include lead time, rework rate, human intervention, defect rate, and trusted delivery throughput.

### Model Evolution Benchmark

The benchmark may measure whether improvements in AI models translate into measurable software production improvements, including:

- Task completion speed
- Quality improvement
- Cost reduction
- Change in assurance confidence

### Platform Stability Benchmark

The benchmark may verify that model replacement does not destroy engineering consistency, including:

- Context understanding consistency
- Decision consistency
- Artifact consistency
- Governance compliance

### Assurance Benchmark

The platform may integrate with Guardian to measure assurance effectiveness, finding quality, trusted change throughput, and assurance cost efficiency.

This records the integration direction only and does not design Guardian internals.

## Scope Boundary

These benchmark directions are not current MVP requirements. They should be developed only after sufficient production experience has established the relevant evidence and evaluation needs.


