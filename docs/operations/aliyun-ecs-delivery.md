# Governed Alibaba Cloud ECS Delivery v1

The owner-facing path starts from a current, Human-accepted software Deliverable:
**部署到阿里云 → 连接阿里云 → 选择发现的 ECS → 验证目标授权 → 授权并部署**.
The existing Delivery manifest, its exact Candidate revision, Guardian decision
(when configured), Human Acceptance, customer Cloud Connection, exact target grant,
and one-time Delivery Authorization remain separate records and checks.

Cloud Connection is a durable owner asset. It stores a customer Role ARN, unique
ExternalId, account identity, selected instance identity, lifecycle, and evidence
timestamps. It never stores customer AccessKeys or issued STS credentials. Watt's
service-side RAM identity is configured separately. Re-assuming the customer role
uses the same ExternalId and verifies the observed account before every effect.
Discovery presents a list from ECS OpenAPI; the owner chooses an opaque option
token. Account, Region, and InstanceId are bound internally. Selection does not
authorize deployment. A fresh target-specific RunCommand dry run and a distinct
Human Delivery Authorization bind the current manifest fingerprint, archive
SHA-256, candidate commit, exact target, port, and expected prior deployment.

Remote Server Operation is a capability, not a Product surface. Infrastructure
effects are deny-by-default and allowlisted only after bounded implementation
and verification. There is no SSH, terminal, user-supplied command, OS package
installation, IAM mutation, security-group change, host nginx edit, or generic
server administration. The current typed set checks prerequisites, deploys an
exact Watt release, verifies its runtime, cleans up an exact failed Watt runtime,
and rolls back only to a recorded and re-verified Watt-owned predecessor. The
same provider boundary can later serve an authorized standalone Work; that Work
is not part of this release.

The target must already have a dedicated `wattdeploy` OS user with home
`/home/wattdeploy`, healthy Cloud Assistant, and **rootless Docker under that
user**. The commands explicitly name that non-root user. Precheck requires
`curl`, `sha256sum`, `ss`, writable home, at least 2 GiB free, a free target
port or a recorded exact Watt-owned predecessor, and a Linux ECS in `Running`
state. Missing prerequisites block deployment. Watt writes only under
`~/.watt/deployments/<deployment-id>` and creates containers named
`watt-delivery-<deployment-id>` with exact Watt labels. An unrelated listener or
container is never stopped. Replacement stages and checks the new container
before stopping the prior known-good container; a failed activation attempts
rollback to the exact predecessor and requires a passing health observation.
The selected connection exposes its prior Watt deployments across manifest
versions so the Human can explicitly bind the predecessor being replaced.

Static Web uses only the exact manifest's allowed public Web files beneath its
entrypoint directory and a locally available pinned Python 3.13 base image. The
fixed build recipe runs the standard-library static HTTP server as UID 101 on
internal port 8080; it does not depend on a base image's default listener. The full application
path exports the **exact served Candidate Preview image ID**; it does not rebuild
from HEAD or build on ECS. The current full-application Preview topology also
needs database and runtime configuration that this bounded ECS contract cannot
supply safely. Its export path is preserved, but authorization currently fails
with `FULL_APPLICATION_RUNTIME_CONFIGURATION_REQUIRED` before any cloud effect.
It is contract-only until an exact governed runtime-configuration seam exists.
Neither an image load nor Cloud Assistant exit code alone is a successful
delivery.

The service exports the image to its persistent owner runtime root, computes
SHA-256, uploads it under `watt-delivery/sha256/<digest>.tar` in a Watt-owned
private OSS bucket, and issues a five-minute HTTPS GET URL. The target verifies
the archive digest before loading. The signed URL exists only in transient
execution material; persisted Delivery Reality retains the digest and OSS object
identity, not the URL. Configure OSS lifecycle expiry for this prefix (one day is
sufficient for dogfood). If public reachability fails while local health passes,
the result asks the Human to inspect their network settings; Watt does not edit
Security Groups or a firewall. Deployment receipts retain the typed operation,
account/region/instance, invocation and command IDs, exit status, bounded status
code, and verification outcome.

## Human setup order for dogfood

1. Create a **dedicated Watt service RAM user**. Give it an AccessKey through
   the ignored local `.env`, never a root-account key. `GetCallerIdentity`
   needs no extra RAM action. Grant only `oss:PutObject` and `oss:GetObject`
   for the Watt-owned bucket prefix described below. Once the customer role
   exists, add `sts:AssumeRole` with `Resource` set to its **exact role ARN**.
   The service-user policy for this dogfood is the following template. Replace
   `<WATT_BUCKET>` and `<CUSTOMER_ROLE_ARN>` with the actual values; do not use
   `*` for the role resource or grant any ECS action to the service user:

   ```json
   {
     "Version": "1",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["oss:PutObject", "oss:GetObject"],
         "Resource": ["acs:oss:*:*:<WATT_BUCKET>/watt-delivery/sha256/*"]
       },
       {
         "Effect": "Allow",
         "Action": ["sts:AssumeRole"],
         "Resource": ["<CUSTOMER_ROLE_ARN>"]
       }
     ]
   }
   ```
2. Create one Watt-owned OSS bucket, preferably in the selected ECS region, with private bucket
   ACL, no public bucket policy, and a one-day lifecycle rule for
   `watt-delivery/sha256/`. The service-side object policy resource is
   `acs:oss:*:*:<bucket>/watt-delivery/sha256/*`. The customer role receives
   **no OSS permission**. The service explicitly uploads each object with private
   object ACL. The service needs no bucket-list or object-delete grant because
   lifecycle handles expiry.
3. Start Watt from this branch and open an accepted software Deliverable. Click
   **连接阿里云**. Watt calls `GetCallerIdentity`, creates a unique ExternalId,
   and shows the exact trust policy in technical details. Create the suggested
   `WattECSDelivery` customer RAM Role with this policy; do not broaden its
   principal or remove its ExternalId condition. Paste only the resulting Role
   ARN into Watt. Watt then shows the exact read-only discovery policy for the
   customer account ID embedded in that Role ARN. Attach that policy, return,
   and verify the connection.
4. Select one discovered ECS. Watt shows a second custom policy. Its only write
   action is `ecs:RunCommand` on the exact selected instance ARN with
   `ecs:CommandRunAs=wattdeploy`. Its reads cover only the invocation-result
   resources needed for reconciliation. Attach it to the same Role and verify
   the target grant. `DescribeRegions` and STS `GetCallerIdentity` require no
   explicit grant; the discovery policy contains only `ecs:DescribeInstances`
   and `ecs:DescribeCloudAssistantStatus` on the customer's instance wildcard.
   Revoking the connection in Watt blocks new authorizations; separately revoke
   or remove the customer RAM Role grant in Alibaba Cloud when access must end.
5. Confirm manually that the selected Linux ECS is `Running`, Cloud Assistant
   healthy, `/home/wattdeploy` exists and is writable, the user can use rootless
   Docker and its own image store, `curl`, `sha256sum`, and `ss` are present,
   and the chosen high port is free. Prepare the public port or Security Group
   yourself if external verification is required. Watt will only observe these
   conditions and will not repair the host.

The ignored environment file for this checkout is
`/Users/yu/Documents/dev/software-production-platform/.env`. Configure variable
**names** `SPG_DATABASE_URL` (the existing Product database, reachable from the
host), `SPG_OPERATOR_TOKEN` (required by the Product login),
`SPG_OWNER_RUNTIME_STORE_ROOT` (a persistent host directory),
`SPG_ALIYUN_ACCESS_KEY_ID`, `SPG_ALIYUN_ACCESS_KEY_SECRET`,
`SPG_ALIYUN_OSS_BUCKET`, `SPG_ALIYUN_OSS_REGION`,
`SPG_ALIYUN_ECS_DEPLOYMENT_USER` (default `wattdeploy`), and
`SPG_ALIYUN_ECS_STATIC_BASE_IMAGE` (a Python 3.13 image pinned as
`name@sha256:<digest>` and already pulled into Watt's service-side Docker daemon;
the current local image is
`python@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26`).
For the current dogfood, run the Watt API from this checkout on the local host,
with access to the existing Docker daemon and the same Product database. Use a
persistent `SPG_OWNER_RUNTIME_STORE_ROOT` for exported archives. The existing
Compose app image contains the Docker CLI but its service has no Docker daemon
connection; that container therefore fails closed at image export. Do not add
a Docker socket or elevate the app merely to pass this qualification. The
Compose profile already points its owner runtime root at the persistent
`/var/lib/spg/owner-runtime` volume for a future separately governed daemon
access path. The existing host startup command is
`uv run --env-file .env uvicorn spg.api.http:create_http_application --factory --host 127.0.0.1 --port 8000`.
Do not send any key or secret value in chat.

Official contracts used for the two RAM policies and execution:
[RAM trust policy](https://www.alibabacloud.com/help/en/ram/user-guide/edit-the-trust-policy-of-a-ram-role),
[ExternalId](https://www.alibabacloud.com/help/en/ram/use-cases/use-externalid-to-prevent-the-confused-deputy-problem),
[AssumeRole](https://www.alibabacloud.com/help/en/ram/developer-reference/api-sts-2015-04-01-assumerole),
[ECS RAM action matrix](https://www.alibabacloud.com/help/en/ram/api-elastic-compute-service),
[RunCommand](https://www.alibabacloud.com/help/en/ecs/developer-reference/api-ecs-2014-05-26-runcommand),
[invocation results](https://www.alibabacloud.com/help/en/ecs/developer-reference/api-ecs-2014-05-26-describeinvocationresults),
[OSS PutObject](https://www.alibabacloud.com/help/en/oss/developer-reference/putobject),
[private signed URL](https://www.alibabacloud.com/help/en/oss/use-a-fixed-file-url-to-access-a-file).

Same-account personal dogfood still uses logically separate service RAM user and
customer RAM Role. Its success does not prove cross-account production trust.
