# Runtime Profile, Provider Placement, and Containerized Deployment

## 1. Status and interpretation

This document records an architecture clarification under **Architecture Baseline v0.1** for the SPG First Vertical Slice (FVS). It does not reopen Runtime Architecture Refinement, the Implementation Contract / Runtime MVP Design, or Coding Readiness. It introduces no production code, deployment artifact, provider integration, infrastructure commitment, or additional FVS feature.

The governing direction is:

> One SPG product architecture and one primary codebase support multiple deployment and provider profiles.

Regional and enterprise differences should primarily be expressed through capability bindings, provider/model configuration, adapters, deployment placement, and future residency policy—not independently evolving SPG products.

## 2. One product architecture, multiple profiles

```text
Single SPG Product Architecture
        |
        +-- Global Runtime Profile
        +-- Mainland Runtime Profile
        +-- Enterprise Private Runtime Profile
        +-- future custom profiles
```

The following remain stable across profiles:

- SPG domain model;
- Runtime governance model;
- Production Run and Plan Revision semantics;
- Production Work Unit (PWU) and Execution Attempt semantics;
- Completion Contract and Verification semantics;
- Candidate, Governance, Commit, and Trusted Baseline semantics.

The intended architecture is not a separate China codebase, Global codebase, and Enterprise codebase. Mainland and Global support should not become two independently evolving products unless future Reality demonstrates that separation is unavoidable.

## 3. Runtime Profile

**Runtime Profile** describes how the AI and execution capabilities required by a production environment are bound to concrete providers, models, adapters, and deployment placements.

```text
Runtime Profile
        |
        +-- Planning Capability Binding
        +-- Execution Capability Binding
        +-- Verification Capability Binding
        +-- Decision / Model Capability Binding, where applicable
        +-- Context capability/configuration, where applicable
```

A Runtime Profile configures capability realization. It must not redefine SPG domain semantics, governance invariants, Authority boundaries, or trusted-state transitions. This document does not freeze its physical schema, persistence representation, or management API.

## 4. Reference profiles

### Global Runtime Profile

An initial reference preset may bind:

```text
Planner        -> global / overseas model provider
Executor       -> Codex or another global coding provider
Verification   -> deterministic checks + global provider where required
```

### Mainland Runtime Profile

An initial reference preset may bind:

```text
Planner        -> Mainland-compatible model provider
Executor       -> Mainland coding provider / private coding provider
Verification   -> deterministic checks + Mainland provider where required
```

These are reference presets, not hard-coded product variants or an exhaustive profile taxonomy. Future profiles may be mixed, enterprise-specific, project-specific, custom, or residency-specific.

### Enterprise Private Runtime Profile

Enterprise-private deployment is a supported **Future Architecture Direction**, not a current capability. An enterprise profile may bind:

```text
Planner            -> enterprise-selected model and version
Executor           -> enterprise coding model or internal coding platform
Verification       -> enterprise-selected verification provider
Context / Embedding -> enterprise-private provider
```

Where supported, the enterprise retains control over provider selection, model selection and version, deployment location, and internal/private AI infrastructure. SPG supplies production governance and capability contracts rather than requiring one model vendor.

## 5. Capability binding chain

```text
SPG Capability Contract
        ↓
Runtime Profile
        ↓
Capability Binding
        ↓
Provider / Model Configuration
        ↓
Capability Adapter
        ↓
Actual Provider
```

Logical capabilities may include Planning, Execution, Verification, and Decision / Model Capability where applicable. SPG Core depends on capability contracts rather than provider identity, brand, prestige, endpoint, or model name.

> The system consumes capabilities, not provider prestige or vendor identity.

Provider identity, model identity, and model version are configuration and capability-binding concerns. They must not become SPG domain logic. Changing a model must not require rewriting Production Run, PWU, Attempt, Completion, Governance, Commit, or Baseline semantics.

Region-specific branching embedded in Runtime domain behavior is therefore prohibited as the intended architecture. Runtime resolves configured capability bindings rather than selecting a separate regional product runtime.

## 6. Provider Registry direction

A lightweight **Provider Registry** is reserved as a Future Capability. It may eventually describe configured providers through information such as:

- provider identity and type;
- endpoint and credential reference;
- region / placement;
- available models;
- supported capability types;
- availability and configuration status.

The registry is not implemented by the FVS and must not be treated as a Provider Marketplace. The FVS only preserves configuration and adapter boundaries that allow this direction later.

## 7. Model Provider and Executor Provider are distinct

```text
Model Provider
    ≠
Executor Provider
```

An Executor may be a coding CLI, remote coding worker, enterprise internal coding system, model-driven execution adapter, or another future execution capability. An Executor Profile may itself bind a model/provider:

```text
Provider
    ↓
Model / Version
    ↓
Executor Adapter / Executor Profile
```

Executor identity must not collapse into model identity. The Executor remains governed by the Execution Capability Contract regardless of how its underlying intelligence is realized.

## 8. Provider and model compatibility adapters

Different providers or models may require compatibility adapters while fulfilling the same logical SPG capability.

```text
Capability Contract
        ↓
Provider Adapter
        ↓
Vendor / Model-specific behavior
```

An adapter is not merely parameter renaming. It may normalize:

- request/response protocols and structured output;
- JSON/schema support and tool calling;
- system-role semantics and reasoning/model parameters;
- streaming and context limits;
- timeout, retry, rate-limit, and error behavior;
- asynchronous execution;
- CLI versus API execution modes.

The first FVS does not build a universal compatibility framework. It preserves only the stable contract and adapter boundary needed by its selected provider path.

## 9. Capability Descriptor and performance distinction

A future provider/model may expose a lightweight **Capability Descriptor** describing technically supported behavior, such as structured output, tool calling, streaming, context capacity, execution mode, and supported capability types. Its purpose is pre-execution profile validation, not automatic provider ranking.

```text
Planner requires structured output
        ↓
selected model cannot satisfy the contract
        ↓
Profile Validation fails
or a compatible adapter is required
```

Automatic capability discovery and profile validation are not FVS requirements.

The following concepts remain distinct:

```text
Capability Descriptor
= what a provider/model is technically able to support

Capability Performance Profile
= how well it performs in observed governed production
```

Observed performance may later inform routing, task decomposition, verification burden, autonomy, and model selection. It does not redefine capability support, Authority, or Runtime semantics.

## 10. FVS provider strategy

> FVS is architecturally provider-neutral but operationally simple.

For the first FVS:

```text
Provider abstraction          REQUIRED
Executor adapter boundary     REQUIRED
Configuration boundary        REQUIRED

Multiple production providers NOT REQUIRED
Global + Mainland dual runtime NOT REQUIRED
```

One real provider path is sufficient. A second provider should later validate the replaceability contract, but must not block the first vertical slice.

The MVP-level validation direction is that equivalent governed production flows can eventually run through both Global and Mainland Runtime Profiles without changing core Runtime semantics:

```text
Same Production Intent / Contract shape
Same SPG Runtime
Same PWU and Attempt semantics
Same Completion and Governance semantics
Same Trusted Baseline semantics

Profile A -> Global providers
Profile B -> Mainland providers
```

Only provider/model configuration, adapters, and placement should materially differ. This is a future validation of **Replaceable Intelligence, Durable Governance**; both chains are not implemented by this documentation task or required by the first FVS.

## 11. Future management control surface

The platform may eventually expose a thin administration/control surface for persisted provider and Runtime Profile configuration, including:

- Provider Registry;
- model/version configuration;
- Executor Profiles;
- Capability Bindings and Runtime Profiles;
- credential references;
- provider placement / region.

The UI is a control surface, not an independent Source of Truth for domain semantics. FVS does not require this web UI; CLI, configuration, and persistence may precede it.

## 12. Local-first and containerized FVS deployment

Initial FVS validation should run locally before final production server placement is selected:

```text
local development
↓
containerized FVS
↓
real Runtime validation
↓
server deployment later
```

Singapore, Mainland China, or another server region is not an FVS prerequisite.

SPG packaging should be containerized where practical. Containerization is an infrastructure and packaging concern, not a domain architecture concept:

```text
Source
↓
Build
↓
Container Image
↓
Local / Server Container Runtime
```

Application code, language runtime, dependencies, system tools, and appropriate provider-worker dependencies may be packaged into images to reduce host-environment drift.

**Docker + Docker Compose** are the preferred FVS/local deployment direction. A possible topology is illustrative, not a permanent three-container commitment:

```text
Docker Host
├── SPG Runtime Container
├── PostgreSQL Container
└── Executor Worker Container
```

Kubernetes is not introduced during FVS.

## 13. Host, database, worker, and secret boundaries

Containerization does not eliminate host responsibilities. A host may still require container runtime, network configuration, storage, firewall/security configuration, secret/environment injection, persistent volumes, domain/TLS, logging, backup/restore, and workload-specific host capabilities.

> Application runtime dependencies should normally be packaged into containers rather than manually reproduced on every server.

For development/FVS, PostgreSQL may run in a container with persistent volume storage. Future production deployment may use managed PostgreSQL or another compatible topology without changing SPG domain semantics. This document does not select production database hosting.

Executor-specific dependencies may be packaged into a dedicated Worker image. For example, a Codex-oriented worker may contain its worker runtime, Git, Codex CLI, and required execution dependencies. This is an example of packaging, not an integration commitment.

Raw user passwords and unmanaged permanent secrets must not be embedded in images. Credentials must eventually be injected through controlled configuration/secret mechanisms.

## 14. Provider placement and data residency

> Provider placement is an execution/deployment concern and must be decoupled from SPG Runtime semantics.

```text
Control Plane     -> may run in Region A
Planner Provider  -> may run in Region B
Executor Provider -> may run in Region C
```

The Runtime consumes capabilities rather than assuming co-location. FVS begins with the simplest local topology and does not implement distributed cross-region execution.

Enterprise and regional deployments may later require explicit policy for engineering data residency, provider region, executor region, repository placement, and external data transfer. No legal/compliance model or Policy Engine is selected or implemented here.

The current implementation boundary must nevertheless preserve this constraint:

> Do not assume that all engineering data may always be sent to every provider or every region.

## 15. Provider consolidation and Authority

A single physical provider may eventually perform planning, coding, and review. This does not collapse logical Capability Contracts, Responsibility, Verification, or Authority boundaries.

> Provider Consolidation Does Not Collapse Authority Boundaries.

Outputs continue through their respective governed contracts even when one provider realizes several capabilities.

## 16. FVS and future-scope boundary

This clarification adds only the following foundation constraints to the FVS:

- provider abstraction;
- Executor adapter boundary;
- Runtime/Profile configuration boundary;
- container-ready packaging direction;
- local-first execution direction.

It does not add requirements for:

- Global + Mainland dual-provider completion;
- provider-management web UI or Provider Marketplace;
- enterprise-private deployment;
- distributed workers, cross-region execution, or autoscaling;
- capability auto-discovery or routing engine;
- residency Policy Engine;
- Kubernetes, CI/CD, or server provisioning.

No Provider Registry, Runtime Profile implementation, adapter, Dockerfile, Docker Compose file, provider integration, or deployment artifact is created by this clarification.

The later [FVS-1 Contract](spg-fvs-1-implementation-contract.md) admits a minimal conceptual local-global-fvs profile boundary with deterministic Planner, Codex CLI Executor, and deterministic repository Verification adapters. Those are FVS-1 contract choices, not implementations, and do not promote the deferred Provider Registry or multi-provider infrastructure.

## 17. Architecture and mainline continuity

```text
Architecture Baseline v0.1

Runtime Architecture Refinement
    CLOSED

Implementation Contract / Runtime MVP Design
    CLOSED

Coding Readiness
    PASS

Implementation Governance
    AUTHORIZED FOR CONTROLLED IMPLEMENTATION
```

The current FVS mainline is:

```text
First Vertical Slice

F1. Slice Goal & Governance Contract
    REVIEWED / ADMITTED

F2. Minimal Technical Foundation
    REVIEWED / ADMITTED

F3-A. Runtime Slice Boundary & Physical Spine
    REVIEWED / ADMITTED

F3-B. Repository Integration / Commit Semantics
    REVIEWED / ADMITTED

F3-C. Executable Test & Failure Contract
    REVIEWED / ADMITTED

F3-D. FVS Coding Authorization Closure
    CLOSED — FVS-1 AUTHORIZED FOR CONTROLLED IMPLEMENTATION

S1-A. Runtime Project Foundation
    CLOSED / PASS

S1-B. Persistent Runtime Foundation
    CLOSED / PASS

S1-C. Bootstrap Baseline & Minimal Durable Runtime Spine
    NEXT — NOT STARTED
```

S1-A implements typed configuration and local project startup. S1-B adds PostgreSQL configuration and local persistence composition without implementing Runtime Profile resolution or provider adapters. The next governed step is explicit authorization of S1-C after S1-B SOT closure; this admission does not begin S1-C.
