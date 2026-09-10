# Work-to-Delivery First Vertical Slice — implementation and acceptance

Date: 2026-09-10. Base: `d8aece326366ef329d15c1bc0a6779f59be9ec46`.

**IMPLEMENTED / AUTOMATED VALIDATION PASS / RUNTIME READY / HUMAN PRODUCT ACCEPTANCE PENDING**

## A. Architecture Design

The [as-built architecture](../architecture/work-to-delivery-multi-repository-spg-proposal.md) describes the same-runtime multi-repository extension. Work owns intent and admitted scope; Assets provide observed evidence; Guided Design and Steering form bounded production; existing SPG/PWU/Executor/Verification govern execution. Delivery publishes exact trusted artifacts and records a separate Human decision. No Project entity, ECF, Guardian Core, or Executor lifecycle redesign.

Repository namespaces use the existing immutable `(repository_identity, repository_ref)` identity. Source Snapshot lineage determines production namespace; per-namespace pointer locks/CAS and same-repository foreign keys prevent a second repository from becoming an implicit global baseline. Historical fingerprints remain unchanged. Recovery uses the exact source namespace.

## B. Work Model Changes

WIC can admit a long-lived Work without a repository. Empty admitted Engineering Scope and nullable repository facts are explicit, including API responses. Design can run; production still requires a selected repository. Work Reality source distinguishes WIC assessment from Work-owned asset-scope admission. Scope changes append revisions and preserve old production bindings.

## C. Asset Model

Repository Asset reuses EngineeringResource; scope/binding reuse existing Work records. Intake adds a durable request/observation receipt, UUID-managed local path and canonical source deduplication. Supports HTTP(S) Git clone without embedded credentials, existing repositories within the configured import directory, and new local Git creation. Each repository gets its own trusted baseline. New initialization writes only a generic README; design content later goes through SPG.

Limits: one authoritative ref per resource in this adapter; Markdown context required; no remote repository creation/push, SSH authentication UI, arbitrary host path import, repository deletion, or all future asset types. URL aliases are not resolved to a universal remote identity.

## D. Delivery Target Model

Nine target kinds are represented; only Document Package is executable in this slice. Target and acceptance criteria are immutable per Work for now. Unsupported adapters are explicitly rejected.

A manifest binds current Work Reality, exact production binding/Runtime Commit, repository revision, verification IDs, artifact hashes and sizes. Publish requires independent verification PASS and trusted commit. UTF-8 Markdown files are read from that exact commit, never the mutable working tree. Preview/download reject unlisted paths, traversal, symlinks and oversized files; ZIP contains manifest, target and artifacts.

Human ACCEPT/REQUEST_CHANGES is a separate immutable, idempotent decision against the exact current manifest fingerprint. No automatic acceptance. A changed Work revision or production cycle makes old delivery historical. One decision per manifest; after requesting changes, continue through WIC to form a new cycle, rather than overwrite the old decision.

## E. Existing Repository Flow

Synthetic fixture: `/var/lib/spg/repository-imports/inventory-example`, containing a minimal inventory-tool context. Imported through the actual asset page as `验收 A · 已有库存工具`.

Work: `9df7358a-9b46-56c0-b60b-f12f3b48f159`.
Interaction: `cc5a5903-9a9a-4f44-b820-50790be4c658`.

Chinese Human input describes low-stock reminder design for operators and supervisors. Clarification fixes the strictly-below threshold rule, role boundaries, no notifications/history/integrations and a Markdown design deliverable. WIC recognizes existing-product evolution; exact Work admission selects the imported repository. Actual Guided Design continues against its context. Synthetic feedback is labelled as such, not presented as real user research.

## F. New Work Flow

Work: `ef7b1e1a-4788-5c75-9595-3a99da100bbb`.
Interaction: `fca3ff44-40fb-40bc-baa8-ce6dff81b49c`.

Chinese input requests an operations management platform, clarifies supervisor/operator permissions and three task states. Work is first admitted with no repository. Real Guided Design results for motive/users, outcomes and boundaries were persisted before creating any new asset. The actual page then creates `验收 B · 新运营平台`, binds it to the same Work and sets Document Package criteria. Both repositories coexist in the same app/database. The separately admitted recheck Work is `f55ff982-650e-57d7-a863-fe2c1ae11f19` (Interaction `911b2c96-1ad6-4f0f-b965-73c3244bbe61`). It also starts without a repository and then selects the already-created empty repository B. The existing post-admission seed selector remains a text heuristic: the recheck outcome phrase “现有格式检查” selected the evolution agenda despite the explicit new-product intent. Its design outputs still use the admitted new-product scope; the original new Work selected the general product agenda. Aligning this legacy selector with the full Design Intent Frame is a known follow-up limitation, not a new product or repository ownership rule.

## G. End-to-End Production Flow

Exact design result summaries/decisions and source IDs are materialized into the reviewable document objective. Human proposal approval → Steering admission → one PWU → Executor → independent contract-driven verification → exact Candidate authorization → Git integration → trusted Runtime Commit → manifest/preview/download. Product acceptance remains pending until Human operates the acceptance UI. The existing Markdown verifier checks the exact path/operation, readable content, required markers and diff format; it does not prove that every prose acceptance criterion is semantically satisfied. Human inspection of the actual document remains necessary.

The PostgreSQL/Git deterministic E2E test traverses this full chain, including explicit test-only Human acceptance and exact-manifest rejection. It is separate from the interactive acceptance database; it does not accept the user's feature or runtime deliveries.

### Real Provider evidence

Existing-repository case traversed real `gpt-5.6-sol` WIC, Guided Design and Executor, independent Verification PASS, exact Candidate authorization and trusted Runtime Commit. Through the actual browser UI, its package was published, previewed and downloaded, then verified against manifest hashes after an app restart.

- Runtime Commit: `e82cd953-23ff-5706-9719-81a17f21586e`.
- Manifest: `8c72d489-d084-5019-ad88-a25325847c33`.
- Git revision: `0f617bc5b55abe6fcc3c2b08f7b5c7029734dc27`.
- Artifact: `docs/low-stock-reminders-design.md`, 10,972 bytes, SHA-256 `6122a2d08f5a8f5931e198d9e0821c1485d4c518c512ffad2308b802bd2b7bcb`.
- Verification: `f01eaa0c-2ae1-536f-8975-53dd08c05002`.
- Browser: `delivery-existing-published.log`, zero page errors; downloaded `existing-document-package.zip` matches the exact manifest.
- No Human product acceptance decision was recorded in the acceptance database.

The first new-Work production produced `docs/design.md` but independent verification correctly FAILED `git diff --check` because line 3 contained Markdown trailing spaces. Its Work, snapshot and failure remain preserved, and no delivery was published from it. The existing verifier was not weakened and the failed snapshot was not edited or relabelled PASS. Executor materialization now explicitly communicates the existing whitespace/UTF-8 requirement, including the fact that untracked files are not covered by a plain working-tree diff check. A separate synthetic new-Work recheck uses the same still-trusted repository. Failed-Verification replan/retry UI is not implemented by this slice; it does not invent a PWU lifecycle transition.

The original new Work remains an intentional failed-history fixture at its original URL. The recheck result is recorded separately below when finished. Provider structural-response errors are preserved as failed turns; retries do not grant authority or overwrite previous evidence.

## H. Automated Validation

Automated checks pass after the recorded corrections. Local evidence is under `.spg/validation-evidence/`:

| Check | Result | Evidence |
| --- | --- | --- |
| Complete non-integration suite | 364 passed before final focused corrections | `delivery-unit-final.log` |
| Final Provider/collaboration/WIC/delivery/UI contracts after admission/correction prompt fixes | 71 passed | `delivery-final-provider-contracts.log` |
| Earlier wire/WIC/delivery/UI contracts | 53 passed, including the new contradictory-RESOLVED rejection | `delivery-focused-final.log` |
| Executor input and code/document scope contracts | 54 passed after the format instruction correction | `delivery-executor-input-regression.log` |
| Legacy populated baseline migration / lossy downgrade | 1 passed; old baseline unchanged and multi-repo downgrade rolled back | `delivery-migration-check.log` |
| JavaScript state/queue contracts | 35 passed | `delivery-js.log` |
| Runtime, Git integration, trusted commit, recovery, WIC, API, delivery | Initial 262-case run: 260 passed, 1 test-fixture failure, 1 opt-in case skipped; failed case corrected and passed in the final scope run | `delivery-linux-regression-final.log` |
| Final Work/asset/attention/WIC/API regression | 40 passed, 1 opt-in case skipped | `delivery-scope-regression.log` |
| Semantic integration plus delivery | 15 passed, 1 prompt-wording assertion failed, 1 opt-in case skipped; corrected assertion passed on rerun | `delivery-linux-focused.log`, `delivery-semantic-recheck.log` |
| Actual browser pages | Import, create, bind, record target and proposal approval succeed; no page JavaScript errors, preview/download/ZIP hash checks pass | `delivery-ui-final.log`, `delivery-proposal-ui.log`, `delivery-existing-published.log` |

The final delivery tests prove empty-scope Work/semantic input, later multi-asset binding, exact provenance DTOs, independent namespaces, explicit conflicting ref/cross-repo pointer rejection, historical attention no longer blocking a newly admitted basis, unverified publication rejection, exact Markdown/ZIP retrieval, explicit-manifest acceptance, and recovery of A after B is independently bootstrapped. Independent repository B stays unchanged during A's production and recovery.

The earlier Windows and Linux bind-mounted regression runs were interrupted for filesystem latency and are not counted as completed passes. Final Linux tests use isolated temporary source and a dedicated PostgreSQL database. Two real-Provider opt-in tests across the regression groups remain skipped; the separately started real runtime is reported below, not substituted with deterministic Provider results.

Runtime checks found and corrected nullable Work Reality response fields, Refresh busy ordering, illegal WIC reference ambiguity, contradictory resolved/incomplete semantic output, new-document/code-field prompt ambiguity, historical design attention after a Work revision, and CSS overriding hidden forms. Validation did not weaken the exact-source, verification or authorization gates. `git diff --check` and Python compilation pass.


## I. Runtime Acceptance Environment

- Conversation/design: <http://127.0.0.1:8009/app>
- Assets/production/delivery: <http://127.0.0.1:8009/delivery>
- New Work recheck: <http://127.0.0.1:8009/delivery?work=f55ff982-650e-57d7-a863-fe2c1ae11f19>
- Original new Work / preserved verification failure: <http://127.0.0.1:8009/delivery?work=ef7b1e1a-4788-5c75-9595-3a99da100bbb>
- Existing Work: <http://127.0.0.1:8009/delivery?work=9df7358a-9b46-56c0-b60b-f12f3b48f159>
- Health: <http://127.0.0.1:8009/health>

Local single-operator runtime; no login page. Keep access on localhost. Compose project is `watt-delivery-acceptance`, PostgreSQL port 54339 and dedicated `spg_delivery_acceptance` database. The regression database is separate on port 54338. This acceptance development deployment mounts the checkout `src` read-only at `/opt/watt-source`; `PYTHONPATH` selects the reviewed code and UI over the dependency image. Restart the app after source changes. Persistent volumes hold app workspaces/assets, database and Codex state. No actual customer data is used.

The runtime uses existing Codex SDK provider `gpt-5.6-sol` and contract-driven verification. Existing host auth is mounted read-only through `SPG_CODEX_AUTH_FILE_HOST`; no key/auth contents are copied into this report or repository. Executor runs within its container/Attempt workspace. Guardian Core is not implemented and no Guardian approval is claimed.

Reproduce from the repository with Docker available and the existing `.env` auth-path setting:

```powershell
docker compose -p watt-delivery-acceptance -f compose.delivery.yaml up -d --build
docker compose -p watt-delivery-acceptance -f compose.delivery.yaml logs --tail 100 app
```

The startup script upgrades the schema and creates the synthetic existing-repository fixture if absent. Repeating startup preserves assets and Work. Stop with compose `stop`; do not remove volumes to retain acceptance history.

Native Codex browser automation could not start due to Windows `CreateProcessWithLogonW 1385`. The actual pages were checked with local headless Edge/Playwright as fallback; Human can operate the same URLs in a normal browser.

## J. Human Acceptance Checklist

- [ ] Open the existing Work. Inspect its imported repository, observed revision and design agenda.
- [ ] Open the new Work. Confirm it contains design history before its later asset-scope revision; its asset is independent of the inventory repo.
- [ ] To repeat from scratch, clarify a new intent at `/app`, leave the repository selection empty when admitting Work, then create and bind a repository at `/delivery`.
- [ ] Review the bounded document production proposal and its artifact paths before approval.
- [ ] Review the exact Candidate change and authorize repository integration through the existing Attention workflow.
- [ ] Publish the document package from the verified trusted result; inspect and download its exact files and manifest.
- [ ] Compare content with role, state-transition, scope and data-model criteria. A design package is not a deployed operations platform.
- [ ] Enter a reason and choose **接受此交付** or **请求修改**. Confirm the stored identity/reason/decision remains after refresh. Request changes through subsequent WIC conversation for a new cycle.
- [ ] Explicitly tell the implementation task whether the feature itself passes Human product acceptance.

No script has accepted an interactive runtime delivery on behalf of the user. Automatic tests, proposal approval, Candidate authorization, and product acceptance are distinct.

## K. Documentation Updates

As-built multi-repository architecture replaces the obsolete design-pending proposal. This A–L report records implemented scope, limits, evidence, runtime access and Human checklist. AI_context and the main roadmap point to both documents without relabelling earlier foundation checkpoints.

## L. Commit / Push

Commit/push details will be recorded after final validation. Branch: `feature/spg-first-vertical-slice`. Feature acceptance remains **HUMAN PRODUCT ACCEPTANCE PENDING** regardless of repository publication.
