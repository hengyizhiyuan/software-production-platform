# Governed Obligation Fulfillment — bounded implementation and truthful stop

Captured 2026-10-09 UTC on Watt ECS `i-0jl386xnbauudq5j9jk0`, `cn-wulanchabu`.
This is a **new** qualification receipt. It is not a replacement for any historical N1 G0–G6 report. Original failed Works, Candidates, Human Decisions, Quality Ledger and production main were not changed.

## Result

**GOF PARTIAL — exact engineering blockers.** The owner binding, current/future obligation split and strict Guardian evidence contract are implemented and pass directed regressions. The required real production-to-verified-Candidate end-to-end qualification did **not** pass. Four new isolated G0 attempts are retained as failures; no Candidate or Verification record was produced. N1 remains PARTIAL and its original qualification remains paused.

Two independent gaps are now visible:

1. The Native Worker rejected a prepared exact workspace before its first execution step. The final two attempts persisted `VERIFICATION_FAILED: workspace unavailable` despite the isolated workspace directory being present when subsequently inspected. A bounded two-second availability wait did not converge. The event cannot establish whether the directory was a symlink, inaccessible, or temporarily invisible at the instant of rejection. No further Work retry is justified without an exact runtime observation at this seam.
2. In the last admitted G0 Work, the original input's deployment and publication prohibitions are present both in an IR `CONSTRAINT` item (`prohibited_effects`) and in ten Work constraints, but its five admitted Engineering Semantic Facts contain only heading, paragraph, cardinality and file-scope facts. The IR's `semantic_fact_candidates` also omit the prohibition. The persisted Completion Contract has **zero** fulfillment bindings. This locates the gap before Engineering Fact admission. The approved Fact-to-Obligation route cannot invent a missing Fact after admission. Existing delivery authorization gates remain independent, but this Work does not demonstrate complete Fact/Obligation traceability. Repair belongs at the existing semantic admission/completeness seam with bounded Self-Refine; do not manufacture a post-admission Fact or silently claim this prohibition was routed.

## Exact identity and isolation

| Item | Identity |
| --- | --- |
| Watt task branch | `codex/governed-production-context-convergence-v1` |
| GOF implementation | `e3de9bf47f3fc7934bccf3e08a10d3ec8b5d3ece` |
| Preflight evidence repair | `3a00dfc3317945ec3b9287f205bab732845e2019` |
| Final tested application code | `84d16b1f98ee124a4a7fb11761c821e25223ad24` |
| Final source archive SHA256 | `154fbdd3e0c7ed3aa989160986d8cef17202ca9e80e2c575bf5ae9bada2cfe3a` |
| Isolated final image | `watt-n1-gof:84d16b1`, `sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14` |
| Guardian owner branch/code | `codex/governed-obligation-evidence` / `7cdd58540b59767d9a68a5d16038c06f89059a5d` |
| Isolated PostgreSQL | `spg_n1_qualification_20261008` |
| Isolated Gitea | `watt-n1-gitea-20261008` |
| Production main (read only check) | `ee5bd86a53891f9391785c91d0ccef81ad2d56c3` |

The four isolated N1 API/Coordinator/Worker/Tool Host roles run the final image. Previous isolated containers remain stopped with `-held-*` suffixes. The Guardian source overlay is the exact separate owner checkout under `/data/watt/n1-qualification-20261008/gof-e3de9bf/guardian`; the formal Guardian export was not changed. No production container was restarted. The isolated workspace volume's root ownership was corrected to UID/GID 10001 after the first attempt's explicit `Permission denied`; no production volume was changed.

## Implemented owner boundary

- `FulfillmentBinding` is a derived, immutable route referencing exact Fact, Work Reality revision, original provenance, source revision, Owner, phase, evidence method and gate. It is not a new Fact, authorization or Assurance verdict.
- Current static content goes through exact Candidate/Git evidence; current continuous prohibitions need persisted Native Attempt permission grants; future Candidate seal and Human delivery/integration obligations remain pending at their existing gates. Unresolved claims fail closed.
- Managed ECF projection checks original Work/IR/ECF identities and passes only relevant current content to bounded static verification. Git Diff, Product Source and lifecycle records use their respective owners.
- Guardian's opt-in `governed-obligation-v1` contract independently resolves persisted Verification, Candidate and Native Attempt owner records. A Watt-only `COVERED` string, stale version, unsealed Candidate or absent evidence does not grant PASS. Legacy requests remain compatible.
- The Worker records a fixed-format preflight rejection before terminal settlement. A pre-effect, two-second workspace availability wait retains exact Git/source, scope, symlink and size checks; the real failure did not converge under that wait.

## Independent regression and negative protection

The final exact Watt source archive ran in a disposable test image against the separate regression database: **67 passed** across GOF binding, Native preflight, static HTML semantics, Protected Context, Candidate assurance and Guardian adapter. The final run used a read-only source mount; the Pytest cache warning reflects that mount. Guardian's exact owner branch previously ran **8 passed** directed contract/runtime cases. Earlier Watt `e3de9bf` source ran 177 directed tests, which are not substituted for the final revision's 67.

The directed cases reject wrong/missing content, wrong file/scope/order, missing Candidate seal, mismatched Guardian source or owner records, forbidden execution capability, wrong workspace, symlink workspace and missing required artifact. These are independent regression results, **not** live G0/G3/G4 Work PASS. An intermediate combined harness run produced three fixture setup errors in `test_managed_greenfield_context.py`; they were excluded from the final 67 and are not counted as PASS. Two legacy-shape Guardian adapter failures exposed by that run were fixed before the final 67.

## Real isolated G0 attempts

All four used an explicitly agent-authored G0 page prompt under the user's isolation qualification authorization. They are not Human Integration Authorization or Delivery Acceptance. The exact persisted IDs, terminal states and preflight event references are in `live-outcomes-read-only.jsonl`; the final Work's source constraints and admitted facts are in `last-work-binding-diagnosis.json`.

| Image | Product / Work | Observed boundary | Candidate / Verification |
| --- | --- | --- | --- |
| `e3de9bf` | `8e21a10c-b044-4b02-a34c-b599265ffb69` / `32d556bb-a940-5f7d-b760-c1093ad256fe` | API orchestration `RepositoryRealityError`: isolated workspace volume root not writable by UID 10001 | 0 / 0 |
| `e3de9bf` | `6210c01b-8062-4f9f-a3c0-7b25911408b7` / `5317c219-8167-581c-aa03-651dd6a7a83c` | Native `UNABLE_TO_COMPLETE` before step 1; old event lacked exact preflight reason | 0 / 0 |
| `3a00dfc` | `527b7ec8-ccfe-49a0-b24a-1ccf8e77fd0e` / `8f8c379b-a9be-55c3-9323-a06fc629a96a` | `ExecutionWorkspacePreflightRejected` event `06da8731-f613-4580-8223-6cbdb3ed0f2a`: workspace unavailable | 0 / 0 |
| `84d16b1` | `7e39eefc-5653-4ed7-90c9-c180479681e9` / `84d7f3a9-b90c-5341-a007-2661fc6399b3` | Same exact signature after bounded wait; event `879cdfb4-77e6-4837-a8af-875563dbb59b` | 0 / 0 |

The Work projection for each stopped trial is `NEEDS_ATTENTION`; the raw `product_works.condition` remains `READY` and must not be read as Work success. No Human choice was fabricated to bypass the stopped Steering step. No Runtime Commit, Manifest or acceptance is claimed.

## G0/G3/G4 scenario coverage and limit

The original G0/G3/G4 persisted cases were read **only** from PostgreSQL. Their exact Work/Revision/Fact IDs, source revisions, Work constraint counts and ECF obligation counts are in `original-scenarios-read-only.jsonl`. They predate GOF and correctly show zero persisted fulfillment bindings; they were not retroactively edited or reclassified as PASS. G3's exact Product V0 Source and G4's ordered content remain governed regression targets. The new G0 attempt stopped before Candidate, so no actual G3/G4 live successor/ordered-list qualification was started. The capability's requested primary end-to-end acceptance is still open.

## Evidence persistence and next boundary

This directory is tracked on the Watt task branch. The same read-only receipts and scripts are retained on ECS under `/data/watt/n1-qualification-20261008/gof-84d16b1/`; exact source archives and all isolated database events remain there. This is the cross-computer recovery location after pushing the branch.

Next work should start from the two observed seams, not from another random G0 Work. First distinguish Worker preflight symlink/access/visibility with exact process and mount evidence without changing a historical Work. Then repair upstream semantic admission so explicitly stated prohibitions either yield an admitted Fact with provenance or prevent Work readiness through bounded existing Self-Refine. Only after both are verified should one new exact-image G0 end-to-end Work be attempted, followed by G3/G4 capability qualification. N1 original G0–G6 and 23 Closure Conditions remain unchanged and paused.
