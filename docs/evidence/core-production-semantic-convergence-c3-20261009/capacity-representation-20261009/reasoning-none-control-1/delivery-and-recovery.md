# C3 reasoning-none control — delivery and recovery

Branch: `codex/c3-open-semantic-obligation-convergence`. Starting evidence HEAD: `61f77ff62af5176fdf0e7870df7601cb12b58d1c`. This continuation changes evidence only; application source remains `e0df8196cb51480f542af13b40cfa77fca6b6a6e`, tree `d479d61f5fcac075a5af3a274f60cbe3f6e9f53f`, actual image `sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35`.

After cloning this branch, read [Architecture Lead submission](architecture-lead-submission.md), [actual result](reasoning-mode-result.json), [Candidate review](candidate-integrity-review.json), [authorization](authorization.json), and [public manifest](public-file-manifest.json). Previous low-profile receipts and all earlier evidence remain unchanged.

SSH alias: `watt-ecs`. Task root: `/data/watt/c3-semantic-convergence-20261009`.

| Material | Retained position under task root |
|---|---|
| Original public execution receipts | `capacity-representation-20261009/reasoning-none-control-1/evidence/` |
| Strict controls | `capacity-final-inputs/reasoning-none-control-1/` |
| Complete public delivery snapshot | `public-delivery-c3-reasoning-none1-20261010/reasoning-none-control-1/` |
| Public archive | `capacity-final-inputs/public-delivery-c3-reasoning-none1-20261010.tar.gz` |
| Post-push verification | `capacity-representation-20261009/reasoning-none-control-1/remote-delivery-verification.json` (written after commit; no self-referencing commit) |
| Private safe Candidate, expanded/located Candidate, execution logs and provider-only credentials | `capacity-representation-20261009/reasoning-none-control-1/private/` (`0600`; excluded from Git) |
| One-shot guard | `capacity-representation-20261009/reasoning-none-control-1/execution-started.json` |
| Existing exact image archive | `capacity-representation-20261009/image-recovery/exact-image.tar.gz`; SHA256 `35576c81785997c4ff1e6d347671bdf283b0f38323875e3218affffbca8f4949` |

The preflight and live diagnostic containers are exited and retained. This is not a Work checkpoint to resume: the Human-authorized call has been consumed, Candidate failed, Review was not run, and no Owner was changed. Do not replay the execution marker or automatically request another candidate.

The public snapshot is hash-checked and scanned for known credential literals before push. This is not a universal privacy or restore qualification. Restore and offsite-copy qualification remain NOT_PERFORMED. Private evidence stays on the verified ECS and can be read securely on another computer with authorized SSH access; it is not in public Git evidence.

The remote receipt records the exact pushed evidence HEAD and empty application/test delta, plus unchanged remote main and ECS canonical main observations. No merge, deployment, production model configuration change, original Work/Owner/Human/Quality record mutation or Holdout access occurred.
