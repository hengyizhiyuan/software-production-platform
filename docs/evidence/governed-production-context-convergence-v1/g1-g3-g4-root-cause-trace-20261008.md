# N1 G1/G3/G4 root cause and semantic trace — 2026-10-08

Status: **PARTIAL**. This is a new investigation receipt, not a replacement for the older qualification reports. Sources are persisted isolated ECS PostgreSQL rows, immutable Git objects, read-only Candidate replay, and new regression runs. E1 means a directly persisted fact; E3 means a new code-path reproduction. Neither turns an old Verification record into a new PASS.

## G1 — exact document lineage

E1: Work `ae8530f0-1f28-55f7-aea6-e79b13c7fabd` admitted a document objective naming its Work ID, Semantic IR `9a88e343-6c62-5b30-af81-83594b03e171`, governance IDs `f4a91c10-1d27-57c5-9617-2220b916b33b` and `efb0a35b-a549-4f3e-ae94-9fcf75d68724`, source baseline, source revision and source tree. Its verification expectation requires exact source/Work lineage identifiers to appear. PWU `12e183d1-581a-4d70-bd01-e0edbc1aac4b` saved `required_markers=[]`. Thus admission failed to convert a mechanically checkable Work obligation into CompletionContract markers. RepositoryArtifactVerifier then checked `all(...)` over the empty tuple and allowed PASS. The old sealed Candidate `7d410081-4319-5529-a12e-ce844f9d9ac2` omits the three IDs above; old Verification `b10a6b32-faad-5982-8b29-cdd89940c116` remains historically PASS but is materially unsound for the full Work Contract. No Human Integration Authorization should be requested for it.

Repair: document admission extracts literal UUID/SHA lineage from the **admitted Work objective**, only when its verification expectation explicitly requires exact identifiers in the document. It rejects such an expectation if the admitted objective supplies none. CompletionContract stores the exact markers; the Worker instruction already renders them; Artifact Verification checks each marker against the immutable Git blob with token boundaries. It also consumes the admitted Human `document.sections` ordered fact. E3 negative regression omits the Semantic IR ID and yields `required_markers_present=false`, overall FAIL; reversed sections also FAIL. A read-only replay of the old Candidate with the reconstructed seven markers gives FAIL without changing that Candidate or its original Verification row. A fresh legal Work/Candidate on the final exact image is still required.

## G3 — accepted Product source identity

E1: the new non-new Work `1043ffa0-04b0-5147-8367-fef5858b2e56` came from a Human phrase “the currently accepted Product V0 source.” WIC correctly typed the phrase as a repository-required source reference, but left its provenance `HUMAN_EXPLICIT` and its value as natural language. Existing managed-source context requires an exact `REPOSITORY_OBSERVED` Product source identity, so the Work obtained no Runtime binding. Product Reality already held an accepted V0 repository identity and exact accepted revision/tree. A later turn referring to `status.html` rather than the original `health.html` is a distinct scope change and correctly did not produce a governed change.

Repair: after typed semantic validation, resolve only the accepted-Product source role against persisted `product-managed-source` observations with a matching owner evidence reference and accepted revision. Exactly one matching V0 source produces an observed repository identity; none or multiple leaves the source unresolved for Human clarification. External URLs and generic “existing source” text are unchanged. E3 regression covers unique, missing, ambiguous and external references. This is source binding within the existing Product owner contract; it does not weaken exact accepted revision/tree checks. A fresh successor/non-new Worker Work on the final image is still required.

## G4 — F01–F14, item by item

E1: Human record `367c2a56-0c4d-413b-b69f-63706e11eb1d` contains 14 ordered required lines. Assessment `5e4f0cc9-9ddd-4f2a-983c-7784eb1acdfd` and admitted Work revision `086d51b6-23cd-54d9-a1f7-0a3f8a8cdeff` preserve their exact values as the typed `page.ordered_list.items / ORDERED_COMPONENT` Human fact `45452139-afde-555f-a409-794f0e69b610` scoped to `index.html`, with count 14 and source provenance. Work `4a9f9064-d307-5261-a1c5-e734a52db4bf` has nine summary constraints; these are not fourteen independent facts, but the typed ordered fact retains all fourteen values without semantic merging. PWU `ff999ad9-ecca-4456-b08e-9977fe47eb46` CompletionContract and Task Contract reference this fact, and the rendered Worker instruction contains each exact line once. No context budget or protected source was removed.

| Human item | Admitted ordered value | WIC/IRK/Work | PWU/Task/Context | Candidate Verification after repair |
| --- | --- | --- | --- | --- |
| F01 | `F01: N1 protected fact 01` | exact element 1/14 | ordered fact element 1/14 | exact `li` position 1 |
| F02 | `F02: N1 protected fact 02` | exact element 2/14 | ordered fact element 2/14 | exact `li` position 2 |
| F03 | `F03: N1 protected fact 03` | exact element 3/14 | ordered fact element 3/14 | exact `li` position 3 |
| F04 | `F04: N1 protected fact 04` | exact element 4/14 | ordered fact element 4/14 | exact `li` position 4 |
| F05 | `F05: N1 protected fact 05` | exact element 5/14 | ordered fact element 5/14 | exact `li` position 5 |
| F06 | `F06: N1 protected fact 06` | exact element 6/14 | ordered fact element 6/14 | exact `li` position 6 |
| F07 | `F07: N1 protected fact 07` | exact element 7/14 | ordered fact element 7/14 | exact `li` position 7 |
| F08 | `F08: N1 protected fact 08` | exact element 8/14 | ordered fact element 8/14 | exact `li` position 8 |
| F09 | `F09: N1 protected fact 09` | exact element 9/14 | ordered fact element 9/14 | exact `li` position 9 |
| F10 | `F10: N1 protected fact 10` | exact element 10/14 | ordered fact element 10/14 | exact `li` position 10 |
| F11 | `F11: N1 protected fact 11` | exact element 11/14 | ordered fact element 11/14 | exact `li` position 11 |
| F12 | `F12: N1 protected fact 12` | exact element 12/14 | ordered fact element 12/14 | exact `li` position 12 |
| F13 | `F13: N1 protected fact 13` | exact element 13/14 | ordered fact element 13/14 | exact `li` position 13 |
| F14 | `F14: N1 protected fact 14` | exact element 14/14 | ordered fact element 14/14 | exact `li` position 14 |

The common WIC/IRK/Work and PWU/Task entries in each row refer to the same lossless ordered fact, not to fourteen separately admitted Work constraints. The historical Candidate `c1cd623c-f5e7-54fe-b26d-a9dd1bac91de` happens to contain the fourteen lines and its old PATH_SCOPE/GIT_DIFF records PASS. That alone was insufficient evidence because RepositoryCodeVerifier did not mechanically consume the semantic fact values. The repaired consumer reads the immutable proposed Git `index.html`, checks the unique H1 and exact ordered `li` tuple, count, order and no duplicate text outside the list. It binds the acceptance assertion to that ordered fact and fails closed on unsupported scope/profile. E3 negative tests remove F07, swap F07/F08, duplicate F01 in or outside the list, or omit the ordered source fact; all FAIL. Read-only replay of the old Candidate against the new consumer passes its three supported checks but leaves its historical Verification records unchanged. Fresh live qualification on the final image is pending.

No claim here establishes fourteen independent ECF protected facts, complete G4 Work PASS, or N1 Closure. The exact final source/image identity and new live event IDs must be appended in a later receipt.
