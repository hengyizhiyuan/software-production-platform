# Work Identity, Closure and Archive Invariants
## Canonical Motive-bound Work and Anti-Project Guardrail

Date: 2026-09-15

~~~text
MOTIVE_BOUND_WORK_IDENTITY
    FROZEN

PROJECT_AS_FIRST_CLASS_DOMAIN_OBJECT
    NOT_INTENDED

PROJECT_CONTAINER_DRIFT
    PROHIBITED

ARCHIVED_WORK_AS_DORMANT_PROJECT
    PROHIBITED

NORMAL_REOPEN_COMPLETED_WORK
    PROHIBITED

ARCHIVED_WORK_REACTIVATION
    NOT_NORMAL_WATT_SEMANTICS

NEW_MOTIVE_AFTER_WORK_CLOSURE
    NEW_WORK
~~~

This document is the canonical long-term product and architecture guardrail for
Work identity, genuine closure and Archive/History semantics. It records
Human-approved truth. It does not implement lifecycle, archive UX, relation
schema, Asset discovery or ECF.

## 1. Core invariants

> Work is Motive-bound, not Asset-bound.

> Same Asset does not imply same Work.

> New Motive after Work closure creates a new Work.

> Archived Work is historical Reality, not dormant active Work.

> Historical Work may inform new Work but is not reactivated by it.

> Directly expressing a new Motive should normally be easier than locating and
> reopening historical Work.

> Asset continuity carries long-term software continuity.

> Executor Pause/Resume does not imply Work reopen semantics.

> Project is not a first-class Watt domain object.

> Navigation grouping must not silently become Project semantics.

These invariants deliberately prevent Watt from drifting toward the familiar
Project -> Task model.

## 2. Product rationale

Rejected mental model:

~~~text
The Human once used a Work to build a product
-> later wants to change the same product
-> finds the historical Work
-> reopens it as the continuing Project container
~~~

Intended Watt model:

~~~text
Every meaningful Human Motive forms a Work.
~~~

The Human may tell Watt which existing product to change, what should happen
now, which result is unsatisfactory or which new behavior is desired. They
should not need to remember which historical Work originally built “the
Project”.

Example:

~~~text
Earlier Motive:
    “做一个客户门户。”

-> Work A
-> production
-> delivery
-> genuine closure
-> archive

Later Motive:
    “客户门户的登录页太普通了，我想重新设计一下。”

-> Work B

NOT:
    reopen Work A
~~~

Work B may affect the same application, repository or Runtime. Shared Assets do
not make it the same Work.

## 3. Workshop and warehouse rationale

The active Work workspace is analogous to a factory workshop floor:

> 工厂车间 / workshop floor

It contains current production orders that still require attention,
production, judgment or closure.

Archived Work is analogous to a completed production order stored in the
warehouse:

> 已经完成生产、进入库房的生产记录 / completed production order

Once a production order has genuinely completed and left the workshop, it
should not remain on the workshop floor forever. If the resulting product later
needs rework, enhancement, redesign, repair, performance optimization or
migration, issue a new production order and bring the Asset back into
production under that new order.

Do not pull the old completed production order from the warehouse and pretend
the original order never finished.

~~~text
completed Work -> archive

new desired change
    -> new Motive
    -> new Work
~~~

The old Work remains immutable historical evidence of why production happened,
what was intended, produced, verified and delivered.

## 4. Motive determines identity, not duration

Motive-bound does not mean short-lived. One Motive may require weeks, repeated
Human refinement, many PWUs, multiple repositories and production cycles,
pause/recovery, and substantial design evolution.

~~~text
same active Motive -> same Work
~~~

Long duration does not turn Work into a Project container. Motive defines the
boundary.

The distinction between current production-cycle completion and genuine Work
closure is essential:

- a production cycle, PWU or currently admitted outcome may complete while the
  same Motive remains active and the Work relationship remains open;
- genuine Work closure establishes a historical boundary;
- after genuine closure, a later desired change forms a new Motive/Work even
  when it touches the same Asset.

## 5. Asset continuity versus Work continuity

A software product can live for ten years while accumulating:

~~~text
Work A - initial product creation
Work B - login redesign
Work C - export performance optimization
Work D - payment defect correction
Work E - database migration
Work F - accessibility improvement
~~~

All may reference the same long-lived Assets. Assets carry continuity; Work
objects do not need to.

Do not derive Work identity from Project, Product, Application, Repository,
repository namespace, Runtime, Customer, business system, source tree, Asset
collection or prior Work membership. These provide context, not identity.

## 6. Archive, History and intentional product friction

After genuine closure:

~~~text
Active Workspace -> Archive / History
~~~

Archive primarily preserves Motive, Work Reality, decisions, Evidence,
Verification, Delivery, artifacts, cost, production history and provenance.
It is not a sleeping active Work waiting to resume.

A future convenience action may say “基于此继续改进” or “基于此发起新工作”.
Exact wording is open, but the semantic result is always:

~~~text
new Motive -> new Work
~~~

Never:

~~~text
historical Work -> active again
~~~

The previous Work remains closed.

This asymmetry is intentional: directly telling Watt what the Human wants now
should be easier and more natural than finding and reopening an old Work. Do
not “optimize away” that distinction by turning historical Work into an
infinitely renewable container.

## 7. Historical context follows Assets

For a request such as “我想把之前那个订单导出功能优化一下”, Watt should
eventually discover relevant software Assets, repositories, Runtime, prior Work
outcomes, decisions, constraints and Delivery history without forcing the Human
to reconstruct organizational history.

~~~text
New Human Motive
    -> New Work
    -> ECF discovers relevant Reality
        -> Assets
        -> repository state
        -> prior Work outcomes and rationale
        -> decisions
        -> Verification / Delivery evidence
~~~

Historical facts can follow the Asset into the new Work without reopening the
historical Work. This is a future ECF direction, not implementation authority.

## 8. Execution continuity is different

Executor mechanics may legitimately support:

~~~text
active Work
-> active PWU
-> Attempt pause
-> checkpoint
-> resume
~~~

That is execution continuity. It does not imply:

~~~text
completed Work
-> archive
-> resume Work
~~~

> Execution continuity != Work identity continuity.

> Resume an Attempt/PWU != reopen a completed Work.

Future Executors must not reuse technical Resume semantics to implement
archived-Work reactivation.

## 9. Relationships do not require Project

Future Work may be informed by, follow up, fix a result of, share Assets with,
or supersede a Delivery from another Work. Such relationships preserve
provenance without introducing a Project parent. This document does not design
the relationship schema.

Works may be grouped by similarity, customer, time, Human-defined label,
product family or organization. Those are navigation projections unless
separately governed:

~~~text
UI group != Project domain aggregate
~~~

Left navigation should primarily represent active Works—the things currently
requiring attention. Completed Works belong in a separate History/Archive
projection, consistent with the workshop/warehouse model. This is product
direction, not implementation authorization.

## 10. Warning signs and mandatory architecture review

Stop and request architecture review if a future design implies:

- one Work permanently represents one application;
- completed Work is routinely reopened for future changes;
- unrelated Motives accumulate forever in one Work;
- Repository or Asset identity becomes Work identity;
- an Asset becomes a hidden Project parent;
- UI grouping becomes domain ownership;
- project_id is added because conventional systems use it;
- History makes “reopen Work” the normal continuation path;
- one Work contains years of unrelated product evolution.

Do not implement the familiar industry pattern automatically.

Before implementing History, Archive, Work Formation, WIC routing, Asset
relationships, Delivery continuation, Work navigation or ECF context assembly,
verify that the design preserves:

~~~text
Motive -> Work -> Closure
~~~

rather than:

~~~text
Project -> endless Work container
~~~

When ambiguous, stop for architecture review.

## 11. Explicit non-decisions

This guardrail does not freeze:

- exact archive eligibility;
- final History UX;
- Work relationship schema;
- Asset discovery;
- historical search;
- ECF retrieval behavior.

It implements no schema, lifecycle, UI, Runtime or ECF capability.

## References

- [Work-centric Production Model](work-centric-production-model.md)
- [Work-centric Production and Responsibility Principles](work-centric-production-and-responsibility-principles.md)
- [Motive / Work / Plan Concept Calibration](motive-work-plan-concept-calibration.md)
- [Work Interaction & Closed-loop Refinement](work-interaction-closed-loop-refinement.md)
- [Watt Product North Star](watt-product-north-star.md)
- [Core Workspace Experience Calibration](../product/watt-core-workspace-experience-calibration-notes.md)
