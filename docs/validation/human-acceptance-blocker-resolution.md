# Human Acceptance Blocker Resolution

Date: 2026-09-10.

Status: **READY_FOR_HUMAN_ACCEPTANCE**.

This bounded change removes the workflow blockers that prevented a Human from validating the Software Artifact Delivery vertical slice. It does not redesign Watt, introduce Project, or alter Software Artifact Delivery architecture.

## New Work entry

Watt now exposes an explicit **New Work** action in the Human–Watt interaction surface and a visible **新建 Work** link from Work-to-Delivery. The delivery link opens `/app?new=1`. The application consumes that parameter once, removes the prior Interaction selection from browser preference state, and starts a fresh Interaction context. The first Human message still creates only an Interaction; Work admission remains a later explicit Human authority action.

The new context does not inherit the selected Work, Work Reality, production authority, PWU, Run, or repository scope from the previous context. Existing Work remains available through the Work list.

## Work boundary finding and correction

The active Interaction already received an exact `ActiveWorkInterpretationContext`, including the current Work Reality Revision, Engineering Scope fingerprint, Plan/production references and satisfaction state. The boundary failure was therefore not caused by missing conversation binding or missing Work context.

The first divergence was classification policy:

- the deterministic fallback recognized only literal markers such as `new work` and `unrelated`;
- the real Provider instruction emphasized new-Work distinction when a Work was already satisfied, but did not make the same comparison normative for every active Work;
- consequently, an explicit different durable objective such as “I want to develop a CRM system” could be classified as an on-topic change to an inventory-system Work.

The correction adds a conservative application guard for explicit declarations of a different system/platform/application-scale object and strengthens the Provider policy. Such input is projected as `UNRELATED_NEW_DEMAND` with `NEW_WORK_RECOMMENDED`. Watt asks the Human whether to start independent Work formation. It does not modify the current Work, create a Work, or transfer production authority automatically. Ordinary features, questions and related explorations remain inside the existing classification path.

## Runtime port assessment

The current acceptance environment uses `127.0.0.1:8009` for Watt and `127.0.0.1:8010` through `8019` as the bounded static-Web delivery adapter pool. The PostgreSQL mappings are runtime-infrastructure ports, not Human product routes. Separate loopback origins intentionally isolate delivered application versions and their browser storage from Watt and from one another.

This topology does not block MVP Human acceptance. Consolidated routing, automatic external port management and a general Runtime Manager remain deferred; this change does not redesign them.

## Human acceptance path

1. Open Watt at `http://127.0.0.1:8009/app` or use **新建 Work** from `/delivery`.
2. Select **New Work**, describe a new Software Artifact Delivery objective, review the interpreted candidate, and explicitly admit it.
3. Complete the existing governed delivery flow.
4. Return to an existing Work through the Work list.
5. State an unrelated durable objective, for example “I want to develop a CRM system.”
6. Confirm Watt shows a pending new-Work recommendation and requires a Human choice before independent Work formation.

No Project concept, new lifecycle state, schema change, migration, automatic Work admission, or delivery architecture change is introduced.

## Focused validation evidence

- Provider policy and static UI/API contracts: 24 PASS.
- Browser-state and interaction-entry Node contracts: 36 PASS.
- Affected WIC focus, active-cycle and transition integration cases: 9 PASS against an isolated disposable PostgreSQL database.
- The explicit CRM scenario produced one `PENDING_HUMAN` transition, retained the original governed Work revision, left the Work count at one and created zero production facts.
- Python compile/import and `git diff --check`: PASS. The optional local Ruff/Black tools were not installed, so no formatter result is claimed.

## Runtime readiness

The existing `watt-delivery-acceptance` app container was restarted without restarting PostgreSQL or changing its volumes. Its read-only `/opt/watt-source` mount loaded the validated source directly. `/health`, `/app` and `/delivery` each returned HTTP 200; the served application contains the New Work control, the delivery-page entry and the one-shot context reset. The restart created no new Interaction, Work or production fact.

Automated in-app browser attachment was unavailable on this Windows host because the browser helper process could not start (OS error 1385). This is a host test-tool limitation, not a Watt Runtime failure. Human visual/product acceptance remains the authority and is intentionally not claimed by this record.
