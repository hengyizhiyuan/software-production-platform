# Independent Watt runtime activation and qualification

The native queue, leases and checkpoint pointers are in PostgreSQL. The
worker, Tool Host and coordinator are already separate processes. Deploy the
entire stack on a host that remains running when the Human's desktop sleeps,
using [`compose.independent-runtime.yaml`](../../compose.independent-runtime.yaml)
over [`compose.native-executor.yaml`](../../compose.native-executor.yaml).

The five `SPG_DURABLE_*_VOLUME` values must name **pre-provisioned off-host
durable volumes**. Local Docker named volumes on the remote host are not
machine-loss protection. The PostgreSQL volume requires backup/restore and
the shared workspace/Tool Host receipt volumes require consistent durable
mount semantics. Managed repository Git bundles live in PostgreSQL; execution
checkouts can be rebuilt from those bundles. External Git repositories retain
their host-side authority and must be reacquired using an active read grant.

Set `SPG_OPERATOR_TOKEN` (32+ random characters),
`SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN`, the selected inference credential and
model, and the durable volume names as secrets/environment on the remote host.
The `REQUIRED` owner profile also needs approved ECF and Guardian source
checkouts mounted read-only through `SPG_ECF_OWNER_SOURCE_PATH` and
`SPG_GUARDIAN_OWNER_SOURCE_PATH`. Pin and record their revisions independently
of Watt; the overlay adds their `src` directories to the app's Python path.
Watt does not copy their contracts or substitute local assurance decisions.
Guardian's current owner
runtime admits evidence but does not yet return an assurance decision, so its
release gate remains blocked by that owner-side capability.
Start with:

```sh
docker compose -f compose.native-executor.yaml -f compose.independent-runtime.yaml \
  --profile provider up -d --build
```

Reach the app through an authenticated tunnel/VPN to its loopback-bound port.
The browser is a client and may disconnect without stopping the worker.

Qualification must observe a queued real attempt while: (1) disconnecting the
browser; (2) stopping/restarting `native-worker`; (3) letting one lease expire;
(4) interrupting a Provider response; (5) terminating a worker process after
an intent-before-effect record; and (6) replacing the host with a fresh host
mounting the same durable volumes. Inspect PostgreSQL attempt epoch, latest
checkpoint and Tool Host receipt IDs before and after. A retried Git/remote
operation must observe the target revision before another effect. Do not mark
machine-loss continuity PASS until a remote deployment performs the host
replacement exercise.
