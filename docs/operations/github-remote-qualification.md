# GitHub remote delivery qualification

This is the bounded GitHub provider path for an authenticated Watt owner. Set
`SPG_OPERATOR_TOKEN` to a dedicated 32+ character value. Supply
`SPG_GITHUB_READ_TOKEN` only for repositories requiring authenticated read,
and `SPG_GITHUB_WRITE_TOKEN` only when a Human authorizes an actual push. Keep
both secrets in the server secret store; never put them in a repository URL,
Work request or delivery manifest. Revoking a grant does not revoke the token
at GitHub; rotate/revoke that credential with its owner as well. Watt stores a
one-way token fingerprint beside the grant and refuses a rotated token until
the owner grants again and GitHub permission is re-observed.

The Human signs in with `/login`. The scoped API path is:

1. `POST /api/github/grants` with `repository_url` and `capability: READ`;
   verify the returned permission and grant ID. A public repository may be
   acquired without this grant.
2. Admit the exact GitHub repository and development branch into Work. Produce,
   verify and inspect the exact Candidate, then record Human Acceptance on its
   current software delivery manifest.
3. Separately grant `WRITE` and call
   `POST /api/works/{work_id}/remote-delivery/authorize` with `manifest_id`,
   `expected_revision`, `target_branch`, `expected_remote_revision` (or `null`
   for a new remote branch) and a nonempty rationale. This is the distinct
   Human Delivery Authorization; a write token alone does not grant it.
4. Call `POST /api/remote-deliveries/{authorization_id}/push`; retain the
   returned `remote_before` and `remote_after`. Read the GitHub branch head
   independently and require the same exact revision. Retrying this endpoint
   must observe an already-delivered revision without a second effect.
5. If requested, call
   `POST /api/remote-deliveries/{authorization_id}/pull-request` with `base`,
   `title` and `body`. Verify the returned URL's head SHA and base branch on
   GitHub. Revoke unused grants through `DELETE /api/github/grants/{grant_id}`.

The provider uses a non-force Git push. Diverged remote branches, missing
grants, missing current acceptance, stale manifests and unobserved remote
effects fail explicitly. The P0 full-system profile also requires a real
Guardian assurance decision before claiming a delivery gate. The current
Guardian owner runtime only accepts intake, so no full-system remote-release
qualification can be recorded until that owner supplies an attributable
decision/gate API and Watt consumes it. No live GitHub effect was performed in
the P0 batch without the external credentials and Human acceptance.
