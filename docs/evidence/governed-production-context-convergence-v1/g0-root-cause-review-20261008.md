# N1 G0 ECF Root Cause Review — 2026-10-08 06:18 UTC

Status: **root cause reproduced; new live Greenfield qualification pending**. This is new evidence from the isolated ECS database and current branch code. It does not revise the original failed Works.

## Evidence and authority

- E1, isolated persisted PostgreSQL: Product `ed52c0bc-e746-4abf-89c0-1bea5bd61c90`, Work `eaae7b07-38ed-50f4-8322-167da879596d`, Human input `interaction_records:80ab3a5c-f060-43c7-80e9-35d004a14010`, IRK assessment `3286917a-f696-41ee-9fff-91af1e99660b`, admitted Work Reality `bf2483ca-f8b2-5b09-962f-d7b688ed3467`, admission Governance `f8cbb580-eeb8-58df-b77c-4e49980c428f`.
- E1, exact source: managed Product V0 `84fd89663c56cef2ebbb8c7457d6077c4daaadbe`, tree `a25d6d85c3888a7d4be1346a758363f985aaffd3`, Work source basis bound to resource `92ee7c31-0f32-4545-b56f-ff5c4bd64230`. Product source identity is `watt://repositories/products/ed52c0bc-e746-4abf-89c0-1bea5bd61c90`; the Work resource identity is `watt://work-branches/eaae7b07-38ed-50f4-8322-167da879596d`.
- E1, original G0 trial: ECF reported missing `PRODUCT_INTENT`, `PRODUCT_INVARIANT`, `APPROVED_DECISION`; no runtime binding or Candidate. The first trial remains invalid setup because its managed-source provider was absent.
- E3, current-code reproduction: the old adapter required the Product source identity to equal the Work branch identity. They are intentionally distinct in a real managed Gitea Work, so it returned no managed context. The consumer then selected ECF `PRODUCT_UI_CHANGE`, whose repository README basis requires all three classes. The V0 genesis does not have that README.
- E3, patched-code read-only replay over the **same persisted G0 Work and exact source**: ECF selected `MANAGED_GREENFIELD_PRODUCTION` with `PRODUCT_INTENT` plus eleven admitted `APPROVED_CONSTRAINT` obligations; fingerprint `d72ac3ddba30f1e8e6073a66c2110be93b7ba4e82a29b2597be85451471e0a8e`. No `PRODUCT_INVARIANT` or `APPROVED_DECISION` was created. No DB row or Git ref was changed by this replay. This is a gate replay, **not** a G0 Work PASS.

## Contract comparison

| Boundary | Prior successful or intended first Greenfield seam | G0 live trial before repair | Resolution |
| --- | --- | --- | --- |
| Admission | Admitted Work revision and Governance scope; Human intent typed by IRK | Valid admitted revision and Governance; the Human explicitly requested one static `index.html` page | Admission was not the block |
| Context scope | ECF `MANAGED_GREENFIELD_PRODUCTION`: Product Intent, Repository Reality and Work Reality required; invariant/decision only if explicitly established or unresolved choice demands them | Fallback `PRODUCT_UI_CHANGE` demanded three README-derived Product classes | Preserve policy; repair owner-source selection |
| SOP | Feature delivery starts after Task/PWU formation | Stopped before Task/PWU, so no live G0 SOP execution evidence | Fresh Work must prove SOP/Worker |
| Source binding | Accepted managed Product source V0 is copied into a separate Work branch, each with its own identity and exact revision/tree | Both persisted identities were correct, but adapter falsely compared them for equality | Validate the Work resource against its Work basis, then the Product source version/revision/tree against that basis |
| ECF consumer | Managed owner projection uses admitted IRK goal and Work Reality; repository README is for repository-owned existing Product UI | Managed projection returned `None`; fallback sought absent README headings | New projection returns exact admitted Product Intent; Work restrictions remain constraints |

The earlier 2026-10-06 Managed Greenfield qualification used explicit Product Intent, Invariant and Decision sections in a source README and accepted that source. It did not infer those facts from an empty repository. The 2026-10-08 persisted Greenfield integration test also proves a minimal IRK path with Product Intent and Work constraints, but its fixture used one repository identity for both Product and Work, so it missed this live Gitea identity split. The regression fixture now models distinct identities.

The G0 Human input itself states the desired page, exact text, single-file scope and exclusions. The admitted IRK Production Intent and Work Reality legitimately project Product Intent. There is **no** Human statement of an enduring Product Invariant or Approved Product Decision and no pending reserved choice in this G0 IR. Such facts are nonblocking and must not be manufactured. If a future request presents an actual unresolved product choice, ECF must still fail closed and ask that concrete question.

## Repair and remaining proof

The branch changes `read_managed_greenfield_context` to use the exact Work resource identity from `work_source_bases` and to use the parent Work's own resource identity when inheriting an accepted successor. It retains admission, source version/tree freshness, Human fact provenance and ECF completeness checks. Sixteen focused unit/integration tests passed in the isolated regression DB; the new fixture has distinct Product and Work identities. Fresh Greenfield Work on an image built from the final source revision is still required before G0 PASS.

UNKNOWN: The historical Case B/C call stacks and their old missing receipts remain unrecovered. This G0 isolated reproduction proves the current root cause for the new trial, not that every historical failure had this same cause.
