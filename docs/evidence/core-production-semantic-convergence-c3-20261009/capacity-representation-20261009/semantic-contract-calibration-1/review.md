# C3 — Semantic Formation Contract Calibration

## Status and recommendation

**Analysis/design delivered. C3 PARTIAL. Semantic contract calibration requires Architecture Lead approval; no implementation was performed.**

Recommend **a minimal component/source contract calibration within existing Fulfillment Formation**, followed by the existing bounded candidate/review qualification. Do **not yet adopt separate model stages**. The retained result proves both candidate defects and contract representation limits; it does not prove that a properly calibrated two-candidate boundary cannot converge. Additional stages under the unchanged contracts would encounter the same rejection predicates.

This is a recommendation, not an approved architecture change. No model call, G0 Work, Holdout access, Owner mutation, production change, image build or application code change occurred in this task. Counterfactual copies are ineligible for admission, semantic qualification or Assurance.

## 1. Exact basis and evidence levels

Analysis time: see `analysis.json` and the two container receipts (UTC; client local date 2026-10-10).

| Identity | Exact value |
| --- | --- |
| Evidence basis | `db78fdae67acb5862511f3672a58790a5a04e435` |
| Frozen Watt | `e0df8196cb51480f542af13b40cfa77fca6b6a6e` |
| Watt tree | `d479d61f5fcac075a5af3a274f60cbe3f6e9f53f` |
| Actual analysis image | `sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35` |
| Guardian | `d01bac1ad153e1eadefafe87d2ea4f5d65896ab6` |
| ECF | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| Historical Work | `048189aa-0613-5307-b6f4-c430e7977f93` — read only |
| Work Reality | `332a3a38-8719-580c-a1a2-c331ae14a5ae` |
| Product source revision | `465038ded6cf4ba335a11577de76acb1dea55b76` |
| Inventory fingerprint | `7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf` |
| Private original Candidate SHA256 | `e9020a908ba354c2e12ab4db297b32b7d17041fd12e4180a740f39d9fb42c9b5` |
| Candidate fingerprint | `98e38e96d66751327a6eb44519cf980db471aae99664b324c3e36a043a049444` |
| Component fingerprint | `74d621203266a170e163f420e9899ac989cd611d1c80c0d2a30af594ca74ff94` |

Levels used here: **OBSERVED** = retained source/Candidate or actual offline predicate result; **CODE** = exact frozen implementation/Owner contract; **REVIEW** = this analyst's semantic interpretation/design recommendation; **UNKNOWN** = not independently qualified. REVIEW is not an independent Semantic Review model receipt, admitted Engineering Truth, Human Decision or Guardian result.

The analysis capsule independently verified 278 installed Watt files, 5 Guardian files and 5 ECF files against the qualified import attestation. Network was `none`, root filesystem read only, input mounts read only, no credential/env-file mount and no database access. Both successful capsules exited 0; controller receipts prove original input hashes unchanged. Exit 0 means the diagnostic program completed; it is **not** a Candidate PASS.

## 2. What the 57 routes actually represent

All 26 sources and all 11 Work-constraint indices are present. This is identity presence, not fulfilled semantics. Inventory: 6 Facts, 4 IR Clauses, 4 IR Constraints, 11 Work Constraints and 1 Work Context. Capabilities: content 15, Git scope 8, deny-preview 3, deny-deploy 4, deny-publish 4, seal 4, retained context 8, unresolved 11.

### 2.1 One duplicate group: legitimate content distinctions, invalid references

Routes **8 and 9**, source **5**, both select `ARTIFACT_CONTENT`. The private rationales distinguish the heading assertion and paragraph assertion. These are real distinct content requirements, not two invented business requirements. Route 10 separately proposes Candidate sealing.

However, routes 8 and 9 have **identical component basis, entire-source-minus-last-character span `[0,71)`, target and support (source 12)**, and no linked Fact references. Only rationale differs; rationale is excluded from candidate identity. The retained proposal therefore does **not** establish two separately located components. It correctly fails the current duplicate predicate. Silently removing one would erase the model's proposed distinction without proving that the surviving check covers both requirements.

Separately, the validator's unique key is `(source_ref, capability)`; even two correctly located, distinct content components from source 5 would still fail. This is a **contract granularity limitation**, not evidence that these particular routes were already valid. If component-aware identity is approved, identical component/capability proposals must still be rejected and conflicting overlapping dispositions must remain invalid.

Sources **5/12** and **9/10** each share source-text hashes while retaining different authoritative record identities (Fact versus clause; Constraint versus Production Intent facet). They are not duplicates to delete globally. Preserve every reference and explicitly trace their equivalence/correspondence.

### 2.2 Eleven UNRESOLVED proposals, individually reviewed

Route/source numbers below are **zero-based original indices**, fixed by `analysis.json`. Local predicate return is a diagnostic observation, never admission or evidence PASS.

| Route / source | Actual semantic contribution (paraphrase) | Diagnosis and lawful boundary |
| --- | --- | --- |
| 12 / 6 | Work classification / isolated qualification background | Its rationale states there is no execution obligation, yet also proposes UNRESOLVED alongside retained context. Redundant uncertainty over the same component; existing context-only type is eligible, subject to complete span and global review. |
| 17 / 8 | Second classification clause | Same category as 12. Separate authoritative clause must remain; two contradictory dispositions on it need correction, not source deletion. |
| 23 / 11 | Only the governed target file may change | Rationale incorrectly treats affirmative file scope as requiring negative polarity. Git scope can be a current affirmative constraint. Candidate already proposes Git scope on this same whole span. |
| 26 / 12 | Verify required content and leave a reviewable Candidate | Genuine mixed content/lifecycle meaning. Its unresolved phase split is not proof that the requirement is impossible. Content and sealing capabilities exist; explicit components and lawful supports are required. |
| 35 / 14 | Work constraint 0: target-file scope plus exclusions | Genuine mixed scope/prohibition components. The claimed unresolved affirmative portion overlaps every executable proposal's same whole span. Separate components and supported correspondence are missing. |
| 40 / 16 | Work constraint 2: content verification plus Candidate availability | Genuine mixed meaning, but support source 20 is another Work Constraint, not the exact original IR clause accepted by correspondence validation. Local check rejects it. Original item correspondence to source 12 exists in the inventory; wrong support is a candidate defect. |
| 46 / 19 | Work constraint 5: exact content verification | Rationale says method/phase is unestablished although content verification is an existing capability. Support 12 is not an exact correspondence under the current helper; a matching Production Intent scope entry exists at sources 7/10. No need to ask Human to redefine the goal. |
| 48 / 20 | Work constraint 6: reviewable Candidate | Correctly avoids claiming a source-string witness, but support 16 is a Work wrapper; sealing requires original clause/production authority. Source 7/10 includes the corresponding scope entry. No sealed Candidate evidence yet exists for this proposal. |
| 52 / 23 | Work constraint 9: no additional pages | File/change scope exclusion, not deploy/publish permission. Current wrapper helper cannot express this exclusion via Git-diff correspondence; model also mixes unresolved with a whole-source Git proposal. Preserve requirement as unresolved until legal evidence binding exists. |
| 54 / 24 | Work constraint 10: named documentation file must stay unchanged | File/change scope exclusion. Same correspondence gap as 52; do not classify a documentation exclusion as an execution permission. |
| 56 / 25 | Work-level classification background | Rationale states no execution obligation. Redundant uncertainty alongside legal retained context; no separate missing business obligation was identified. |

Six of these original routes return UNRESOLVED at the local binding predicate (12,17,23,26,35,56); five first fail source correspondence (40,46,48,52,54). None became an admitted binding. No independent review established whether all residual semantic components were represented.

### 2.3 Eight RETAIN_CONTEXT proposals, individually reviewed

| Route / source | Classification |
| --- | --- |
| 11 / 6 | Eligible descriptive classification context by existing types; conflicts with route 12 and lacks complete source coverage. |
| 16 / 8 | Eligible second descriptive classification context; conflicts with route 17 and lacks complete coverage. |
| 55 / 25 | Eligible Work Context; cannot grant execution authority; conflicts with 56 and lacks complete coverage. |
| 15 / 7 | Current Production Intent, not context-only. Existing predicate: `OBLIGATION_CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY`. |
| 19 / 9 | Explicit current content constraint. Same rejection. |
| 21 / 10 | Production Intent facet of the same current content clause. Same rejection. |
| 37 / 15 | Required Work content constraint supported by current content clause. `OBLIGATION_REQUIRED_CONSTRAINT_CANNOT_BE_CONTEXT_ONLY`. |
| 44 / 18 | Required content scope entry; selected support lacks exact correspondence. `OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN`; retaining required content would not discharge it. |

RETAIN_CONTEXT is a **disposition**, not an extra record-preservation route to append to every executable source. Source immutability already preserves originals. Five proposals misuse retention to accompany current required content; three correctly identify background but also redundantly claim unresolved.

### 2.4 Coverage, mistaken Owner and evidence gaps

**OBSERVED:** every one of 57 routes uses `[0, length(source)-1)`. Every source loses its final non-whitespace character: some are punctuation; others are characters of file/scope/value text. All linked-Fact arrays are empty. The unique-quote locator makes no adjustment because the truncated quote matches the truncated slice exactly. The missing character is not recoverable by relocating that quote.

**CODE:** Python slicing and both Watt/Guardian coverage checks use end-exclusive offsets. The compact schema fields `a`/`z` lack an explicit end-exclusive description; instructions say start/end, without specifying `[a,z)`. A consistent inclusive/exclusive misunderstanding is a plausible explanation, **not observed hidden reasoning**. Model cognition remains UNKNOWN. Do not silently expand spans or ignore punctuation to make them pass.

**OBSERVED/CODE:** source 3 is a qualified exclusive file Scope. `exact_file_scope_paths` accepts only unqualified literal Scope, so its Git route 3 fails `OBLIGATION_FACT_SCOPE_VALUE_UNSUPPORTED`. The alternative content route 4 returning a local binding does not prove that Git scope was fulfilled by HTML. Preserving exclusivity while validating a derived exact path set needs a lawful representation, not qualifier deletion.

Source 4 is an accepted negated Scope Fact for exclusions. Its three permission routes 5–7 fail `OBLIGATION_PERMISSION_REQUIRES_EXACT_CLAUSE` even with support 13. Prohibition permission must be owned by the exact negative clause. An accepted Fact still needs a traceable result pointing to the clause's actual gate; leaving it unresolved or assigning HTML content is not the same evidence. The current contract lacks this complete cross-source fulfillment representation.

Sources 21/22 (deploy/publish wrappers) cite only negative clause 13, omitting the Production Intent source whose exclusions provide exact wrapper correspondence. Merely adding that source is insufficient: the exclusion path additionally requires typed `requested_effects`, while all 8 relevant IR facets have **empty** effect lists. Sources 23/24 are Git-scope exclusions, while that wrapper path requires `CONTINUOUS_FROM_ADMISSION`. These are concrete correspondence limits; no Subject Alias resolves them.

The negative source 13 names deploy/publish and file/page exclusions. It does **not** supply an explicit preview prohibition. Routes **5,27,32** nevertheless propose DENY_PREVIEW. Default execution permission may independently deny preview, but it must not be presented as this Human requirement's semantic component. No independent review ran, so these potentially incorrect assignments were not qualified.

There is no proven semantic omission ledger: all source identities appear, but whole-span reuse, lost characters, missing component links and conflicting dispositions prevent proof of complete obligations. Do not infer completeness from 57 routes or invent a missing Human authorization requirement from the absence of a route.

**CODE, bounded related risk:** `work_constraint_sources_correspond` returns true for an empty support list through `all(direct(entry) for entry in entries)`. None of this Candidate's Work-constraint routes has empty supports. This is a local proof-precondition gap, not an observed Guardian bypass or actual trial success. Missing-support negatives must be included in any approved correspondence calibration; no implementation is added here.

## 3. Counterfactual predicates and their limits

`analysis.json` runs unchanged routes through local binding predicates and separately checks global copies with `allow_review_pending=True`. This flag only permits diagnostic pre-review checks; no fake review record was supplied. Local checks return 24 pending-evidence bindings, 6 unresolved, 3 retained; 24 routes reject locally (16 correspondence, 3 permission-clause, 3 current-context, 1 Fact Scope, 1 required-context). These are **not** 33 partial PASS results.

| Isolated operation | First observed predicate |
| --- | --- |
| Original unchanged | `OBLIGATION_PROJECTION_DUPLICATE_ROUTE` |
| Remove later exact-key duplicate | `OBLIGATION_PROJECTION_CONFLICTING_DISPOSITION` |
| Executable/unresolved/retained preference variants | Still conflicting dispositions; choosing globally does not settle semantics. |
| Single disposition per source after destructive selection | `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST` |
| Extend those selected spans to whole sources | `OBLIGATION_FACT_SCOPE_VALUE_UNSUPPORTED` |
| Suppress the unsupported Fact Git route | `OBLIGATION_PERMISSION_REQUIRES_EXACT_CLAUSE` |
| Replace prohibition Fact permission routes by UNRESOLVED | `OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN` |

The latter four copies have 40/40/39/37 routes, retain all 26 source identities, and still reject. Recipes, fingerprints and rejected predicates are saved in `counterfactual-predicates.json`. The copies deliberately alter/drop proposed meaning and are not repairs. No copy was reviewed, admitted, persisted into Work Reality or used for runtime execution. Original SHA256 was rechecked unchanged.

## 4. Can the existing Self-Refine boundary solve this?

Frozen `_form_fulfillment_projection` uses at most **two formation candidates, one feedback, one independent review per candidate, at most four logical calls**. Receipt replay guards identities and pending unknown outcomes; transport/unknown failures stop instead of probability retry. Retain these protections.

Current candidate-validation `ValueError` feedback contains only the first predicate (first line, at most 1000 chars). In this case that is duplicate-route, without route IDs, missing-character coverage, scope limits or the correspondence failures. A model might repair more issues from the full inventory; **actual second-candidate effectiveness is UNKNOWN** because it was neither authorized nor executed in the reasoning-none trial or this task.

Model repair can in principle correct exact offsets, distinguish background disposition, choose original rather than wrapper supports, remove invented semantic assignments and propose precise components. It **cannot** change a source/capability uniqueness key, preserve an exclusive qualifier in a checker that refuses qualified Scope, manufacture absent typed effects, or change Guardian's requirement that every non-retained Fact has a current-verification route.

Another limitation: a structurally valid candidate whose independently reviewed bindings remain UNRESOLVED is recorded terminal with `UNRESOLVED_BINDING`; it does not automatically get the second candidate. Only the relevant exception path uses the one feedback. This preserves truthful stop and is not proof that all unresolved meanings received repair. Changing that classification would be a contract decision, not an authorization to retry probability failures.

**Conclusion:** existing uncalibrated Self-Refine is insufficient for confirmed representation gaps. There is no empirical evidence that **calibrated** one-feedback/two-candidate convergence is insufficient. A stage-count increase is not established as necessary.

## 5. Relevant Guardian/ECF seams — no wider audit

Exact Guardian software-assurance v1 / governed-obligation-v2 was inspected, including runtime `_component_plan_evidence`, `_projection_inventory_evidence`, `_supporting_clauses` and phase evidence. Guardian independently resolves Work/PWU/Native/Verification records; source/version/authority fingerprints and pending Human states remain required. Watt's COVERED flag is insufficient.

Guardian already hashes complete bindings and component plans, verifies source slices/union coverage, cumulative receipts (budget limit 2; attempts 1/2; at most 4 calls) and independent source-level semantic review. **It also currently requires every non-retained Fact to have CURRENT_VERIFICATION**, and wrapper-exclusion proof requires typed effects. A Fact-to-continuous-gate correspondence or staged receipt shape cannot be assumed compatible. The recommended extension must be qualified on both Owner sides before use; this task does not make that extension.

ECF pinned production-environment contracts carry observed identities; they do not grant execution or Delivery authority. The accessible ECF checkout HEAD is `e2202f3211843d3f6a6e16b3cdfa5226f21ee908`, not the qualified pin, but the inspected production-environment contract has zero diff from the pin and the actual-image ECF import hashes were checked against the pin's qualified attestation. No ECF change is currently justified by this formation failure. No 易决 access occurred.

## 6. Options and Architecture Lead decision package

### Option A — recommended: minimal semantic contract calibration

This is a bounded design proposal; **approval required before implementation**.

1. Define component identity over immutable source/version, precise original contribution and preserved semantic structure. Distinct assertions may share capability; exact component/capability duplication and contradictory same-component dispositions still reject. Do not equate arbitrary different spans with different semantics or require disjoint spans when shared qualifiers/scope legitimately overlap.
2. Make `[start,end)` explicit in the temporary schema/instructions and validate complete contribution coverage. Prefer exact quotes when location is uncertain; deterministic expansion may restore identity metadata, never widen an insufficient quote into an assumed semantic component.
3. Keep disposition at the component level. Retaining background must not discharge current content, and an unresolved component remains explicit and blocking where due. Preserve source-wide all-components completeness and independent global semantic review.
4. Define only the necessary derived **component/support correspondence proof**: exact original IDs/fingerprints, typed meaning and scope/qualifiers, existing target-path authority, relation of wrapper/facet to original requirement and correct Owner/Gate evidence. Model proposes correspondence; deterministic identity/authority checks and independent semantic review validate it. No model creates a typed admitted effect or rewrites Facts. Qualified file Scope must retain exclusivity; file/page exclusions bind exact Diff, prohibitions bind negative clauses/Native gates. Ambiguity stays unresolved.
5. Allow authoritative Fact fulfillment to cite the actual continuous or lifecycle Owner proof where semantically required, with reciprocal exact clause/Fact linkage and current gate coverage. Guardian must independently validate this narrow proof instead of requiring unrelated HTML content. No new Fact, permission, global ontology, audit database or Owner.
6. Supply a **bounded structured set of safely evaluable violations** (source/component/route IDs, stable predicates, exact evidence refs) to the existing single feedback. Dependent predicates must be labelled NOT_EVALUABLE, not guessed. Keep candidate limit, token/profile/transport limits and cumulative receipt budget. No side-effect retry is implied.

Likely change boundary for a later approved implementation: Watt `domain/governed_obligation.py`, `application/governed_obligations.py`, provider wire/review and managed fulfillment/evidence adapters; exact Guardian `runtime.py` evidence validators if the narrow proof changes. Reuse current contracts where possible; add versioned fields only when required. Guardian top-level request extension and any new version are **not assumed necessary** before schema compatibility is proved. ECF currently needs no change. No global Refine Coordinator, new lifecycle, semantic alias table or separate orchestration.

### Option B — contingent: bounded staged formation

Only consider if Option A qualification shows that simultaneous component identification/routing remains the demonstrated common failure, or Architecture Lead explicitly approves a staged contract now. Stage design must first solve the same Option A representation gaps; it is not an alternative to them.

- **Component candidate:** model sees the entire immutable inventory plus admitted relations and identifies contributions, shared scope/qualifiers, cross-source correspondence and unresolved/background facets. This output is derived and unadmitted; it does not divide Work into independent requests.
- **Routing candidate:** sees the same full inventory, all first-stage contributions and all capability contracts; proposes complete Owner/Phase/Evidence/Gate bindings. Any addition, split or correction requires a preserved lineage and full-source review; no hidden deletion, authority change or evidence fabrication.
- **Global independent review:** sees originals and the complete final plan, not isolated chunks, and verifies semantics, order/value/scope/qualifiers, all cross-source links, unresolved components, prohibitions, future gates and capacity/receipt identity. Guardian remains a separate evidence owner after production.
- A conservative schedule within the existing ceiling is **one component proposal + one final routing proposal + one independent review**, with no automatic extra formation call. Reusing the one correction opportunity requires an explicit alternative schedule: the second formation entry can correct the component proposal while producing final routes; an invalid/unresolved final result stops. Do not silently add two candidates per stage or turn the four-call ceiling into a new budget allocation.
- Partial-output receipt/replay identity, stage semantics and consumption of the existing two-candidate/one-feedback slots require approved contract calibration and Guardian compatibility. Keep cumulative wall/token observations and pending-outcome UNKNOWN rules. If preserving the original budget meaning is impossible, submit the exact budget/contract decision before coding.

| Evidence comparison | Option A | Option B |
| --- | --- | --- |
| Duplicate component/capability key | Fixes confirmed granularity seam | Still needs A's fix |
| All spans omit final character | Explicit locator contract + bounded feedback | Stage boundary can help inspect; does not guarantee correct offsets |
| Current-content retention and redundant unresolved | Component dispositions plus aggregate diagnostics | Explicit decomposition may help; improvement unmeasured |
| Qualified Scope / wrapper / Fact-to-gate gaps | Necessary lawful representation and matched Guardian proof | Cannot route around missing contracts |
| Capacity | None trial completed at output 3722; no observed output-capacity failure in that trial | Extra requests/repeated full inventory cost UNKNOWN; no demonstrated need from this result |
| Existing budget/replay compatibility | Preserve current mechanism; targeted calibration | New partial-stage lineage/scheduling must be approved and qualified |
| Empirical convergence after calibration | UNKNOWN | UNKNOWN |

**Decision requested:** approve Option A's exact component/source/evidence calibration scope, including the matched narrow Guardian evidence proof if necessary. Defer a new staged formation mechanism pending that bounded comparison. If choosing Option B instead, approve its partial-candidate/receipt contract and explicit unchanged-ceiling scheduling before implementation. This document supplies the reviewable design; no Runtime change accompanies it.

## 7. Qualification conditions after approval

Before any real G0: controlled small/medium/complex full inventories; correctly distinct same-capability components accepted, exact duplicate/conflicting same-component rejected; all characters/contributions and shared qualifiers retained; current content cannot be retained; legitimate background cannot become execution authority; mixed current/lifecycle components preserve both; exact Git exclusions and qualified Scope remain enforceable; source versions and wrapper links cannot drift; missing authority/evidence stays unresolved/blocked.

Preserve C1/C3 typed and open IR regressions, receipt replay/pending-unknown/cumulative budget/transport-stop regressions and affected PostgreSQL integration. Both Watt and exact Guardian must reject forged semantic review, injected binding, missing independent records, invented permission, wrong source/tree and unproven gate coverage. No absence-of-log safety proof.

A later specifically authorized model comparison must use a frozen implementation and independent non-prelisted expressions; evaluate complete plans, actual usage, error attribution and second-candidate outcomes. Fixture success is not model/production qualification. Holdout remains sealed. Only after applicable controlled and real-model evidence can the original C3 real Work qualification resume under its separate scope. Neither this analysis nor a successful specialty repair closes C3/N1 or grants Human Integration/Acceptance.

## 8. Usage, failures and durable recovery

This task: **0 model calls, 0 Work creations, 0 database connections, 0 builds, 2 successful offline diagnostic capsules**. First analysis capsule failed to read the private Candidate because cap-dropped root could not read a file owned by UID 10001. Original permissions were preserved; a new root-owned read-only private copy with verified identical bytes was mounted for the successful analysis. Retained startup failure is diagnostic infrastructure evidence, not a production regression or PASS. One follow-up controller invocation failed before producing an analysis receipt; stderr was not retained, so its precise remote failure is UNKNOWN. The repeated configured container name was corrected before the separate successful follow-up capsule. No such failure consumed model budget.

First successful analyzer wall time (including its local hash/validation work): **0.05677839700365439 seconds**, from its monotonic observation. Follow-up total CPU time, actual peak memory, Docker/SSH overhead costs and monetary compute cost are UNKNOWN; configured memory limit is not measured use. No library or PostgreSQL regression was rerun for this documentation/diagnostic-only task.

Historical reasoning-none trial, unchanged: HTTP 200/completed; input **17441**, output **3722**, reasoning **0**, cached **0**, total **21163**, wall **11.909806004026905s**; one Formation, zero Review. Low-effort historical trial exhausted its 16384 output allowance with 16384 reported reasoning tokens. Visible JSON token counts and the model's internal reasons remain UNKNOWN. Historical usage is not this task's usage.

Public receipts/design are committed in this directory; see `public-file-manifest.json`. Private full Candidate/dossier/rationales are **not** in Git. Cross-computer recovery uses remote C3 branch for public evidence and ECS persistent paths:

- Original private Candidate: `/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/reasoning-none-control-1/private/model-observations/formation-located-candidate.json`.
- Complete private semantic dossier and masked diagnostic output: `/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/semantic-contract-calibration-1-run2/private/` (directory 0700; generated dossier 0600).
- Actual follow-up receipts: `/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/semantic-contract-calibration-1-run3/evidence/`.
- Public snapshot: `/data/watt/c3-semantic-convergence-20261009/public-delivery-c3-semantic-calibration-20261010/`.

These are durable ECS locations, not a claim of an independent backup. No complete Human conversation, raw Provider response, hidden reasoning or credential value is included in this public analysis. No canonical main, historical Candidate, Human Decision or Quality Ledger was altered.

**Next necessary action: Architecture Lead review of the narrow semantic contract calibration decision. Execution stops here; C3 remains PARTIAL.**
