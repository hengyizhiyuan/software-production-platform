# C3 authorized live observation — delivery and recovery

Branch: `codex/c3-open-semantic-obligation-convergence`. This continuation changes **evidence only** after evidence HEAD `31e29d8ff7ee82f3149625ddd5dbab688fb65095`. Frozen application source remains `e0df8196cb51480f542af13b40cfa77fca6b6a6e`; actual image remains `sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35`. Guardian and ECF source are unchanged.

## Cross-computer evidence

Clone this branch and read [Architecture Lead submission](architecture-lead-submission.md), [result](live-model-result.json), [authorization](authorization.json), and [public-file manifest](public-file-manifest.json). Prior public snapshots and all failed attempts remain unchanged.

Verified ECS SSH alias: `watt-ecs`. Root: `/data/watt/c3-semantic-convergence-20261009`.

| Material | Retained position under root |
|---|---|
| Actual original result and before/after container observations | `capacity-representation-20261009/live-model-verification-1/evidence/` |
| Controller inputs | `capacity-final-inputs/live-model-verification-1/` |
| Complete public delivery snapshot | `public-delivery-c3-capacity-live1-20261010/live-model-verification-1/` |
| Public archive | `capacity-final-inputs/public-delivery-c3-capacity-live1-20261010.tar.gz` |
| Post-push remote verification receipt | `capacity-representation-20261009/live-model-verification-1/remote-delivery-verification.json` (written after the evidence commit; not part of that commit) |
| Protected provider-only credential and execution logs | `capacity-representation-20261009/live-model-verification-1/private/` (not in Git; `0600` files) |
| One-shot execution marker | `capacity-representation-20261009/live-model-verification-1/execution-started.json` |
| Qualified exact image archive | `capacity-representation-20261009/image-recovery/exact-image.tar.gz`; SHA256 `35576c81785997c4ff1e6d347671bdf283b0f38323875e3218affffbca8f4949` |

The isolated preflight and live containers are exited and retained. No Candidate file was generated, no Semantic Review was entered, and there is no Work/Owner checkpoint to resume from this diagnostic. The execution marker and prior-result guard prevent automatic repeat. Recovery means reading and verifying the retained evidence; **this authorization must not be replayed**.

Public delivery hashes and known-secret literal absence are checked before pushing. This is not a universal privacy proof. Restore/offsite backup qualification was not performed. The existing exact image archive and earlier source/Owner inputs remain available; no rebuild was needed for this evidence-only continuation.

The final remote receipt records exact pushed evidence HEAD, application-source delta (empty), public archive hash, ECS main and remote main observations. Neither main is merged or deployed. There are no changes to original Work, Candidate, Human Decision, Quality Ledger or sealed Holdout.
