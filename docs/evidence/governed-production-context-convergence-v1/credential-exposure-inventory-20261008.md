# N1 credential exposure inventory — 2026-10-08 06:18 UTC

This inventory deliberately contains **no credential values, prefixes or hashes**. During the earlier N1 investigation a `docker inspect ... .Config.Env` tool output displayed production environment values in this Codex chat/tool transcript. The observed channel is this task transcript and any platform or local logging that retains it. The values were not intentionally written to the tracked qualification reports or sent to another app. External access or reuse cannot be determined from this evidence.

| Credential type | Likely authority / affected scope | Exposure channel | Rotation priority |
| --- | --- | --- | --- |
| Production operator bearer token | Watt administrative HTTP operations on the ECS runtime | Tool output in this chat | P0: stage a new token, coordinate client updates, revoke old token after cutover |
| Native executor internal token | Internal execution/control boundary | Same | P0: coordinated service-side and worker-side rotation with health checks |
| DeepSeek API key | Paid model calls and associated account quota | Same | P0: issue replacement in provider, update isolated/prod consumers as applicable, revoke old after verified cutover |
| Aliyun OpenSearch API credential | Search service access within the configured account policy | Same | P0: replace with least-privilege credential and audit provider usage |
| PostgreSQL application password in connection URL | Watt production database, subject to DB role grants | Same | P1: stage new DB credential/role, migrate consumers, validate, then revoke old |
| Managed Gitea source password | Product source repository operations under the configured Gitea account | Same | P1: stage replacement service identity/password, update consumers, validate Git operations, then revoke old |

Priority expresses potential blast radius, not proof of misuse. Actual permissions, reuse, and log retention are UNKNOWN pending operator/provider audit. Treat all six values as compromised for planning. Do not echo current values in diagnostics or reports; inspect only key names, existence and permissions. Future inspection should avoid `.Config.Env` output.

**Proposed controlled sequence:** (1) identify current consumers and provider-side usage without printing values; (2) prepare replacement credentials and rollback/health plan; (3) request Human approval for each production credential change and any needed restart or service interruption; (4) rotate P0 control/API credentials, then P1 database and Gitea credentials, preserving old validity until verified cutover where provider policy allows; (5) revoke old credentials, audit use, and record only credential IDs, timestamps and health receipts. No production credential, config or service has been changed as part of this inventory.
