# Exact build stop — dependency lock attestation

Frozen source `4cb5b8d1db42e769d17563b0671074bddd8c25d3`, tree `45a4cdfc7209110c34395615e899e2693eea3253` did not produce a qualified image. Build stopped before package reinstall with `DEPENDENCY_LOCK_MISMATCH`. No Work or model request occurred.

The current lock added the test-only JSON Schema reference validator; all 65 prior locked package versions remain identical ([proof](lock-version-proof.json)). Exact new lock SHA256 is `ac853305a52d1daf56df2ca020e984476fb4e58a83cac205e24f0892cd59b8a9`. The image attester still pinned the old application lock `279fba19bb5a40457739e49408137190d3d6f8e2e7171a273b3e742bae12a038`, so it correctly refused a mismatching build input.

The narrow correction pins the exact new application lock in the attester. Dockerfile's independent original dependency-base image and original base lock checks remain unchanged; full COPY hashes and installed imports remain required. No dynamic acceptance of arbitrary locks, dependency budget or runtime gate weakening is introduced.

Persistent original failure: `/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation43-qualified-20261010/final-image/evidence/{build.json,build.log,build-input-identity.json}`. Next exact build uses a fresh generation44 path, leaving generation43 intact. Controlled tests and independent audit do not replace installed-image, PostgreSQL or real G0 qualification.
