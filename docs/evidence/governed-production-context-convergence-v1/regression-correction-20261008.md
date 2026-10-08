# N1 regression correction — 2026-10-08

## Empty Work / two repository namespaces

The previous report classified `test_empty_work_then_two_repository_namespaces` as an asynchronous attention timing failure. That classification was incorrect. The driver’s `activate` is synchronous. On both canonical and candidate source, the Work had already recorded a terminal no-progress convergence stop during admission. A second manual activation returned `BLOCKED` with zero iterations; no actionable Human question existed. Waiting for idle did not change the result. The old assertion demanding Human Attention was stale. The test now checks the truthful `BLOCKED`/no-attention state, then verifies that binding repository A followed by B gives independent pointers and exact revision/source identities. Isolated PostgreSQL regression: PASS (1). This is a test contract correction; it is not evidence that the empty Work completed.

## Gitea restart and accepted source isolation

The previous managed-source restart test was INCOMPLETE because its Docker Compose command could not execute inside the test runner. A dedicated `watt-n1-gitea-20261008` container was provisioned with **separate qualification data/config volumes** and an independent qualification account. Its credential values are in a mode-600 ECS-local test environment file and are absent from this report. The test now accepts an explicit `SPG_TEST_GITEA_RESTART_CONTAINER` override limited to `watt-n1-gitea-*`; the normal CI Compose path remains. Only the isolated container was restarted. Production Gitea `watt-cloud-worker-gitea-1` was not restarted.

The first isolated run passed source V1 acceptance, Gitea restart, repository survival, ambient HEAD exclusion, exact export and remote-delivery non-effect, then failed an unrelated stale UI assertion looking for `Code Assets` in `index.html`. That UI section currently lives in `advanced.html`; the assertion was corrected to that file. The second isolated run passed the full test (1). This is a deterministic regression fixture with synthetic test acceptance; it does **not** count as a new real Human Acceptance, G2 Work PASS, or production Gitea restart qualification.
