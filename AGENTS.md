# Repository navigation and governed execution

Read [AI_context.md](AI_context.md), the current Human mission and the applicable Project SOT before work.
Use [Architecture Principles](docs/architecture/architecture-principles.md) and
[System Overview](docs/architecture/system-overview.md) for responsibility boundaries.
Use [Governed AI Engineering Loop](docs/governance/governed-ai-engineering-loop.md)
for the existing Mission, evidence and authority process.

The highest Program invariant is owned by the Human Governor Accepted
[ADR-0002 at the fixed Program commit](https://github.com/hengyizhiyuan/software-production-system/blob/1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1/docs/04-decisions/ADR-0002-STOCHASTIC-NATIVE-ENGINEERING.md).
[Watt applicability](docs/architecture/program-architecture-decisions.md#stochastic-native-engineering--program-adr-0002)
records its publication and local scope.

For substantial work that produces, consumes, validates or relays probabilistic
intelligent products, including deterministic modules without LLM calls, read
[§13 execution discipline](docs/architecture/ai-native-development-execution-principles.md#13-ai-non-determinism-principle-and-execution-discipline)
and [§14 module adaptation and review](docs/architecture/ai-native-development-execution-principles.md#14-ai-native-module-adaptation-and-development-review).
Apply their admission/review/maintenance/closure checks in the existing Owner.
The current Human Governor / AI collaboration amendment is in that canonical
document; historical role names add no separate Architecture Lead approval gate.
For substantial work, establish an authorized scope and use the existing
[Mission Contract / capability review](docs/architecture/ai-native-development-execution-principles.md).
Model outputs remain candidates until their existing Owner validates and admits
them. Preserve accepted facts, exact source identity, authority, effect permits
and independent Guardian gates. Reuse bounded Self-Refine; do not manufacture
PASS through static expression special cases or altered obligations.

Inspect Repository Reality, the active branch and exact source/evidence versions
before edits and respect the user's current mission,
branch, side-effect and production boundaries. Preserve historical evidence and
report actual qualification separately from design intent.
[Golden Journey governance](docs/architecture/watt-regression-protection-and-golden-journey-governance.md)
defines regression and real qualification responsibilities.
