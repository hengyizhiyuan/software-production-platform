# Watt Dogfood Project Pool & Production Coverage

Status: **LIVING MEMO / CAPABILITY COVERAGE BACKLOG**

This memo records the current pool of real company software that Watt / 工律 may
progressively use as Dogfood after 恒溢启源 formally began commercial operations.
It is not a fixed roadmap, delivery schedule, or implementation authorization.
Projects enter the pool according to real company need and are not assumed to
start together.

## 1. Purpose and operating context

恒溢启源 is now operating as a real company. Its future internal software needs
are therefore an important long-term source of Dogfood for Watt. The preferred
loop is:

```text
Real company need
    -> Watt produces the real system
    -> delivery exposes capability gaps
    -> Watt improves
    -> delivery becomes Production Coverage evidence
```

Dogfood should create both actual company value and new evidence about Watt's
software-production capability. Synthetic demonstrations remain secondary to
useful company work.

## 2. Current Dogfood project pool

The pool is intentionally broad. It describes software forms and representative
company needs, not commitments to build every item.

### 2.1 Content and presentation systems

Representative projects:

- 恒溢启源 corporate website
- Watt technical or product marketing site
- Product documentation and usage guide site

Coverage questions include information architecture, content organization,
branding, responsive Web, SEO and discoverability, static and dynamic content,
deployment and release, and continuous content evolution.

### 2.2 Complex Web applications

Representative projects:

- Watt / 工律 itself
- Operations management or campaign operations platform

Coverage questions include complex domain modeling, long-lived evolution,
multi-module workflows, stateful interaction, permissions, business process,
data-model evolution, Brownfield change, production integration, and
verification, recovery, and delivery loops.

Watt is a major long-term Dogfood system, but it must not be the only evidence
that Watt generalizes beyond itself.

### 2.3 Consumer Mini Program

Representative project: 易决小程序端.

Coverage questions include Mini Program ecosystem adaptation, mobile interaction,
multi-client API contracts, identity and session handling, shared backend
capability, platform-specific publishing and review, and synchronization across
Web, backend, and mobile surfaces.

### 2.4 Consumer application

Representative project: 易决客户端.

Coverage questions include mobile client lifecycle, local and remote state
coordination, push and notification, device capability integration, release and
upgrade, mobile UX, client stability, and multi-version evolution.

This memo does not choose a native or cross-platform stack; that remains a
separate Repository Reality and architecture decision.

### 2.5 Enterprise internal and back-office applications

Representative projects:

- employee management system
- internal company workflow or process system
- other small operational systems required by 恒溢启源

Coverage questions include CRUD, complex forms, RBAC and permissions, approval
flows, enterprise data models, reporting and query, internal tools, and rapid
delivery of common SME software. This category matters because it represents a
large share of ordinary enterprise software demand.

### 2.6 Infrastructure, middleware, and engineering systems

Representative projects:

- Guardian — Engineering Assurance System
- ECF — Engineering Context Fabric

This category tests whether Watt can produce engineering infrastructure and
platform-level systems, not only end-user business applications.

Guardian remains an independent Engineering Assurance System: platform-native,
but platform-independent. Its concern is evidence-driven assurance, findings,
gates, verification, independent subsystem architecture, cross-system contracts,
and trustworthy engineering infrastructure. It is not redefined here as a Watt
Agent or ordinary code-review wrapper.

ECF remains the Engineering Context Fabric. Its concern is Engineering Memory,
Truth Routing, Context Assembly, engineering fact organization, version,
ownership, rationale and impact relationships, and decision-scoped context.
This memo does not redesign Guardian or ECF.

## 3. Watt Production Coverage

Watt's claimed capability should gradually be backed by real delivered projects,
rather than architecture claims alone. A lightweight conceptual coverage model
is:

```text
software form × lifecycle stage × engineering capability × real delivery evidence
```

Each Dogfood project can add evidence across different dimensions. A coverage
area may be described as:

- `UNPROVEN` — no credible delivery evidence yet;
- `PROVING` — active or limited evidence exists, but the boundary is not stable;
- `PROVEN` — real delivery evidence supports the stated boundary;
- `NEEDS_REQUALIFICATION` — prior evidence is stale, contradicted, or no longer
  representative.

These are documentation concepts only. This memo does not create a runtime
coverage registry, database, scoring system, or new Truth Source.

## 4. Coverage principles

1. Do not launch all projects at once.
2. Real company needs take priority over synthetic capability demonstrations.
3. Each project should ideally create company value and new Watt evidence.
4. Prefer projects that exercise different capability boundaries instead of
   repeatedly proving the same CRUD path.
5. State capability from evidence: describe what real delivery has proven and
   what remains unproven. Do not claim that Watt can build any software.
6. The pool is living. New company needs may add projects as 恒溢启源 develops.

The pool does not replace the current development roadmap or reorder its active
priorities. Project admission, production scope, Work formation, Steering,
PWU, execution, verification, delivery, and Human acceptance remain governed by
their existing contracts.

## 5. Commercial evidence without marketing claims

The long-term commercial value is credible delivery history. When a customer asks
whether Watt can produce a class of system, the useful answer should point to:

- software forms actually delivered;
- lifecycle stages actually exercised;
- engineering capabilities supported by evidence;
- capability boundaries that remain unproven or need requalification.

This memo is an internal evidence and planning reference, not a marketing claim.

## 6. Scope boundaries

This document does not create implementation plans, dates, delivery schedules,
technical stacks, new architecture, Guardian or ECF designs, or current roadmap
items. It does not authorize coding any listed project and does not modify Work,
PWU, Runtime, Verification, or Human Authority semantics.

Future project selection must begin from Repository Reality and actual company
need, then receive its own bounded product, architecture, and implementation
authorization where required.
