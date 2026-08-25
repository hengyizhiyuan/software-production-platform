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



## Decision Intelligence Boundary

YiJue is a Decision Intelligence Consumer Product / Application and remains independently owned and developed.
YiJue is a Consumer Product / Application and a possible Decision Intelligence Capability Provider. The platform boundary is the Decision Intelligence Capability / Interface, not the YiJue product. YiJue can develop independently, does not depend on SPG, does not need to be aware of the software production platform, and does not own software production responsibilities. The Software Production Platform consumes a future Decision Capability through a capability contract; it does not embed YiJue Decision Intelligence.

The relationship is:

```text
Decision Intelligence Provider → Production Planning → Production Loop
```

The MVP does not implement YiJue integration. Any future provider remains subject to Ownership Separation, Source of Truth Separation, and Lifecycle Independence.


