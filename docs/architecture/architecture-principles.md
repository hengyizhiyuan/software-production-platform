# Long-term Architecture Principles

This is a living architecture document. It records long-term directions and does not freeze the target architecture or expand the current MVP.
## AI-Native Software Production System

The platform is not an AI coding tool. It solves how humans and AI can continuously produce trustworthy software through a governed production loop.

```text
Intent → Design → Planning → Execution → Verification → Feedback → Refinement
```

The platform enables continuous software production rather than isolated development stages.

## Engineering Capability over Model Capability

The platform should not be designed as a wrapper around a specific frontier model.

Its fundamental value comes from providing:

- Engineering context
- Governance
- Workflow
- Role abstraction
- Authority boundaries
- Artifact management
- Verification
- Assurance

Models provide intelligence capability. The platform provides a production system in which that intelligence can reliably participate in software production.

> Model capability determines execution capability.
>
> Platform capability determines production reliability, scalability, and sustainability.

## Model Independence

The platform should preserve engineering understanding independently of model versions. It should not rely on a model to permanently store:

- Project intent
- Design rationale
- Historical decisions
- Current baseline
- Task status
- Governance rules

These must exist as explicit, platform-managed artifacts.

The platform should enable model replacement, executor replacement, model capability upgrades, and cost/performance trade-offs without losing:

- Project understanding
- Engineering continuity
- Decision history
- Production governance

## Target Architecture and Current MVP

Target Architecture describes long-term direction. Current MVP Implementation describes the smallest scope currently being built. They must remain distinct.

These long-term principles are not MVP requirements. The current MVP remains focused on:

- Project Workspace
- Context Management
- Role-based AI collaboration
- Task lifecycle
- Executor integration
- Artifact management

Future capabilities should be activated only after sufficient real-world production experience has been accumulated.

## Strategic Value

The platform does not compete with AI model providers. It enables organizations to continuously absorb advances in AI models while maintaining a stable software production system.

Future users may choose different executors according to cost, speed, capability requirements, and risk profile. The platform remains valuable regardless of which model generation dominates.


