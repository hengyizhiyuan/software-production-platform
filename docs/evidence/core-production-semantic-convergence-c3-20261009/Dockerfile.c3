# C3 only: build a NEW image; the parent must inspect the local base tag against
# BASE_IMAGE_ID before building. Do not run the old N1 role-swap scripts.
# Context: watt/, guardian/src/, ecf/src/, ecf-unsupported/src/, test-deps/,
# c3-source-identity.json. Sources are exact archives, not runtime overlays.
ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS c3-runtime
USER root
WORKDIR /app

ARG BASE_IMAGE
ARG BASE_IMAGE_ID=sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14
ARG WATT_REVISION
ARG WATT_TREE
ARG GUARDIAN_REVISION
ARG GUARDIAN_TREE
ARG ECF_REVISION=5aa4f8833c359c15bd059eda5972aa3915bcc18c
ARG ECF_TREE=878d39d9c259272bb05f2e02bdf9d60c22fad460
ARG ECF_UNSUPPORTED_REVISION=c6b568d006022e39b95daebedfecfb55e562ebe5
ARG ECF_UNSUPPORTED_TREE=f102fa082bbd0a1abd827e77d6aa1340db8b83c5

# Fail before replacing the source if the dependency image has a different lock.
RUN test "$BASE_IMAGE_ID" = "sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14" \
    && printf '%s  /app/uv.lock\n' '279fba19bb5a40457739e49408137190d3d6f8e2e7171a273b3e742bae12a038' | sha256sum --check --status

# COPY merges directories. Clear only these image-local source trees first so
# files deleted in the new exact revision cannot survive from the old image.
RUN rm -rf /app/src /app/migrations /app/docker /qualification \
    /opt/c2-owners /opt/c2-test-deps /opt/c2-build /opt/c3-owners /opt/c3-test-deps /opt/c3-build

COPY watt/pyproject.toml watt/uv.lock watt/alembic.ini watt/README.md /app/
COPY watt/src/ /app/src/
COPY watt/migrations/ /app/migrations/
COPY watt/docker/ /app/docker/
COPY watt/tests/ /qualification/tests/
COPY watt/migrations/ /qualification/migrations/
COPY watt/pyproject.toml watt/alembic.ini /qualification/
COPY guardian/src/ /opt/c3-owners/guardian/src/
COPY ecf/src/ /opt/c3-owners/ecf/src/
COPY ecf-unsupported/src/ /qualification/ecf-current/src/
COPY test-deps/ /opt/c3-test-deps/
COPY watt/docs/evidence/core-production-semantic-convergence-c3-20261009/Dockerfile.c3 /opt/c3-build/Dockerfile.c3
COPY watt/docs/evidence/core-production-semantic-convergence-c3-20261009/attest_c3_image.py /opt/c3-build/attest_c3_image.py
COPY c3-source-identity.json /opt/c3-build/c3-source-identity.json

# The installed spg package must be observed from the venv. Do not put /app/src
# or /qualification/src in PYTHONPATH and silently bypass package reinstallation.
ENV SPG_RUNTIME_REVISION=${WATT_REVISION} \
    C3_WATT_TREE=${WATT_TREE} \
    C3_GUARDIAN_REVISION=${GUARDIAN_REVISION} \
    C3_GUARDIAN_TREE=${GUARDIAN_TREE} \
    C3_ECF_REVISION=${ECF_REVISION} \
    C3_ECF_TREE=${ECF_TREE} \
    C3_ECF_UNSUPPORTED_REVISION=${ECF_UNSUPPORTED_REVISION} \
    C3_ECF_UNSUPPORTED_TREE=${ECF_UNSUPPORTED_TREE} \
    C3_BASE_IMAGE_REF=${BASE_IMAGE} \
    C3_BASE_IMAGE_ID=${BASE_IMAGE_ID} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/c3-owners/guardian/src:/opt/c3-owners/ecf/src:/opt/c3-test-deps \
    C1_ECF_CURRENT_MAIN_SOURCE=/qualification/ecf-current/src

LABEL org.opencontainers.image.revision=${WATT_REVISION} \
    watt.c3.source-tree=${WATT_TREE} \
    watt.c3.guardian-revision=${GUARDIAN_REVISION} \
    watt.c3.guardian-tree=${GUARDIAN_TREE} \
    watt.c3.ecf-revision=${ECF_REVISION} \
    watt.c3.ecf-tree=${ECF_TREE} \
    watt.c3.ecf-unsupported-revision=${ECF_UNSUPPORTED_REVISION} \
    watt.c3.base-image-id=${BASE_IMAGE_ID}

RUN python /opt/c3-build/attest_c3_image.py --build-inputs-only \
    && uv sync --locked --no-dev --no-editable --reinstall-package spg-runtime --offline \
    && python /opt/c3-build/attest_c3_image.py --output /opt/c3-build/build-attestation.json

USER spg
EXPOSE 8000
# Migration is a separate root-controlled isolated step. This deliberately does
# not invoke start_app.py, create spg_dev/spg_test, or bootstrap a default Product.
CMD ["python", "-m", "uvicorn", "spg.api.http:create_http_application", "--factory", "--host", "0.0.0.0", "--port", "8000"]