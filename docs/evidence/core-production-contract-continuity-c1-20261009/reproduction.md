# C1 controlled qualification reproduction

This records the final executed entry points; it is not an instruction to start C2 or repeat live G0. Use a fresh isolated directory/database. Do not overwrite this evidence set or point these tests at a business database: the dedicated fixture database is intentionally truncated between cases.

## Exact inputs

Use `exact-source-manifest.json` and the three committed repositories:

- Watt `00e2a77e6b80ea79185d74a12db2cec8eeb9445e`;
- Guardian `6b974748df22d84b88f6908ea8ee90a9752fd183`;
- selected ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`;
- unsupported ECF source `c6b568d006022e39b95daebedfecfb55e562ebe5`.

Git archives named in the manifest, the pytest dependency archive and `pytest-py-shim.tar` are retained at `/data/watt/c1-contract-qualification-20261009` on `watt-ecs`. Source archives can also be reconstructed using `git archive --format=tar <exact revision>` from the corresponding repository; verify their SHA256 before use. No authentication material is part of this package. The local `.gitattributes` disables newline normalization for evidence; SHA256 indexes refer to the exact persisted bytes across operating systems.

The original runner used dependency image ID `sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14`. It did not qualify that image as a new C1 application build. Runtime dependency versions and imports are recorded in `source-attestation.json`. Fresh reproduction must independently report its runtime identity and result.

## Controlled layout and isolation

The isolated runner mounted only a fresh qualification root at `/c1`:

```text
/c1/watt/           exact Watt archive
/c1/guardian/       exact Guardian archive
/c1/ecf/           exact supported ECF archive
/c1/ecf-current/   exact unsupported ECF archive
/c1/test-deps/      pytest dependency archive + py.py shim
/c1/evidence/      new output directory
```

A newly created PostgreSQL 17.6-alpine container used network `none`, tmpfs PG data, no published ports, database `c1_contract_continuity`, user `c1_test` and container-local trust. The runner joined that PG container's network namespace. No production credentials, settings, volume, Docker socket, API or Worker service was mounted. The test fixture verifies the database host is loopback and the database name is exactly `c1_contract_continuity` before truncation. These isolation properties must be checked before any rerun.

Recorded environment for the entry points below:

```sh
export PYTHONPATH=/c1/test-deps:/c1/watt/src:/c1/watt:/c1/guardian/src:/c1/ecf/src
export SPG_TEST_DATABASE_URL=postgresql+psycopg://c1_test@127.0.0.1:5432/c1_contract_continuity
export C1_ECF_CURRENT_MAIN_SOURCE=/c1/ecf-current/src
export C1_APPLICATION_REVISION=00e2a77e6b80ea79185d74a12db2cec8eeb9445e
export C1_GUARDIAN_REVISION=6b974748df22d84b88f6908ea8ee90a9752fd183
export C1_ECF_REVISION=5aa4f8833c359c15bd059eda5972aa3915bcc18c
export C1_EVIDENCE_OUTPUT=/c1/evidence/exact-contract-chain
```

`SPG_TEST_DATABASE_URL` above is only the isolated trust fixture endpoint; it is not a production URL or secret. `SPG_DATABASE_URL` is scoped by the fixture to the same new database. Migration remains `20261007_72`.

## Executed final suites

In the runner, from `/c1/watt`:

```sh
python -m pytest -p no:cacheprovider -o junit_family=legacy \
  tests/test_c1_ecf_contract_compatibility.py \
  tests/test_managed_greenfield_context.py \
  tests/test_decision_context_integration.py \
  tests/test_governed_obligation_fulfillment.py \
  tests/test_guardian_assurance_adapter.py \
  tests/integration/test_c1_contract_continuity.py \
  -x --tb=short --junitxml=/c1/final-watt.xml
```

From `/c1/guardian`:

```sh
python -m pytest -p no:cacheprovider \
  tests/test_c1_governed_evidence_continuity.py \
  tests/test_governed_obligation_evidence.py \
  tests/test_software_assurance.py \
  --tb=short --junitxml=/c1/final-guardian.xml
```

Actual final results: Watt 99, Guardian 73; 0 failures/errors/skips and exit 0. The source archives were compared to every regular source file before and after the final runs using `attest_sources.py`. This checker uses the fixed `/c1` layout; copy it and the manifest to a fresh root rather than changing the retained receipt.

## Recover exact fixture Git evidence without running tests

For each work in `evidence/git-objects/manifest.json`, first verify the `.pack` SHA256. In a newly created bare repository:

```sh
git init --bare /tmp/new-c1-witness
git -C /tmp/new-c1-witness index-pack --stdin < <work-id>.pack
git -C /tmp/new-c1-witness rev-parse '<input-revision>^{tree}'
git -C /tmp/new-c1-witness rev-parse '<output-revision>^{tree}'
git -C /tmp/new-c1-witness show '<output-revision>:index.html'
```

Replace placeholders with the manifest's exact identities and compare both trees and the HTML SHA256. `recovery-check.json` records this recovery already performed for both works. `verify_git_recovery.py` records the checks using `/c1/recovered-witnesses`; it requires a fresh directory and fails if the repository already exists. `export_git_witnesses.py` was a read-only export from the original fixture repositories before container cleanup, not a way to manufacture missing historical evidence.

## End of this run

The exact two newly created containers were stopped and removed after ID/name/label/mount checks. Fixture tmpfs data was discarded; this package contains selected canonical Owner JSON records, Git objects and JUnit, not a full database backup. Source archives and the persisted evidence directory remain on ECS. Production source and all existing running container IDs remained unchanged; see `cleanup-receipt.json`.

A future reproduction must use new containers, a new fixture database and new result filenames. Do not reuse this run's Work IDs, claim its synthetic authority as Human acceptance, or replace historical evidence with a rerun.
