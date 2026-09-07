# Work Formation Review Before Admission

## 1. Status and finding identity

~~~text
Finding
    PRE_AUTHORIZATION_WORK_PREVIEW_REQUIRED

Category
    Product Experience Gap

Priority
    FUTURE HIGH PRIORITY PRODUCT IMPROVEMENT

Implementation
    NOT IMPLEMENTED
~~~

This finding was identified during Control Room Slice 4 Human Product
Acceptance. It records a future product-experience improvement direction only.
It does not authorize a change to WIC, Work Admission, Human Authority, or the
Control Room implementation.

## 2. Problem

The current flow is:

~~~text
Interaction
    -> Interpretation
    -> Readiness
    -> Human Authorization
    -> Work Admission
~~~

Before authorization, the Human can review:

- what the Human said;
- what Watt interpreted;
- the current understanding.

The Human cannot yet sufficiently preview the governed Work that authorization
will create, including:

- the resulting Work objective;
- scope;
- constraints;
- expected outcome;
- production boundary.

Human authorization may therefore feel like approval of an interpretation
rather than approval of a governed production proposal.

## 3. Desired future flow

~~~text
Interaction
    |
    v
Interpretation Candidate
    |
    v
Readiness
    |
    v
Work Formation Review
    |
    v
Human Authorization
    |
    v
Work Admission
    |
    v
Production
~~~

`READY != Authority` remains unchanged. Work Formation Review would make the
proposed authority transfer understandable before the Human chooses whether to
authorize Work Admission.

## 4. Future capability

A future Work Formation Review should present:

- Proposed Work Objective;
- Desired Outcome;
- Scope;
- Constraints;
- Expected Artifact;
- Production Boundary;
- Impact Summary.

The intended Human actions are:

- **Admit** - authorize admission of the reviewed proposal through the existing
  governed Work Admission boundary;
- **Refine** - return the proposal to WIC refinement without creating Work;
- **Reject** - decline the proposal without creating Work or production
  Authority.

These are product-direction semantics, not an implementation contract, API,
schema, or lifecycle design.

## 5. Boundary

Work Formation Review is a Human decision-support surface before authority
transfer. It is not:

- a new Work truth source;
- a replacement for WIC;
- a replacement for Work Admission;
- automatic production authorization.

WIC remains responsible for Interaction, Interpretation, readiness, and Work
formation. Human Governance remains the source of Work Admission Authority.
The admitted Work Reality becomes authoritative only after the existing Work
Admission transition succeeds. Production Authority remains separate from Work
Admission Authority.

## 6. Current status

~~~text
Future High Priority Product Improvement

Not implemented.

No current WIC or Control Room architecture change authorized.
~~~

This finding must not be read as evidence that Work Formation Review already
exists. Control Room Slice 4 acceptance closed independently with this finding
classified as non-blocking. Any implementation requires a separate governed
contract and authorization.

## 7. Related source-of-truth context

- [Work Interaction & Closed-loop Refinement](../architecture/work-interaction-closed-loop-refinement.md)
- [Control Room State Experience Design](software-production-control-room-state-experience.md)
- [Control Room Slice 4 Human Product Acceptance Contract](../architecture/software-production-control-room-slice-4-implementation-contract.md)
- [Control Room Slice 4 Human Product Acceptance Evidence](../evidence/control-room-slice-4-human-product-acceptance.md)
