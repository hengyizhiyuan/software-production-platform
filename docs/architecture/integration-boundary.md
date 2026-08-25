# Integration Boundary

## Guardian

The platform orchestrates Guardian. The platform is not the owner of Guardian Core.
The MVP does not implement Guardian. It reserves an Assurance Extension Point for a future flow:

```text
Verification → Guardian → Evidence → Acceptance
```

Guardian remains an Independent Assurance System: platform-native but platform-independent.

## Engineering Context Fabric

The platform consumes ECF capability. It does not design or redefine ECF Core.
The MVP does not implement ECF. It reserves a Context Provider abstraction for a future relationship:

```text
Role Runtime → ECF Projection → Engineering Context
```

## Consumer Project

Consumer Projects, for example 易决, use platform capabilities. They are not internal modules of the platform.

Using SPG to produce a Consumer Project does not make that product's runtime or Decision Engine a dependency of SPG.



## Decision Intelligence Boundary

YiJue is a Decision Intelligence Consumer Product / Application and remains independently owned and developed.
YiJue is a Consumer Product / Application and an important possible Decision Intelligence Capability Provider. The platform boundary is the Decision Intelligence Capability / Interface, not the YiJue product. YiJue can develop independently, does not depend on SPG, does not need to be aware of the software production platform, and does not own software production responsibilities. The Software Production Platform consumes Decision Artifact Candidates through a capability contract; it does not embed YiJue Decision Intelligence.

The relationship is:

```text
SPG → Decision Intelligence Interface
          ├── Lightweight Provider
          ├── YiJue Decision Engine
          ├── Enterprise Internal Decision Engine
          └── Third-party Decision Provider

Decision Artifact Contract → Production Planning → Production Loop
```

SPG does not wait for YiJue completion and does not depend on any provider's internal model, Agent, prompt, or product API. A lightweight provider may be used to validate the production loop without becoming a second Decision Intelligence product.

The MVP does not implement YiJue integration. A concrete interface API, adapter, and provider deployment remain Future Implementations / Not Implemented. Any provider remains subject to Ownership Separation, Source of Truth Separation, and Lifecycle Independence.
