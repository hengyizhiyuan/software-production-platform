# Phase B — Source and Evidence Register

Audit date: **2026-10-09 (Asia/Shanghai)**. Read-only ECS observations below were taken at **04:02–04:17 UTC**. These observations attest deployed identity, not a newly executed Work or Runtime qualification.

## 1. Frozen repository identities

| Source | Exact revision | Role / limitation |
| --- | --- | --- |
| Program Accepted ADR-0002 | `1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1` | [Authoritative decision](https://github.com/hengyizhiyuan/software-production-system/blob/1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1/docs/04-decisions/ADR-0002-STOCHASTIC-NATIVE-ENGINEERING.md); normative, not Runtime proof |
| Program published main | `dd89f79d4e1c59486cb16ca904da75a610f22d3e` | Remote default branch observed |
| Watt main / audit base | `3c367be19d7663b5b9764347b45e6ae355c28e7d` | Published documentation baseline; src/spg identical to ECS canonical source |
| Watt production ECS canonical | `ee5bd86a53891f9391785c91d0ccef81ad2d56c3` | `/data/watt/runtime/source`; clean Git status observed; no update performed |
| N1/GOF evidence branch | `5fd2579f8ab67db12f6ea122048613184276175f` | Local and remote `codex/governed-production-context-convergence-v1`; preserved unchanged |
| Latest N1/GOF application code | `9b3ca2f0b3e298a64ba345229c5856e22be931e5` | Recovery code; retained receipt says no new image, Work or live PASS |
| Last deployed GOF code | `84d16b1f98ee124a4a7fb11761c821e25223ad24` | `watt-n1-gof:84d16b1`, image ID `sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14` |
| Last pre-GOF N1 real qualification | `0d4835353dbdb38abd6abfc19127b84eb5544475` | Image ID `sha256:64289d0a086ecf03efb2dae24ab036bd83906905e00fd71fa30fc51feb160709`; not current GOF qualification |
| ECF published main | `c6b568d006022e39b95daebedfecfb55e562ebe5` | Code baseline `8b2c7b68d6e1752c32050c2042e168b654d8139f`; different managed-context API from N1 export |
| ECF N1 / observed mounted source | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` | Object fetched/read from owner remote; Python source matches ECS mount |
| Guardian published main | `cda2e744ee9027a223a4173faeb9c28829b99a71` | Code baseline `27bf5691e30104bf9a460df29a6f7dd4fb884a30`; Python source matches production mount |
| Guardian N1 owner code | `7cdd58540b59767d9a68a5d16038c06f89059a5d` | Independent governed-obligation resolver is on this unmerged owner branch; Python source matches isolated overlay |

Audit-only branch: `codex/core-production-convergence-phase-b-audit`. Reports are added under `docs/evidence/core-production-convergence-20261009/`. No existing file, main branch, N1 branch or owner branch is changed by this audit.

## 2. Evidence vocabulary

Capability classes: **PROVEN_SCOPED**, **IMPLEMENTED_UNQUALIFIED**, **DEFECT_CONFIRMED**, **CAPABILITY_GAP**, **UNKNOWN**, **DEFERRED**. Scope/revision matters; a class never applies automatically to the whole system.

- **E1**: retained structured actual-run/durable-owner evidence, or this audit's read-only deployed identity. State whether it is retained or newly observed. A narrative citing an event is not an independent database requery.
- **E2**: retained exact-source tests, deterministic integration or scripted fixtures. This audit runs none. Fixture PASS does not prove a real model Work.
- **E3**: exact-revision source/call path, including static composition defects.
- **E4**: architecture intent or narrative not independently corroborated here.
- **UNKNOWN**: necessary historical facts or qualification absent.

Causality is separate: **PROVEN** (specific evidence supports cause), **CONFIRMED_EDGE** (source/contract seam proved, no assertion it caused a historical run), **HYPOTHESIS**, **UNKNOWN**. Existing report grades and historical outcomes remain unchanged.

## 3. Read-only deployed identity

SSH used the existing `watt-ecs` alias without changing authentication/configuration. IMDS returned instance `i-0jl386xnbauudq5j9jk0`, region `cn-wulanchabu`. No token or credentials are included here.

At `2026-10-09T04:02:29Z`, isolated API/Worker/Coordinator/Tool Host all reported `watt-n1-gof:84d16b1` and image ID above. Production roles reported image ID `sha256:bdd1f24a0151533e658ead8ecd7d91368d1352e8288f1f5acfcded05d2ed5562`. This is Docker image identity, not an asserted registry RepoDigest.

At `04:04:19Z`, production and N1 API both mounted ECF from `/data/watt/owners/ecf`; production Guardian mounted `/data/watt/owners/guardian`, isolated Guardian mounted `/data/watt/n1-qualification-20261008/gof-e3de9bf/guardian`. Isolated workspace/app mounts are separate from production. No environment variables or credentials were read/output.

Pure Python byte readers (no application imports, no test execution, no writes) compared Git archives and mounted `.py` files. Algorithm: sort **relative POSIX paths**, aggregate SHA256 over `path UTF-8 + NUL + file SHA256 hex ASCII + LF`.

| Python source set | Files | Aggregate SHA256 / result |
| --- | ---: | --- |
| Production `/app/src/spg` and ECS canonical `src/spg` / Watt main | 252 | `d26a55c4ebe740e32d6c325ca41759eb86a7f855bdb9758233af42ec98d45815`, equal |
| Isolated `/app/src/spg` / Git `84d16b1` | 256 | `dae29a4b4bfeba283f00256609e22777600348286de6ba17223a44f718442b08`; all paths and file hashes equal at `04:15:08Z` |
| ECF mount / Git `5aa4f883` | 5 | `3f3fea2ec06e45917bb6f219f5f172ff0256f893817cdf75ba1f56f2051d6767`, equal |
| Production Guardian / current main | 5 | `0873620a31d1f32d7f8f16b7c964fbe768725796e7f0649ee49dbed1509d4083`, equal |
| Isolated Guardian / Git `7cdd585` | 5 | `c03659155b14e39fd4a26cc7ade394b5136723d918681a87cfc8d9f4ea021fcf`; all paths and file hashes equal at `04:15:09Z` |

An initial local aggregate used a different nested-path ordering. The identical per-file comparison and common POSIX-sort aggregate resolved that measurement discrepancy; it is not a source or Runtime defect. Coverage excludes frontend, dependencies, configuration and migrations; these source hashes alone cannot prove complete image reproducibility or conformance.

The current isolated Worker StartedAt is `2026-10-09T01:00:56.607016088Z`. This predates the last Attempt preparation/rejection (`01:03:52.446511Z` / `01:03:55.715306Z`). The old GOF report's non-overlapping-lifetime assertion lacks original container IDs/timestamps in its retained forensics JSON. This audit records the evidence conflict; neither current timing nor a later successful path probe proves historical filesystem visibility. Historical cause remains UNKNOWN.