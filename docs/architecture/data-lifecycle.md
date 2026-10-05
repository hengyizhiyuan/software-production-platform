# Watt Production Infrastructure Data Lifecycle v1.0

Status: **policy baseline with current-state distinctions**. The current ECS
has a 100 GB `/data` disk, with Docker, PostgreSQL, Watt runtime and update
logs placed there. Disk use is inspectable with
[`inspect-disk.sh`](../../deploy/cloud-worker/inspect-disk.sh). The existing
[`cleanup-docker.sh`](../../deploy/cloud-worker/cleanup-docker.sh) is an
operator command, not an automatic scheduler or a backup mechanism.

| Class | Examples and current home | Retention/cleanup rule | Authority |
| --- | --- | --- | --- |
| Transaction data | User, Product, Work, Task, Decision Context, authorizations, queue/lease and authoritative records in `/data/postgres` | Long-lived; no age-only deletion. Backup and governed retention/migration decisions precede removal. | Product/Data owner and applicable governance policy |
| Execution data | Attempts, Worker/Tool receipts, checkpoints and logs in PostgreSQL or `/data/watt`/Docker logs | Preserve evidence needed for active Work, retry, review and audit. Apply class-specific retention only after reference and legal/policy checks; compact or archive eligible bulky logs separately from authoritative records. | Execution/assurance record owner |
| Artifacts | Generated files, builds, images, referenced workspaces | Keep exact identity, source revision, Work/Attempt and verification lineage. Later move immutable large artifacts to object storage with checksum and reference migration before local deletion. | Artifact/Work owner |
| Temporary data | Build cache, unused test images/containers, disposable workspaces | Bounded cleanup after age and active-reference checks. Never prune running containers, volumes, current images or referenced evidence merely to free space. | Runtime operator plus resource owner |

The existing native workspace policy has 30-day hot and 180-day cold defaults
with pin, review and recovery guards; Candidate Preview has a separate
review-aware hot period. See
[Production Environment Architecture](watt-production-environment-architecture.md).
These are **not** blanket retention limits for all execution records or
transaction data. The complete cross-provider reference graph and automatic
garbage collector are not implemented.

## Bounded disk hygiene

- Docker local logs are configured at 10 MB × 3 files per container in the
  current Compose deployment. Update logs under `/data/logs` are eligible
  for deletion after 14 days by the existing cleanup command.
- The existing command prunes build cache older than 7 days with Docker's
  `--keep-storage 5GB` setting, plus dangling images and stopped containers
  older than 7 days. This is not a hard 5 GB cache quota. It does not touch
  volumes or running resources. Schedule/automation is a future operations
  decision; record every run and inspect candidates first.
- Before deleting a workspace, generated artifact, receipt or test image with
  possible Work/Evidence references, evaluate the resource-specific retention
  owner. Age alone does not establish that it is disposable.

## Monitoring requirement

Record daily `/data` free bytes and inode availability, Docker image/cache/log
sizes, PostgreSQL size/growth, `/data/watt` size and oldest cleanup-eligible
objects. Proposed operational thresholds for this 100 GB node: investigate
at 70% usage, schedule bounded cleanup/capacity action at 80%, and stop new
large builds at 90% until space is proven safe. These are design thresholds,
not an installed alert or enforcement mechanism. Alerts need an owner and
runbook before being called operational.

No local cleanup substitutes for an off-host backup. Machine loss and data
restore are addressed in [operations.md](operations.md).
