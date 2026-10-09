# C3 capacity repair — recovery and delivery

## Versioned evidence

Repository branch: `codex/c3-open-semantic-obligation-convergence`. Frozen application source: `e0df8196cb51480f542af13b40cfa77fca6b6a6e`, tree `d479d61f5fcac075a5af3a274f60cbe3f6e9f53f`. Later evidence-only commits do not change this tested application. Source baseline `e8e04b296b31d776a13dda728fa19469681cbaab`, prior evidence `6fbc692de4696ff5a1b9ea3073fe4c42bc405292` remain ancestors.

After cloning this branch on another computer, read [Capacity & Representation Review](capacity-and-representation-review.md), [final image](final-image/build.json), [actual imports](final-image/actual-imports.json), [191-test receipt](final-image/watt-continuation-receipt.json), [actual wire measurement](exact-wire-measurement-1/actual-compact-wire-measurement.json), [PG receipt](owner-pg-retry-1/receipt.json), and [live-model decision package](live-model-decision-package.md). The failed baseline and development/setup attempts remain in the same directory.

## ECS durable recovery positions

Host: existing verified SSH alias `watt-ecs`; task root `/data/watt/c3-semantic-convergence-20261009`.

| Material | Persistent position |
|---|---|
| This round's evidence | `capacity-representation-20261009/` below task root |
| Complete public delivery snapshot and file-hash manifest | `public-delivery-c3-capacity-e0df819-20261010/capacity-representation-20261009/` |
| Remote push verification (written after the evidence commit) | `capacity-representation-20261009/remote-delivery-verification.json` on ECS; excluded from the preceding snapshot to avoid a self-referencing commit |
| Frozen source/Owner input archives, hashes and controls | `capacity-final-inputs/` |
| Qualified image | `watt-c3-capacity:e0df819`, actual ID `sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35` |
| Exact image archive | `capacity-representation-20261009/image-recovery/exact-image.tar.gz` |
| Retained original inventory basis | `public-delivery-c3-final/retry-1/g0-owner-2/20261009T130020024208Z-2fc7b990c1b54846a25bd067bc94b849-canonical-work.json` |
| Qualified isolated fixture cluster and Docker volume | `watt-c3-capacity-owner-pg-retry-1-20261010` (stopped; internal network; no host port) |
| Fixture credentials, excluded from Git/public reports | `capacity-representation-20261009/owner-pg-retry-1/private/` (`0600` files) |
| First setup-failure cluster/volume | `watt-c3-capacity-owner-pg-20261010` (stopped, preserved) |

Image archive SHA256: `35576c81785997c4ff1e6d347671bdf283b0f38323875e3218affffbca8f4949`; 293,129,132 bytes, mode `0600`. [Archive receipt](image-recovery-receipt.json) records the actual image and source. Restore and offsite-copy qualification were **NOT PERFORMED**. These are retained recovery materials, not a claimed disaster-recovery PASS.

For a later isolated recovery, first verify the archive hash, then load it with `docker image load --input <exact-image.tar.gz>` and verify the resulting image ID. Check the source/Owner hashes and exact imported identities before qualification. Do not start or reuse production services, attach production volumes, or reset the original failed Work. Fixture credentials remain on ECS; they are not needed to read Git evidence or the aggregate reports.

## Protection observations

At the end of this scoped work, read-only observations still show ECS `refs/heads/main=ee5bd86a53891f9391785c91d0ccef81ad2d56c3` and its independent checkout HEAD `5de657f3cb65780adf50f6557b54171a6c3cfae5`. Remote `main=5b7bf217937d7e002c0264c3fe9fdd518dba152c` matched this round's earlier observation. These are different refs; this task performed no merge, deployment, production restart or original database write.

No Guardian/ECF source changes, Holdout access, new G0, Human Integration/Acceptance, Quality Ledger mutation or C4/N1/N3 work occurred. Actual model calls this round remain zero until the explicit live-model gate is answered.
