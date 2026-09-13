# Watt Human Journey Architecture Tension Register

## 1. Status and use

```text
Register
    HUMAN_JOURNEY_ARCHITECTURE_TENSIONS

Status
    DISCOVERED / NOT RESOLVED BY THIS MISSION

Implementation authority
    NONE
```

This register compares the desired first-release Human experience with current
repository Reality. “Prototype simulation” means the later isolated prototype
may represent the target to test whether it is understandable. It does not mean
the capability exists or that the prototype can become a source of truth.

Change labels are discovery estimates for later planning:

- **API:** command/query contract changes or new aggregation endpoint.
- **Projection:** a new read model or composition of existing facts.
- **Domain:** owner semantics or lifecycle behavior requires review.
- **Data:** persistence or durable fact changes.
- **ADR:** an architecture decision is required before implementation.

## 2. Register

| ID | Desired Human experience | Current repository Reality | Mismatch | Safe to simulate? | Likely later work |
|---|---|---|---|---|---|
| T01 | Home starts with a Motive and useful conversation | `/app` opens a Work/Goal-oriented shell with a selected-Work surface | First use is organized around existing entities before the user has a Work | Yes; label as target | Projection, UI; possible API aggregation |
| T02 | Returning Home says what changed, what is active, and what needs action | Work list, attention list, queue, events, and deliveries are available through separate projections/routes | No single consequence-ordered return summary or visit cursor | Yes | API, Projection, possibly Data for last-seen basis |
| T03 | Work Formation Review shows objective, scope, constraints, outcome, artifact, and production boundary before admission | WIC exposes interpretation/readiness; the broader `PRE_AUTHORIZATION_WORK_PREVIEW_REQUIRED` finding remains open | Human authorizes an interpretation without a complete visible governed proposal | Yes, prominently marked planned | Projection, API, possibly Data; ADR on exact proposal identity/expiry |
| T04 | One calm Work context adapts to formation, design, production, review, and completion | Current UI renders many Control Room and engineering panels together | Correct facts exist, but information priority and disclosure are not state-aware enough in the live surface | Yes | UI/Projection |
| T05 | Human language names meaningful stages | Runtime stores PWU, Attempt, queue, Step, and execution status; UI exposes several raw states | No stable Human-facing naming/progress projection across plan and execution | Yes | Projection; possibly API display metadata |
| T06 | Queue is a first-class cross-Work product view | Durable queue APIs and selected-Work queue controls exist | Queue is embedded in Work detail; global competition and plain wait narrative are limited | Yes | API/Projection, UI |
| T07 | “Needs me” is one projection with deep links to exact context | `/api/attention` exists and current UI has attention panels | Attention types across formation, assets, queue, result review, and recovery do not yet form one coherent navigation contract | Yes | Projection, API; ADR only if attention semantics expand |
| T08 | Result preview happens before exact authorization and shows behavior, changes, checks, limits, and risks | Candidate/Vector and verification infrastructure exists; current delivery UI mainly exposes post-delivery artifacts/runtime; blueprint defines preview direction | General, form-aware pre-authorization preview adapters and a consolidated review projection are incomplete | Yes; use deterministic mock previews | API, Projection, Data for preview records; adapter implementation; ADR for unsupported forms |
| T09 | One Human action authorizes the exact understandable result and target set | Scalar Candidate and native CandidateVector authorization paths exist with exact identities | Internal Candidate/Vector vocabulary and technical target details need a Human translation without weakening exactness | Yes | Projection/UI; API DTO adaptation |
| T10 | Multi-repository result appears as one coherent outcome with per-target convergence | Native vector and multi-target convergence models exist; some routes are capability-gated | Product-wide aggregate preview, authorization, and partial-convergence presentation are not yet complete | Yes | API, Projection, UI; targeted capability completion |
| T11 | Assets include repositories, documents, designs, runtime targets, external systems, and generated artifacts under Work | Current implemented asset intake is repository-centered; managed workspace support exists | The generalized Human asset model is broader than current durable asset types and capability observations | Yes, but unsupported types must be labelled simulated | Domain, Data, API, Projection, ADR on asset taxonomy |
| T12 | No-repository Work proceeds naturally and receives a managed workspace only when needed | Architecture and current implementation support repository-optional admission and managed workspace allocation | Current UI still gives repository/engineering resource concepts high prominence | Yes | UI/Projection |
| T13 | Delivery history unifies runtime, repository, downloads, trust, and later refinements | `/delivery` is a separate page with manifests, runtime status, downloads, and Work selector | Delivery is detached from the main Work narrative and returning Home | Yes | Projection/UI; possible aggregate API |
| T14 | “Done” distinguishes produced, verified, authorized, integrated, delivered, and Human-satisfied without jargon | Those facts are separately modeled across SPG, verification, governance, Runtime Commit, delivery, and acceptance | No concise progressive trust story spans all owners; raw states can leak | Yes | Projection/API composition; no domain merge |
| T15 | Completed Work can be reopened from its delivery and retain history | Work interaction semantics support `CURRENTLY_SATISFIED + OPEN` and re-entry; application logic records reopened satisfaction | Navigation and delivery-to-refinement affordance are not yet a coherent primary journey | Yes | UI/Projection, possibly API link metadata |
| T16 | Topic changes preserve the current Work and offer a clear new-Motive path | WIC focus/relationship classification and transition decisions exist | Current technical classification and candidate-change fields leak implementation language | Yes | UI/Projection; conversation copy |
| T17 | Browser disconnect and slow clients never look like cancelled or duplicated work | Event streaming, cursors, bounded buffers, draft/outbox logic, and durable Runtime semantics exist | Reconnect, offline, pending-message, and “still running elsewhere” states need a coherent experience contract | Yes | UI; Projection/API error semantics; focused tests |
| T18 | Recovery says whether Watt is recovering, the Human only needs awareness, or action is required | Recovery classifications, barriers, checkpoints, queue modes, and attention facts exist | Technical conditions are not consistently translated into the three Human contracts | Yes | Projection/API composition; UI terminology |
| T19 | A stale plan/result decision refreshes safely and explains what changed | Exact revisions and optimistic/concurrency checks protect commands | The UI mostly presents an error/refresh path instead of a changed-basis comparison | Yes | API conflict payload, Projection, UI |
| T20 | Partial integration shows safe forward completion and exact reauthorization needs | Multi-target integration effects and recovery semantics are specified/partly implemented | No simple Human projection explains old/new refs, advanced targets, and remaining authority | Yes | Projection/API; capability completion; focused ADR if policy choices remain |
| T21 | Capacity and commercial limits are understandable without provider operations | Runtime retains resource reservations/usage and queue capacity; WIC/Executor profiles are configurable | No settled first-release commercial usage projection, and provider detail is too low-level | Simulate only the generic limit, not billing facts | Product decision, API/Projection; possible Data |
| T22 | Ordinary faults do not turn the Human into a debugging relay | Recovery semantics are strong and autonomous where safe | Some errors and statuses are still engineering codes; escalation copy/options are inconsistent | Yes | Projection/UI; error taxonomy mapping |
| T23 | Current Work list is the primary organizer; Goals are optional metadata | Current sidebar leads with Goals and status filtering | Goal-first hierarchy can imply a required Project-like container | Yes | IA/UI; no new domain entity |
| T24 | Product identity and language consistently say Watt | Runtime UI header still includes `TNGA Software Production`; English/Chinese and internal labels are mixed | Current shell does not yet express one product voice or terminology system | Yes; final visual brand remains out of scope | Content design/UI; later brand decision |
| T25 | Prototype review statuses are recorded per scene without changing product data | No scene-acceptance product model exists, and none is required | Review continuity needs a lightweight ledger outside production truth | Yes, in a documentation ledger only | Documentation/process; no product schema |
| T26 | Prototype simulation states reveal the full journey without competing with domain state machines | Reality is distributed across WIC, Work, Guided Design, Steering, queue, Executor, Verification, Candidate, commit, delivery, and satisfaction | A single mock enum could falsely imply one authoritative lifecycle | Yes only as a scenario cursor mapped to source facts | Prototype architecture rule; no domain/data change |
| T27 | Future Guardian/ECF can later add assurance/capability without blocking first release | Both are explicitly future and independent | Prototype could accidentally imply their judgments or marketplaces exist | Yes only by excluding claims and marking future placeholders deferred | None for first release; future ADRs |
| T28 | Current architecture documents accurately signal implemented status | Some older product/architecture documents retain point-in-time labels such as “designed/not implemented” or stale WIC status while later evidence and code moved on | Readers can mistake historical scope headers for present aggregate Reality | Prototype may cite current evidence; do not rewrite history silently | Documentation SOT index/recency policy; possible ADR on status roll-up |

## 3. Tensions that must be resolved before formal implementation

The following are experience-critical and should become explicit gates between
prototype acceptance and production implementation:

1. T03: the exact identity and authority semantics of Work Formation Review;
2. T07: a coherent Attention projection without a second interaction system;
3. T08–T10: form-aware result preview and exact authorization, including
   multiple targets;
4. T11: the boundary between current repository assets and a generalized asset
   model;
5. T14: a cross-owner trust projection that preserves distinct truths;
6. T19–T20: stale-decision and partial-convergence Human contracts;
7. T26: prototype state mapping that cannot be mistaken for domain lifecycle.

The prototype should intentionally exercise these tensions. If Human review
rejects the target mental model, the prototype is calibrated. If Human review
accepts it but repository Reality cannot support it without changing ownership,
an architecture review precedes implementation. Production must not imitate a
prototype assumption that Reality disproves.
