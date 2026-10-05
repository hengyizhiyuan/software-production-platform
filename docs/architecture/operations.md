# Watt Production Infrastructure Operations Strategy v1.0

Status: **operational design**, anchored to the [current ECS runtime](runtime-baseline.md).
The single-ECS qualification proved Compose restart and on-disk persistence;
it did **not** prove off-host backup, new-ECS restore or high availability.
This document defines the work required before those claims can be made.

## Backup boundary

| Asset | Current location | Required backup approach before production durability claim |
| --- | --- | --- |
| PostgreSQL transaction and queue state | `/data/postgres` | Consistent PostgreSQL backup to a separate failure domain; record schema head, backup time and restore test. Define RPO/RTO with the Human owner before choosing dump versus continuous archiving. |
| Referenced artifacts, workspaces, receipts and checkpoints | `/data/watt` | Capture referenced content with identity/checksums and a database-consistent cut. A database backup alone cannot restore file-backed execution state. |
| Configuration and deployment source | `/data/watt/runtime`, Git remote | Version the non-secret Compose/scripts/source; back up encrypted secrets and host Docker/storage settings separately with restricted access. Do not commit or place secret values in ECF context. |
| Images and update logs | `/data/docker`, `/data/logs` | Rebuild/pull images from pinned source when possible; retain only logs required for incident/evidence policy. Images are not a substitute for database/artifact backup. |

The current `/data` disk is local to one ECS. A snapshot or copy retained only
on that ECS does not survive its loss. Backup destination, schedule,
encryption, restore credentials and tested recovery objective remain open
operations decisions; this task adds no storage service or backup job.

## Recovery after ECS loss

```text
New compatible ECS
  → mount/prepare durable data and Docker runtime
  → restore versioned configuration and secrets
  → restore PostgreSQL and referenced file data from one consistent cut
  → verify schema and source/image revisions
  → start Compose, migrate only if needed
  → reconcile queue/leases, then resume Workers
  → check API, database, Tool Host, Work/Attempt/evidence lineage
```

Do not resume Workers against a partial restore. Fence the old node, establish
which attempts and external effects may have occurred, reconcile leases and
checkpoints, and preserve unknown outcomes for review. A fresh ECS with an
empty `/data` is a new runtime, not recovered Product Reality. The migration
path must keep historical Work, authority and evidence records intact. Run a
new-host restore exercise before declaring machine-loss continuity PASS.

## Upgrade procedure

1. Record current Git revision, Compose config, image digests, Docker/Compose
   versions, migration head, health state and available disk; take and verify
   the required backup/restore point.
2. For a Docker Engine/Compose upgrade, use a tested Alibaba Cloud Linux 3
   package set, maintenance window and daemon restart plan. Verify
   `/data/docker`, container restart, logging and sandbox behavior afterward.
   Avoid an unbounded system upgrade.
3. For a service upgrade, review the source diff and target image, fast-forward
   the deployment checkout, build/pull, run migration once, then start services
   and verify API health, Worker heartbeat, Tool Host isolation and queue
   reconciliation. [`update.sh`](../../deploy/cloud-worker/update.sh) currently
   performs source fast-forward, build, migration and Compose startup; it does
   not supply automated rollback or a backup.
4. For database migrations, inspect the one canonical Alembic head and
   compatibility with both old and new service versions. If a migration is
   irreversible, recovery is a tested restore plus explicit reconciliation;
   restarting an old image is not sufficient rollback.

Use [`health.sh`](../../deploy/cloud-worker/health.sh) for the local quick
check and inspect service/queue/attempt records for authoritative readiness.
HTTP 200 alone is not proof that execution or external effects are healthy.

## Open operational decisions

- Off-host backup destination, schedule, encryption/key custody, RPO/RTO and
  new-ECS restore test are not yet implemented.
- Public ingress, TLS and domain policy are separate governed delivery choices;
  the current API is loopback-only.
- Cleanup scheduling and disk alerts have not been installed. Their proposed
  policy and thresholds are in [data-lifecycle.md](data-lifecycle.md).
- Separation into nodes requires a secure remote Tool Host/sandbox and
  workspace data path; the current Docker socket and local mounts cannot be
  copied unchanged to a multi-node deployment.

## Bounded recovery qualification — 2026-10-06

The current six-service test runtime additionally has an executable consistent
cut and isolated restoration procedure:
[`qualify_consistent_recovery.py`](../../deploy/cloud-worker/qualify_consistent_recovery.py),
with read-only [SQL fingerprints](../../deploy/cloud-worker/qualification_state.py)
and [restored lineage checks](../../deploy/cloud-worker/qualification_relationships.py).
This is a qualification utility, not an installed backup scheduler or HA system.

Run it only through the authorized exact test ECS operator at a recorded safe
point, with durable source clean and pending/queued Work already persisted:

```sh
python3 /data/watt/runtime/source/deploy/cloud-worker/qualify_consistent_recovery.py \
  /data/watt/qualifications/p0-p1-closure-v1/<new-unique-recovery-cut>
```

The procedure pauses Worker first, then API/Coordinator/Tool Host/Gitea. With
all writers quiesced it captures a PostgreSQL custom-format dump and the
minimum file-backed authoritative set: app/owner/Managed Source state, native
executor state, tool receipts, isolated workspaces and Gitea data. It records
all public SQL table counts/digests and original engineering file hashes.
PostgreSQL also stops, proving interruption of all six services; canonical
Compose then resumes with its existing images and persistent mounts.

It restores into a fresh restricted directory and a temporary PostgreSQL
container on an **internal network with no host port and no Worker**. Every
SQL table and archived regular file must match the original cut. Exact accepted
Gitea refs/trees, Candidate→PWU/Verification links, Task ECF fingerprints,
Guardian request/result→Candidate/Task/Verification links and accepted-source
Human Acceptance links are checked before declaring restored truth consistent.
The live database, repositories and Candidate history are never overwritten.
Temporary PostgreSQL/network are removed; restricted archives, restored files
and the proof manifest remain.

The archive excludes runtime `.env`, Gitea configuration and SSH/JWT private
keys. Their restoration is by the protected deployment process, not Git or a
plaintext source copy. Code, Compose and independent owner versions remain Git
references. PostgreSQL and Gitea application data are private: destination
0700, generated files 0600, and only a credential-free proof is reportable.

Observed on this node: backup 40.808 s; Compose stop/start phase after backup
27.582 s; isolated data reconstruction/check 21.754 s. The proof matched 119
SQL tables/6897 rows, 3572 engineering files and three accepted repositories.
At the quiesced cut there were no later acknowledged writes: observed cut RPO
is zero. These are **qualification measurements, not an SLA or new-host RTO**.
The restored Worker is deliberately not started against duplicate production
authority. The live queued Multi-PWU Work resumes through existing leases and
capacity; operational checks separately verify heartbeat, Search configuration,
Web state and protected pending Candidates.

Off-host storage, recurring backups, encryption/key custody and complete
machine-loss restoration remain the earlier deferred operations decisions.
A local archive on the same data disk does not survive loss of that disk.
