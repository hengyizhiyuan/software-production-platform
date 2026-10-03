# Governed Alibaba Cloud ECS Delivery v1

## Product Intent

After one Cloud Connection authorization and Human selection of an exact ECS,
Watt automatically prepares a supported host, stages the accepted artifact,
deploys it, and verifies the real business endpoint. The Human does not need to
SSH to create users, install Docker, configure the runtime, or edit RAM and
security groups per target. Human authority remains required for the exact
Delivery Authorization and for choosing PRIVATE or PUBLIC exposure.

## Approved Safety Constraint

Cloud effects are limited to the current Cloud Connection, Human-selected exact
ECS, current Delivery Authorization, fixed typed operations, and the exact
deployment port. Root is used only for the fingerprinted host bootstrap recipe;
ordinary deployment runs as wattdeploy with rootless Docker. PUBLIC exposure
may only inspect or create an exact TCP ingress rule on a security group
actually attached to that ECS, then must read the rules again and verify real
public HTTP. PRIVATE exposure never mutates ingress. Watt may revoke only a
rule it created with recorded provenance. Unrelated host and cloud resources
remain untouched.

## Current operation

The owner-facing path starts from a current, Human-accepted software Deliverable:
**部署到阿里云 → 一次连接授权 → 选择发现的 ECS → 授权并部署**.
The existing Delivery manifest, exact Candidate revision, Guardian decision
(when configured), Human Acceptance, customer Cloud Connection, and one-time
Delivery Authorization remain separate records and checks.

Cloud Connection is a durable owner asset. It stores a customer Role ARN, unique
ExternalId, account identity, selected instance identity, lifecycle, and evidence
timestamps. It never stores customer AccessKeys or issued STS credentials. Watt's
service-side RAM identity is configured separately. Re-assuming the customer role
uses the same ExternalId and verifies the observed account before every effect.
Discovery presents a list from ECS OpenAPI; the owner chooses an opaque option
token. Account, Region, and InstanceId are bound internally. Selection does not
authorize deployment. A fresh dry run checks the **existing connection grant**;
it does not require another RAM policy. The distinct Human Delivery Authorization
binds the current manifest fingerprint, archive SHA-256, candidate commit,
exact target, port, and expected prior deployment.

Remote Server Operation is a capability, not a Product surface. Infrastructure
effects are deny-by-default and allowlisted only after bounded implementation
and verification. There is no SSH, terminal, user-supplied command, arbitrary
package installation, IAM mutation, arbitrary security-group change, host nginx edit, or generic server
administration. The only root operation is the fixed, fingerprinted
`PREPARE_WATT_DEPLOYMENT_HOST_V1` recipe for Alibaba Cloud Linux 3. It observes
the host first, creates only the Watt deployment account and approved rootless
runtime when safe, and fails closed on conflicting state. Other typed operations
check prerequisites, deploy an exact Watt release, verify its runtime, clean up
an exact failed Watt runtime, and roll back only to a recorded and re-verified Watt-owned predecessor. The
same provider boundary can later serve an authorized standalone Work; that Work
is not part of this release.

The selected host must be a running Alibaba Cloud Linux 3 ECS with healthy Cloud
Assistant. After Human Delivery Authorization, Watt automatically prepares
`wattdeploy`, `/home/wattdeploy`, and rootless Docker where needed. Ordinary
operations explicitly run as that non-root user. Precheck requires
`curl`, `sha256sum`, `ss`, writable home, at least 2 GiB free, a free target
port or a recorded exact Watt-owned predecessor, and a Linux ECS in `Running`
state. Unsupported or unsafe host states block deployment without asking the
Human to administer the machine. Watt's ordinary deployment writes only under
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
the governed PUBLIC exposure flow checks the attached security group, creates
only the exact missing TCP ingress rule when authorized, rereads cloud Reality,
and then verifies the real public HTTP result. A cloud API success alone does
not establish network PASS. Watt does not edit the host firewall. Deployment
receipts retain the typed operation,
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
3. Start the current Watt runtime and open an accepted software Deliverable. Click
   **连接阿里云**. Watt calls `GetCallerIdentity`, creates a unique ExternalId,
   and shows the exact trust policy in technical details. Create the suggested
   `WattECSDelivery` customer RAM Role with this policy; do not broaden its
   principal or remove its ExternalId condition. Paste only the resulting Role
   ARN into Watt. Watt then shows `WattECSDeliveryConnectionV1` for the customer
   account ID embedded in that Role ARN. Attach this **one** policy and verify
   the connection. It grants only `DescribeInstances`,
   `DescribeCloudAssistantStatus`, `RunCommand`, `DescribeInvocations`,
   `DescribeInvocationResults`, `DescribeSecurityGroups`,
   `DescribeSecurityGroupAttribute`, `AuthorizeSecurityGroup`, and
   `RevokeSecurityGroup` for the governed Delivery capability;
   `RunCommand` is conditioned on `ecs:CommandRunAs` being exactly `root` or
   `wattdeploy`. `root` is used only by the typed bootstrap operation. The
   invocation reads include the account's command namespace.
   Alibaba RAM requires `Resource="*"` for `AuthorizeSecurityGroup`; Watt still
   binds each effect to the selected instance's attached group, exact TCP port,
   exposure mode, and Delivery Authorization. Revocation is allowed only for a
   Watt-created rule with exact evidence. No ECS FullAccess, generic command
   UI, or unrelated ECS mutation is granted.
4. Select one discovered ECS. Watt binds its exact AccountId, RegionId, and
   InstanceId internally and dry-runs both permitted execution identities against
   the **same** connection grant. The user stays in Watt and authorizes the exact
   Deliverable, target, port, and PRIVATE or PUBLIC exposure. Watt then
   classifies and, if safe, bootstraps the host automatically before the
   non-root precheck and deployment. PUBLIC exposure checks and, when needed,
   creates only the exact selected TCP ingress rule, then reobserves it and
   verifies public HTTP. PRIVATE exposure leaves ingress untouched.

The authority layers are deliberate: Alibaba RAM grants a narrow capability
over eligible instances **before** selection; Watt permits an effect only for
the Human-selected exact instance, current Delivery Authorization, and fixed
typed operation. The provider derives `root` only from
`PREPARE_WATT_DEPLOYMENT_HOST_V1`; all other operations use `wattdeploy`.
`DescribeRegions` and STS `GetCallerIdentity` require no additional grant.
Revoking the connection in Watt blocks new authorizations; separately revoke
or remove the customer RAM Role grant in Alibaba Cloud when access must end.

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
[Cloud Assistant RAM scope](https://help.aliyun.com/en/ecs/user-guide/use-ram-to-implement-permission-control),
[CommandRunAs whitelist](https://help.aliyun.com/zh/ecs/user-guide/run-cloud-assistant-commands-as-a-regular-user),
[Alibaba Cloud Linux 3 Docker packages](https://www.alibabacloud.com/help/en/ecs/user-guide/install-and-use-docker),
[Docker rootless mode](https://docs.docker.com/engine/security/rootless/),
[invocation results](https://www.alibabacloud.com/help/en/ecs/developer-reference/api-ecs-2014-05-26-describeinvocationresults),
[OSS PutObject](https://www.alibabacloud.com/help/en/oss/developer-reference/putobject),
[private signed URL](https://www.alibabacloud.com/help/en/oss/use-a-fixed-file-url-to-access-a-file).

Same-account personal dogfood still uses logically separate service RAM user and
customer RAM Role. Its success does not prove cross-account production trust.
