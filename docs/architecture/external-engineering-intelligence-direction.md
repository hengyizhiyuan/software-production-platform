# External Engineering Intelligence Direction

Status: **RECORDED DIRECTION — broader external engineering intelligence remains unimplemented**

Implementation: **Public GitHub/Web evidence acquisition is implemented separately; the broader research/adaptation workflow described here is not complete or authorized by this record.**

Document role: **ARCHITECTURE DIRECTION MEMO / HUMAN-VISIBLE PRODUCT CAPABILITY**

Recorded: **2026-09-09**

Current implementation boundary (2026-09-25): read-only external Search and
Fetch now enter the existing Interaction, Task Contract, Connector, and Evidence
path. See [Public external search and retrieval](watt-ai-native-software-production-architecture.md#public-external-search-and-retrieval-2026-09-25).
The historical non-goals below describe the 2026-09-09 documentation mission,
not the current availability of public search.

This document preserves a future product direction in the repository Source of
Truth. It defines intent and responsibility boundaries, not an implementation
contract. Architecture Baseline remains v0.1. The
[main Roadmap §5.9](../roadmap/watt-development-roadmap-and-progress.md#59-external-engineering-intelligence)
records this capability after the current priorities and existing future
backlog entries. Priorities 1–4 and the current MVP scope remain unchanged.

**External Engineering Intelligence** is a working concept name. Chinese
candidates are **外部工程智能 / 外部方案研究 / 行业方案研究**. Naming and UI
are not frozen.

## 1. Capability Intent and User Story

Watt should not assume its own model or Executor always has the best solution.
A Human should eventually be able to initiate an explicit, independent external
engineering research activity when:

- a technical problem remains unresolved for a long time;
- repeated Executor attempts or refinement do not converge;
- the Human has no clear implementation approach;
- the Human wants to understand mature industry practices;
- useful references may exist in open-source systems, frameworks, plugins,
  papers, RFCs, technical documentation, or existing products;
- the Human wants to adapt an already demonstrated engineering mechanism to
  their own system.

The core User Story is:

> 作为正在使用 Watt 开发软件的用户，
> 当我对某个技术问题没有理想方案，或者希望参考行业中的成熟实现时，
> 我希望能够主动要求 Watt 调研相关的优秀产品、开源项目、论文、框架、插件、标准和工程实践，
> 让 Watt 分析这些方案为什么有效、适用于什么条件、与我的系统有什么差异，
> 并提出如何将其中合适的机制适配到我自己的系统中，
> 而不是要求我自己在搜索引擎、GitHub 和文档之间人工寻找、阅读、理解和搬运代码。

This is a potential **independent, explicit user entry point**, not merely a
hidden Executor behavior. Independent access to the capability does not imply
a second Work lifecycle, new Truth owner, or autonomous production authority.

## 2. From Finding Code to Understanding Mechanisms

Traditional development often involves:

```text
Search Engine
    -> Stack Overflow
    -> GitHub
    -> Plugin Marketplace
    -> Official Documentation
    -> Source Reading
    -> Code Snippet Selection
    -> Manual Adaptation
```

Watt should raise this activity to the level of a **mature solution mechanism,
Architecture Pattern, or Engineering Practice**. Finding code is useful only
when its mechanism, assumptions, and local suitability are understood.

The future conceptual flow is:

```text
Problem Reality
    -> External Solution Research
    -> Candidate Implementations / Practices
    -> Mechanism Understanding
    -> Applicability Analysis
    -> Watt-system Mapping
    -> Recommended Adaptation
    -> Human Decision / Authorization
    -> Implementation
    -> Verification
```

Here, Watt-system Mapping means mapping into the user's system being developed
through Watt, including its local Repository Reality and governed Work/design
contracts. It does not mean copying the reference system's architecture into
Watt itself. The flow describes responsibility handoffs, not new Runtime Step
types or a parallel state machine. A valid research outcome may be rejection
or a decision to defer, with no implementation.

## 3. Expected Research Sources and Evidence Limits

Potential sources include:

- excellent open-source source code and GitHub repositories;
- frameworks, libraries, and plugins;
- official technical documentation;
- RFCs and standards;
- academic papers and engineering blogs;
- publicly documented architectures of mature commercial products;
- benchmarks, case studies, and demonstrated industry practices.

**External source ≠ Truth.** External material is Evidence, Reference,
Candidate Solution, or Design Input. A well-known project's implementation
does not establish the correct architecture for Watt or the user's system.
Source-domain observations remain distinguishable from source claims, Watt's
inferences, and decisions admitted into local governed Reality.

Research should retain source identity, available version/revision and
observation time, relevant excerpts or references, and limits of the evidence.
Unknown versions, unavailable evidence, conflicting sources, or uncertain
applicability must remain visible. Popularity is not proof of suitability.

## 4. Expected Research Result

The output must be an engineering synthesis, not simply “10 GitHub projects.”
A useful result should answer:

1. **Problem:** What is the actual problem, grounded in the current Work,
   Repository Reality, observed failures, constraints, and desired outcome?
2. **Routes:** What materially different solution routes exist in the industry?
3. **Mechanism:** How does each candidate implementation or practice solve it?
4. **Rationale:** Why was it designed that way, distinguishing documented
   rationale from Watt's reconstruction?
5. **Preconditions:** What scale, environment, data, operating model, or other
   assumptions must hold for success?
6. **Trade-offs:** What benefits, costs, limitations, and failure modes follow?
7. **Local fit:** Which mechanisms fit the user's current system and why?
8. **Conflicts:** Where do they conflict with local architecture, Product
   Intent, contracts, dependencies, or ownership boundaries?
9. **Risks:** What License, provenance, Security, Maintenance, and Dependency
   risks or unresolved questions remain?
10. **Disposition:** Should each candidate be **Directly Adopt**, **Adapt
    Conceptually**, **Reimplement**, or **Reject**, and on what evidence?
11. **Mapping:** If selected, how should the mechanism map to local components,
    contracts, Work Assets, design decisions, and bounded production scope?
12. **Verification:** What evidence would demonstrate that the adaptation
    actually solves the original problem without unacceptable regressions?

Direct adoption still requires local suitability, license/provenance review,
and the applicable Authority and production gates. Conceptual adaptation and
reimplementation do not automatically remove these risks. A recommendation
must expose unknowns and alternatives; it is not an approved decision.

These are future product-output expectations, not a frozen artifact schema,
API, checklist UI, or current acceptance-test implementation.

## 5. User-visible Entry and Triggering

### Human-triggered — primary product form

The Human may explicitly request:

> 这个问题我没想好，帮我看看行业里别人怎么解决。

Potential entry concepts include “研究行业方案”, “寻找成熟实现”, “参考开源架构”,
“调研类似产品”, and “寻找已有解决方案”. Specific UI, naming, interaction flow,
and provider selection remain undesigned.

WIC should interpret the research question, desired outcome, relevant Work or
pre-Work context, and scope. Asking for research does not authorize adopting a
recommendation or changing code. Before Work admission, material remains
Interaction provenance or candidate input. Governed Work admission and asset
association remain necessary where applicable; the entry point does not
automatically create Work.

### Watt-suggested — secondary future form

Future Watt, Verification, or Guardian findings may justify suggesting research
when refinement fails to converge, the Executor repeatedly fails, significant
unknowns remain, or local solution quality is insufficient. Watt may propose
that the Human initiate External Engineering Intelligence research.

A suggestion is not self-authorization. Any research must stay within an
explicitly governed question, scope, access, resource budget, and stopping
boundary. Unbounded source exploration, silent scope expansion, automatic
retry, and automatic adoption are not implied. Material expansion returns to
the applicable Human Authority boundary; routine activity inside an admitted
envelope need not become per-search manual approval.

## 6. Relationship With Existing Watt Architecture

The current repository already separates WIC, Work Reality, Guided Design,
Plan Steering, PWU/Executor, SPG, and independent Verification. Full ECF and
Guardian remain future capabilities. This direction preserves those boundaries:

| Existing owner / capability | Relationship to external engineering research |
| --- | --- |
| Human Authority | Owns Product Intent, material direction and risk decisions, and applicable authorization. The Human may reject the recommendation. |
| Work / Work Reality | Remains the center of production work and its governed intent, scope, and decisions. Research refers to the relevant Work and admitted Asset relationships; it creates no second Work Truth. |
| WIC | Owns understanding and interaction around the Human's research request, Shared Understanding, and governed Work evolution. Conversation and research material remain distinct from admitted Reality. |
| Guided Design / Architecture | Assesses how research affects design, local fit, alternatives, conflicts, readiness, and design rationale. Material decisions retain Human Authority. |
| Plan Steering | Owns WHAT NEXT and decides whether and when research findings become production actions from current governed Reality. A research recommendation cannot advance the Plan by itself. |
| PWU / Executor | Performs subsequent authorized implementation inside the admitted production envelope. Research cannot directly edit code through a bypass around PWU or Execution Governance. |
| SPG / Production Governance | Retains production admission, exact contract/basis, Attempt boundaries, independent Observation, Completion, Verification, Candidate authorization, integration, and Runtime Commit semantics. |
| ECF — future | May preserve or assemble sources, source versions, research conclusions, applicability conditions, Historical Rationale, and which knowledge entered a particular Decision Context. Context support does not own the engineering decision. |
| Guardian — future | May verify claimed benefits, new reliability/security/license/dependency risks, and incorrect mappings between reference mechanisms and the final implementation. Assurance does not select product direction. |

**External Engineering Intelligence ≠ ECF.** Research discovers, understands,
compares, and recommends mechanisms; ECF provides context/provenance capability.
**External Engineering Intelligence ≠ Guardian.** Guardian independently
qualifies outcomes and Evidence, rather than owning research selection or
Human product direction. No new Agent hierarchy or physical service allocation
is selected here.

Authoritative related documents:

- [Work-centric Production Model](work-centric-production-model.md) and
  [Work-centric Production and Responsibility Principles](work-centric-production-and-responsibility-principles.md);
- [WIC Architecture Contract](work-interaction-closed-loop-refinement.md);
- [Guided Design Core](guided-design-core.md) and
  [Guided Design Facilitation](guided-design-facilitation-layer.md);
- [Plan Steering Principles](reality-driven-plan-steering-principles.md) and
  [MVP Behavioral Contract](reality-driven-plan-steering-mvp-contract.md);
- [SPG Domain and Contract Baseline](spg-lite-domain-contract-baseline.md) and
  [Executor Autonomy Envelope](executor-autonomy-envelope-attempt-granularity-mvp-contract.md);
- [ECF Integration](../context/ecf-integration.md),
  [Guardian Integration](../assurance/guardian-integration.md), and
  [Human Governance](../governance/human-governance.md).

[External Design Intake](external-design-intake-capability-direction.md) is a
related but distinct input direction: it brings existing design assets into
Guided Design. External Engineering Intelligence starts with a problem and
researches possible mechanisms. They may share attributable inputs and design
governance, but this record neither merges them nor changes Intake's priority.

## 7. Provenance and Decision Accountability

The future product should preserve an explainable chain wherever possible:

```text
Problem
    -> Research Source
    -> Candidate Mechanism
    -> Recommendation
    -> Human Decision
    -> Adaptation
    -> Implementation
    -> Verification Result
```

This is **Explainable Engineering Decision Provenance**. It should let the
Human reconstruct where a solution came from, why it was selected, what Watt
changed, which assumptions came from external material, which judgments Watt
made, what the Human decided, and what later verification established.

The chain should reference existing domain-owned facts and exact applicable
source, design, Work, production, and Evidence revisions rather than create a
new Truth store. ECF may preserve and assemble these references. An approved
recommendation does not rewrite an active PWU's contract or past production
facts; changed material basis requires the existing reassessment and admission
boundaries. Rejected alternatives and superseded rationale remain attributable.

The purpose is learning and accountability, not blame shifting. It should help
distinguish failure caused by an inapplicable reference, an incorrect
architecture decision, a faulty adaptation, Executor implementation error,
insufficient verification, or changed external conditions. Uncertain or mixed
causes should remain uncertain rather than being assigned without evidence.

## 8. Potential Strategic Product Value

### Capability Extension

Even when a model cannot solve a problem directly, Watt may find and help the
Human absorb mechanisms already developed elsewhere. Its effective capability
boundary may partially expand from:

```text
Model Native Capability
    -> Model Capability + External Engineering Knowledge + Governed Adaptation
```

This is a strategic hypothesis, not a promise that every problem has an
external solution or that adoption will succeed.

### User Trust

The Human could see the available industry approaches, why Watt recommends a
particular mechanism, and how it fits their system. Source evidence, local
analysis, and explicit decisions provide a stronger basis for judgment than
an unexplained “AI says this is the design.”

### Potential Differentiation

The product direction extends a Requirement → Generate Code workflow toward:

```text
Problem -> Discover -> Understand -> Compare -> Adapt -> Govern -> Produce -> Verify
```

This broader direction is a potential differentiating capability. It is not a
verified competitive advantage or a claim that other tools lack research.
Current public Search/Fetch covers evidence acquisition, not the full
comparison, adaptation, and governed production journey described here.

## 9. Related Internal Reference Engineering

Watt's own future development may use a similar method at important technical
bottlenecks to study Codex, LibreChat, LobeHub, Open WebUI, or other mature
Agent and engineering systems. These are illustrative research candidates,
not researched findings, selected dependencies, or endorsements.

**Internal Reference Engineering** is an internal application of the same
idea. The newly recorded product direction remains **Human-visible External
Engineering Intelligence**. Internal improvement must not replace or reduce
that product capability to an invisible optimization tool. This mission does
not perform any of that external research.

## 10. Architecture Invariants

1. **External source is not Truth.** It supplies evidence or candidate input,
   not automatic local architecture authority.
2. **Conversation is not Truth.** Raw dialogue is provenance, not a governed
   decision or direct execution authority.
3. **External implementation must not silently redefine Product Intent.**
4. **Research must not bypass Human Authority.**
5. **Research must not bypass Work / Steering / PWU / SPG governance.**
6. **Copying code is not equivalent to understanding a mechanism.**
7. **Architecture pattern adoption must consider local Repository Reality.**
8. **License / provenance / security risks must remain visible.**
9. **ECF may preserve context, but does not own engineering decisions.**
10. **Guardian may verify adoption, but does not select product direction.**
11. **Human may explicitly reject the externally recommended solution.**
12. **Watt must distinguish researched fact, inference, recommendation, and
    final approved decision.** Approval does not convert uncertain claims into
    verified facts or waive required production governance.

## 11. Non-goals for the Current Phase

This documentation mission does not include or authorize:

- Web Search or GitHub Search implementation, repository cloning, or automatic
  source-code download;
- a plugin marketplace, ECF, Guardian, Code Agent, or new Agent hierarchy;
- a new Truth Source, parallel Work lifecycle, or changes to current Work,
  PWU, SPG, or Execution Governance;
- code, database/schema/migration, API, UI, provider, or Runtime changes;
- immediate MVP inclusion or changes to the established first four Roadmap
  priorities.

The current action is only: **Record the capability so it cannot be lost.**

## 12. Roadmap Rediscovery and Future Admission

The [main Roadmap §5.9](../roadmap/watt-development-roadmap-and-progress.md#59-external-engineering-intelligence)
is the navigation entry, with **RECORDED / DEFERRED** status. This direction is
also discoverable through [AI_context.md](../../AI_context.md) and
[Future Capabilities](future-capabilities.md#external-engineering-intelligence).
It follows the current major development items; it is not Priority 5 or a
scheduled implementation commitment.

Future ECF, Executor/PWU, Guardian, Guided Design, and product capability
reviews should revisit this direction for relevance without automatically
promoting it. A future implementation requires a separate bounded architecture
contract and authorization covering research scope, source/provenance and
access semantics, Human decision boundaries, local adaptation, verification,
and acceptance scenarios. No storage model, provider integration, UI design,
Runtime extension, or implementation sequence is selected by this record.
