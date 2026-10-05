# Watt Production Infrastructure Runtime Baseline v1.0

Status: **observed single-ECS baseline**, 2026-10-05. This document describes the
Cloud Worker runtime on `codex/cloud-worker-single-ecs` and the exact target
observed during its qualification. It is not a claim of high availability,
machine-loss recovery, or a public production endpoint. The deployment source
is [`deploy/cloud-worker/docker-compose.yml`](../../deploy/cloud-worker/docker-compose.yml).

## Infrastructure and network

| Item | Observed reality |
| --- | --- |
| Cloud target | Alibaba Cloud `cn-wulanchabu`, `i-0jl386xnbauudq5j9jk0` |
| Instance | `ecs.e-c1m4.xlarge`, 4 vCPU, 16 GiB instance specification; about 14 GiB visible to Linux |
| OS | Alibaba Cloud Linux 3.2104 U13.4, x86_64; kernel `5.10.134-19.8.al8.x86_64` |
| Disks | 40 GB system disk; 100 GB ext4 data disk mounted read-write at `/data` |
| Containers | Docker Engine 26.1.3 and Compose v2.27.0; Docker root `/data/docker` |
| Network | Initially API-only on ECS loopback `127.0.0.1:8000`; the Phase 4 test Web entrypoint is `0.0.0.0:8080` to the same authenticated API/Web process. PostgreSQL and Tool Host have no host port; Compose `executor` network is internal |
| External dependency | Worker uses an external DeepSeek model API; the ECS does not host model inference |

The ECS network permits outbound access to the selected model API and container
image sources. The temporary Phase 4 browser endpoint uses plain HTTP on the
test node; it does not assert a production domain, TLS, load balancer,
cross-node routing, or a multi-zone failure domain. The host Docker socket is
shared with the API and Tool Host for Production Environment containers; it is
a host-level privilege boundary that must be revisited before moving services
to separate nodes.

## Current service topology

The Phase 4 browser entrypoint is Watt's existing static HTML/CSS/JavaScript
Product Experience served by FastAPI. It is not a second application or a
mocked frontend. Browser requests for `/assets/*` and the Product/Workspace
routes reach that process; same-origin `/api/*` requests reach the existing
Product/Work/Execution owners. The single owner signs in through
`/auth/session`, receiving an HTTP-only session cookie. The browser does not
hold Worker leases or production state: closing or reloading it does not stop
the queue, Worker, verification, or Candidate governance. The API service is
the sole host-published container; Gitea, PostgreSQL, Coordinator, Worker, and
Tool Host remain unexposed by Compose.

```text
Single ECS / Docker Compose
  Browser ──TCP/8080──► Watt Web/API ──► PostgreSQL (persistent queue and product state)
   │                       ▲
   └──► Tool Host           │
           ▲                │
           └── Worker ◄────┘
                ▲
           Coordinator (lease/queue reconciliation)
```

| Service | Responsibility | Current dependency and placement |
| --- | --- | --- |
| `api` | HTTP interaction, Product/Work control, task admission and state transitions | Starts after migration and Tool Host health; container on the single ECS |
| `native-worker` | Independently claims persisted execution work, calls the external model, updates execution state | Requires API and Tool Host readiness; separate container/process from API |
| `native-coordinator` | Reconciles expired leases and queue ownership | Separate container, waits for API health |
| `native-tool-host` | Executes bounded tool operations and mediates Production Environment execution | Internal executor network; requires Production Environment isolation on this host profile |
| `postgres` | Transaction data, queue/lease state, execution records | PostgreSQL 17.6 container; `pg_isready` health check |
| `migrate` | One-shot Alembic schema upgrade before API starts | Runs after PostgreSQL health; observed head `20261002_65` |

The queue boundary is PostgreSQL-backed today. It does not require a separate
broker to keep the API and Worker logically independent. The Worker is neither
an API thread nor an HTTP request lifecycle. The baseline verified API health,
database readiness, Worker registration/heartbeat and a Compose `down`/`up`
restart with application and database data intact. It did not verify a live
model completion or recovery after loss of the ECS/data disk.

## Storage and operation

| Host path | Purpose |
| --- | --- |
| `/data/docker` | Docker images, container layers and bounded Docker logs |
| `/data/postgres` | PostgreSQL data directory |
| `/data/watt/runtime` | Compose file, source checkout, root-owned mode-600 `.env`, scripts |
| `/data/watt/app` | Persistent application/owner runtime state |
| `/data/watt/workspaces` | Native workspace volume bind target |
| `/data/watt/native-executor` | Worker checkpoint/runtime state |
| `/data/watt/tool-receipts` | Tool Host receipts |
| `/data/logs` | Runtime update logs |

The data disk had about 92 GB available after initial deployment. Use
`cd /data/watt/runtime && docker compose up -d` to recover the configured
stack on this host. [`update.sh`](../../deploy/cloud-worker/update.sh) performs
fast-forward source update, image build, migration and Compose startup;
[`health.sh`](../../deploy/cloud-worker/health.sh) checks the local services;
[`inspect-disk.sh`](../../deploy/cloud-worker/inspect-disk.sh) inspects disk use.
[`cleanup-docker.sh`](../../deploy/cloud-worker/cleanup-docker.sh) supplies a
bounded cleanup command but is **not** an installed automatic schedule.

The qualified deployment source revision was
`ae0611fbf885a1e69f517967c84ac7833dcc1fbf`. Read-only Cloud Assistant
baseline evidence used invocation `t-wl06z2relppx0xs`; service health used
`t-wl06z2u9ie5ki68`; the Compose `down`/`up` and persistence check used
`t-wl06z2ucdltj2tc`; final disk inspection used `t-wl06z2ui756eark`.
These identify the historical observations; a new target or later runtime
decision requires fresh evidence.

## Runtime boundaries

These are placement-independent boundaries, even while all containers and
storage share one ECS:

- **Application Runtime:** HTTP API and Product/Work authority. It admits and
  observes execution work; it does not run long AI jobs inside requests.
- **Execution Runtime:** Worker, Coordinator, Tool Host and isolated Production
  Environments. Execution reports and effects retain their own lineage and do
  not become Product truth merely because a Worker reported success.
- **Data Runtime:** PostgreSQL durable transaction/queue state and referenced
  runtime files. Database and file-backed state must be backed up and restored
  coherently before claiming host-loss continuity.

The three infrastructure boundaries complement, rather than replace, Watt's
[five capability planes](plane-model.md) and Work/authority model. Future
physical separation must retain the same task, authority, context, evidence
and persistence contracts; it must not make API memory or local filesystem
paths the queue or source of truth.
