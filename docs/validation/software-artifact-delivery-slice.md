# Software Artifact Delivery Vertical Slice

Date: 2026-09-10. Base: `7c349af91649a58f06e9ae42961fbb906e54a20a`.

**IMPLEMENTED / AUTOMATED VALIDATION PASS / RUNTIME READY / HUMAN PRODUCT ACCEPTANCE PENDING.** Human product acceptance has not been granted; this mission is not marked COMPLETE.

## A. Architecture Changes

Extend the existing Work → Guided Design → Steering → single PWU → Executor → independent Verification → Candidate authorization → trusted Runtime Commit → Delivery chain. No Work, Asset, Steering, SPG/PWU, Executor ownership, Verification ownership or Human Authority redesign. Guided Design's admitted result summaries are now included in Code Work production objectives as well as document objectives.

The new software delivery category is separate from its software form and runtime adapter. The first adapter is a dependency-free static Web application. API services, CLI tools, libraries and other forms can acquire separate adapters; this slice does not claim they run on the static adapter.

## B. Software Artifact Delivery Model

`SOFTWARE_ARTIFACT` is a first-class Delivery Target kind. A typed `software_form` and `runtime_recipe` describe the delivered form and how the supported runtime opens it. The first supported combination is `WEB_APPLICATION` + `STATIC_WEB` with an exact HTML entrypoint. Arbitrary host shell commands are not accepted.

Software publication requires the current Work Reality and exact bound Code Work cycle, trusted Runtime Commit, matching PASS records, an independently executed Node/Python test obligation, a software file change, README and declared entrypoint. Merely creating a document or passing a diff check is insufficient.

The manifest records repository/ref, source and delivered commit, commit message, changed files, full Verification records, runtime recipe, reproduction instructions and every exported file's hash/size. It packages the entire bounded exact Git tree, including unchanged dependencies/context needed to reproduce the software. Regular blobs only, immutable commit only, no working-tree reads, links/submodules/traversal rejected. Limits remain 1 MiB/file, 10 MiB/package, with 500 files for software. This MVP requires no dependency download/build.

ZIP exports contain `source/`, `DELIVERY_README.md`, `delivery-manifest.json`, `delivery-target.json`, and `verification.json`. Fixed ZIP metadata makes repeated downloads byte-identical for the same manifest. Existing Document Package targets, manifests, fingerprints, previews and acceptance remain supported; target choice remains immutable per Work.

Runtime instances use independent local ports/origins for each manifest, preventing shared browser storage with Watt or another delivered version. The static adapter serves exact manifest-verified bytes, permits only packaged web resources, disables arbitrary network connections/inline scripts through CSP and validates Host. A new persistence table records runtime identity/recipe/startup HTTP evidence; it does not alter production state. On app restart it restores those instances and revalidates their bytes. API readiness always performs a fresh exact-entrypoint HTTP probe; a stopped/failed runtime is not reported ready.

This is a local single-operator, single-app-process acceptance adapter with ten reserved ports, not an enterprise deployment system. Old instances keep their ports and browser data. The slice does not provide remote hosting, backend hosting, IAM, dependency installation, mobile packaging, CI/CD or a Docker registry.

## C. Existing Repository Flow

The explicit synthetic existing repository is a clone of the newly generated runnable inventory application at `517f00fac33903b5920e303c31487895d3487b6d`, imported through the actual asset UI. The baseline application was produced by the real Executor, not hand-written to substitute for production. The separate Work requests CSV export of the currently filtered list, UTF-8 BOM and correct comma/quote/newline escaping while retaining all existing features.

Interaction: `62fe3cbb-231c-4c64-94bb-39d360d23843`.
Work: `e83aa306-599a-5b0d-b992-1fda06b916ee`.
Repository: `/var/lib/spg/repository-imports/inventory-software-existing`.
Resource: `93ddcb46-202d-49c6-9bcd-edfff8ff3e49`.

This Work selected the existing repository at admission and completed all seven Guided Design issues. Its first Executor invocation returned `UNKNOWN`: “Selected model is at capacity. Please try a different model.” Attempt `297132ec-4f54-4e85-a6ad-bba86c9ded1a` has no workspace changes, Candidate or delivery. The immutable failure remains visible; no PASS or retry authority was manufactured. The existing recovery classifier does not permit same-Attempt retry for UNKNOWN. Automatic transient-capacity recovery is outside this slice.

A separately admitted synthetic recheck repeats the normal full flow on the same unchanged trusted source: Interaction `290d0327-2bf6-4961-b268-2211a44a5788`, Work `63e03b3a-6815-56d0-a60c-22a0858432eb`. The recheck completed all seven design issues, the real Executor, independent Verification and exact Candidate authorization. It now delivers the working CSV improvement; evidence is recorded in F.

## D. New Work Flow

Mandatory input: “我要开发一个简单库存管理系统。支持商品管理。支持库存数量维护。支持低库存提醒。单用户即可。” Synthetic clarification specifies a dependency-free browser application, unique product IDs, nonempty names, nonnegative integer quantities/thresholds, strictly-below low-stock rule, CRUD, search/filter and local browser persistence. It explicitly requires code, Node tests, a runnable URL and Human acceptance, not a document-only substitute.

Interaction: `6cf73751-bc40-4323-b3f5-9fc3e1e82590`.
Work: `2faf6ae7-4fae-544b-826f-54a682c8c7bf`.
Repository: `watt://repositories/7c31e852-cf26-4518-a96e-a0dde85689bc`.
Resource: `880ca511-e277-476c-bacb-f761f97171d0`.

The real WIC admitted Work before any repository binding. Guided Design completed early issues without a repository. The actual delivery UI then created and bound a new independent repository. Only a generic README was initialized by asset intake; all application implementation and tests were subsequently generated by the real Executor, not manually planted into its repository.

## E. Production Execution Flow

Review the precise CODE_WORK proposal and executable test obligations before production approval. The existing production chain owns code execution, tests, Candidate sealing/authorization and trusted integration. Software delivery observes that result; it cannot authorize a Candidate, bypass Verification, or claim a new Runtime Commit.

Delivery publication and runtime startup remain distinct. A Human may inspect source, change/verification evidence, download the package, start/check the exact runtime, operate the generated software and record ACCEPT or REQUEST_CHANGES against the current manifest. ACCEPT requires a live matching runtime. REQUEST_CHANGES remains possible if the software is unavailable. Recorded decisions are immutable and idempotent; stale Work/cycle manifests cannot receive new acceptance.

## F. Code Delivery Evidence

New software real Provider evidence:

- Repository: `watt://repositories/7c31e852-cf26-4518-a96e-a0dde85689bc`, managed path `/var/lib/spg/repository-assets/7c31e852-cf26-4518-a96e-a0dde85689bc`.
- Source commit: `c5f26feb91a34a8a6d215128dca180a8a9fa596b`.
- Delivered commit: `517f00fac33903b5920e303c31487895d3487b6d`.
- Commit message: `SPG proposed repository snapshot`.
- Runtime Commit: `2ef981b9-6081-5122-9e1e-78fbe6f10c85`.
- Manifest: `b17f8a86-51ad-5e2a-8ebc-328398681354`, fingerprint `574f21960d6ceed24e3a16c74eb8d77ca857fac3b0dcc788023ee91d132001f5`.
- Changed files: CREATE `index.html`, `style.css`, `inventory.js`, `app.js`, `tests/inventory.test.cjs`; UPDATE `README.md`.
- Independent PATH_SCOPE, GIT_DIFF_CHECK and NODE_TEST_TARGET all PASS, bound to the exact delivered commit. The seven generated Node tests were rerun from the downloaded ZIP in a separate container with networking disabled: 7 PASS, all six file hashes/sizes match.
- Actual browser: ten groups covering empty state, CRUD, duplicates/blank names/negative and fractional quantities, strict threshold boundary, search/filter, inert rendering of HTML-like product text, refresh persistence and delete cancellation/confirmation. Zero page JavaScript errors. Screenshot visually inspected.
- Evidence: `software-new-published.json`, `software-new-functional.json`, `software-new-reproduced.log`, `software-new.zip`.

Existing software real Provider recheck evidence:

- Repository: `/var/lib/spg/repository-imports/inventory-software-existing`; managed path `/var/lib/spg/repository-assets/c8c0feaf-3d00-4a80-ab80-e11563754c25`.
- Source commit: `517f00fac33903b5920e303c31487895d3487b6d`.
- Delivered commit: `ea082ac84904adbd371cdee8d84f0dcd9b19ddc7`; message: `SPG proposed repository snapshot`.
- Candidate: `adfd9de8-7306-53c5-9ef8-c4bf50fab805`, inspected before exact integration authorization.
- Runtime Commit: `1d505c4a-eae0-5a45-a780-2830b5a06877`.
- Manifest: `7f26d087-720d-59f1-ab18-cf11bfd92eec`, fingerprint `0c51ec02143fb602becfc6cbd19680c1099c457259c0c580cca27ffa5fd90e29`.
- Changed files: UPDATE `index.html`, `inventory.js`, `app.js`, `tests/inventory.test.cjs`, `README.md`; 17 insertions / 6 deletions. `style.css` unchanged.
- Independent PATH_SCOPE, GIT_DIFF_CHECK and NODE_TEST_TARGET all PASS at the exact commit. Verification IDs: `e4db42a9-20e0-507e-bdca-5e15ad528b65`, `1e0d7187-7e3a-5adc-bafc-28e40403808c`, `9e67807d-807e-56c4-84b8-ec782f9a5723`.
- Downloaded ZIP: all six source hashes/sizes match; all 10 Node tests passed again in a separate container with networking disabled, including BOM/column order and comma/quote/newline escaping.
- Actual browser: all ten original inventory regression groups passed. Seven additional CSV groups passed: real BOM/Chinese/comma/quote download round trip, ID search, name search, low-stock filtering, combined filtering, explicit empty-result feedback without download and unchanged persisted products. Zero JavaScript page errors. Screenshot visually inspected.
- Evidence: `software-existing-published.json`, `software-existing-functional.json`, `software-existing-csv.json`, `software-existing.zip`.

Both repositories coexist with the two previous document repositories. After final app restart, both software URLs return the exact entrypoint bytes and manifest identity; manifests and repeated source ZIPs are byte-identical to their published evidence. Both previous document manifests and artifacts remain unchanged. The original new-software repository still points to `517f00fac33903b5920e303c31487895d3487b6d`; the CSV continuation advances only its independently imported repository. The acceptance database contains zero Human acceptance decisions. See `software-restart-check.json`.

Local validation material is under `.spg/validation-evidence/`; no credentials or real customer data are included in tracked reports or synthetic tasks. WIC/Guided Design use the configured real `gpt-5.6-sol` Provider; the dedicated Executor is the real Codex SDK adapter (its report labels the model selection `sdk-default`). The capacity failure remains failed evidence, separate from the successful recheck.

## G. Runtime Acceptance Environment

Watt: <http://127.0.0.1:8009/app> and <http://127.0.0.1:8009/delivery>.
New Work: <http://127.0.0.1:8009/delivery?work=2faf6ae7-4fae-544b-826f-54a682c8c7bf>.
Generated new inventory application: <http://127.0.0.1:8010/index.html>.
Existing application with CSV export: <http://127.0.0.1:8011/index.html>.
[New application source ZIP](http://127.0.0.1:8009/api/works/2faf6ae7-4fae-544b-826f-54a682c8c7bf/deliveries/b17f8a86-51ad-5e2a-8ebc-328398681354/download).
[CSV application source ZIP](http://127.0.0.1:8009/api/works/63e03b3a-6815-56d0-a60c-22a0858432eb/deliveries/7f26d087-720d-59f1-ab18-cf11bfd92eec/download).
Existing-software recheck Work: <http://127.0.0.1:8009/delivery?work=63e03b3a-6815-56d0-a60c-22a0858432eb>.
Preserved capacity failure: <http://127.0.0.1:8009/delivery?work=e83aa306-599a-5b0d-b992-1fda06b916ee>.

The existing `watt-delivery-acceptance` Compose project remains available. Ports 8010–8019 are published only on host localhost. `SPG_DELIVERY_RUNTIME_ENABLED=true` enables the adapter; the container binds its reserved ports internally and maps them to localhost. The source and migrations are read-only checkout mounts for this acceptance development environment. Existing auth-path configuration is reused without exposing credentials.

```powershell
docker compose -p watt-delivery-acceptance -f compose.delivery.yaml up -d --build
```

At the Work delivery page: publish from the verified trusted result, click “启动 / 检查此版本的软件”, then “打开软件进行验收”. Download the source package for offline inspection and follow its README/reproduction instructions. Browser data belongs to the specific delivered origin/version and browser profile; new versions do not silently migrate localStorage.

## H. Human Acceptance Checklist

- [ ] Open the new inventory software URL; confirm it is an operable application.
- [ ] Create a product with a unique ID, name, quantity and threshold.
- [ ] Edit product details and inventory; check strictly-below, equal-to and above-threshold behavior.
- [ ] Search by name/ID and toggle the low-stock filter.
- [ ] Reload; confirm the product and quantity persist in this browser.
- [ ] Try blank names, duplicate IDs, negative/noninteger quantities; verify rejection and clear feedback.
- [ ] Cancel then confirm deletion; verify the respective outcomes.
- [ ] Open the CSV version. Add two products (one below its threshold, one at/above), search and filter, then export. Confirm only the displayed products appear; a name containing a comma and double quote must remain a single field. No matching products should show a message without downloading.
- [ ] Inspect repository/commit/changed files and independent test evidence; download and reproduce from source.
- [ ] At the exact Work delivery page, explicitly select Accept Delivery or Request Changes with a reason.
- [ ] Separately tell this implementation task whether the feature passes Human product acceptance.

No automated browser script records Human acceptance in the real acceptance database. Test-only acceptance records belong to a separate PostgreSQL database.

## I. Automated Validation

- Complete non-integration suite: 370 passed (`software-unit-all.log`).
- Final PostgreSQL/Git/Node/HTTP software, previous document/multi-repo, WIC and API regression: 44 passed, 1 opt-in Provider test skipped (`software-integration-final.log`).
- Earlier focused suite: 50 passed; initial integration suite: 7 passed.
- Software test fixtures prove exact Code Work → independent Node verification → trusted commit → full source package → repeatable ZIP → Node test rerun from extracted package → real HTTP runtime → restart restoration → explicit test-only acceptance. A deliberately incorrect threshold implementation fails the executable test and cannot publish.
- Runtime/path tests reject traversal, Git internals, links, forged Host and host-command recipes. Previous populated namespace migration and multi-repository history tests continue to pass.

The skipped opt-in case is reported separately from this mission's real Provider application generation. Both successful real Provider software runs, offline source reproduction, browser checks and final persisted runtime probes are recorded in F. One earlier real Executor capacity failure remains explicitly recorded in C.

Independent functional acceptance uses actual browser actions, including invalid inputs and threshold boundaries; generated tests alone are not treated as proof of the product outcome.

## J. Documentation Updates

This A–K report describes the as-built extension, runtime limits, real software evidence and Human checklist. Previous slice report remains a historical description of the document-only milestone. AI_context and the roadmap link this extension as implemented, automated validation passed, runtime ready and Human acceptance pending. They retain the documented adapter limits.

## K. Commit / Push

Implementation commit: `6fec4ed2f5383419b92b7078f93599b5de8023ff` (15 code/config/migration/test files). This report, AI_context and roadmap are a separate evidence commit. Branch: `feature/spg-first-vertical-slice`. Destination: `https://github.com/hengyizhiyuan/software-production-platform.git`.

**Push pending:** automatic approval review rejected the normal push twice. The second attempt supplied the earlier same-task explicit destination confirmation; the review still treated retrieved history as untrusted authorization evidence. No push workaround was used. The final handoff supplies both concrete commits for a fresh destination-specific confirmation. Local `.spg` runtime evidence, generated application repositories, auth material and customer data are excluded from the platform push. Generated source remains downloadable from the two exact local delivery URLs above.

Human product acceptance remains pending independently of source publication.
