"""Attest a built C2 image without reading ENV secrets or exercising Work.

The parent creates c2-source-identity.json from frozen exact Git archives:
schema=c2-source-identity-v1; sources.{watt,guardian,ecf,ecf-unsupported}
have revision/tree; base_image has reference/image_id; build_input_sha256 maps
every COPY input's context-relative path to SHA256. archive_sha256 records
retained archives. The identity JSON excludes its own digest from that map.

Use --build-inputs-only before uv sync, then full mode after reinstall and in
the actual newly built image. Root must separately inspect Docker image/labels
and base tag identity. An optional --image-id is caller-observed Docker metadata,
not a value this process independently obtains through a Docker socket.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

BASE_IMAGE_ID = "sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14"
LOCK_SHA256 = "279fba19bb5a40457739e49408137190d3d6f8e2e7171a273b3e742bae12a038"
ARTIFACT_PREFIX = "watt/docs/evidence/core-production-execution-readiness-c2-20261009/"
PREFIX_TARGETS = {
    "watt/src/": (Path("/app/src"),),
    "watt/migrations/": (Path("/app/migrations"), Path("/qualification/migrations")),
    "watt/docker/": (Path("/app/docker"),),
    "watt/tests/": (Path("/qualification/tests"),),
    "guardian/src/": (Path("/opt/c2-owners/guardian/src"),),
    "ecf/src/": (Path("/opt/c2-owners/ecf/src"),),
    "ecf-unsupported/src/": (Path("/qualification/ecf-current/src"),),
    "test-deps/": (Path("/opt/c2-test-deps"),),
}
FILE_TARGETS = {
    "watt/pyproject.toml": (Path("/app/pyproject.toml"), Path("/qualification/pyproject.toml")),
    "watt/uv.lock": (Path("/app/uv.lock"),),
    "watt/alembic.ini": (Path("/app/alembic.ini"), Path("/qualification/alembic.ini")),
    "watt/README.md": (Path("/app/README.md"),),
    ARTIFACT_PREFIX + "Dockerfile.c2": (Path("/opt/c2-build/Dockerfile.c2"),),
    ARTIFACT_PREFIX + "attest_c2_image.py": (Path("/opt/c2-build/attest_c2_image.py"),),
}
FIXED_OWNERS = {
    "guardian": ("6b974748df22d84b88f6908ea8ee90a9752fd183", "c9a1bf4e102d8365a1ce27c9cced88f8ab0cd129"),
    "ecf": ("5aa4f8833c359c15bd059eda5972aa3915bcc18c", "878d39d9c259272bb05f2e02bdf9d60c22fad460"),
    "ecf-unsupported": ("c6b568d006022e39b95daebedfecfb55e562ebe5", "f102fa082bbd0a1abd827e77d6aa1340db8b83c5"),
}
SOURCE_ENV = {
    "watt": ("SPG_RUNTIME_REVISION", "C2_WATT_TREE"),
    "guardian": ("C2_GUARDIAN_REVISION", "C2_GUARDIAN_TREE"),
    "ecf": ("C2_ECF_REVISION", "C2_ECF_TREE"),
    "ecf-unsupported": ("C2_ECF_UNSUPPORTED_REVISION", "C2_ECF_UNSUPPORTED_TREE"),
}


class AttestationFailure(Exception):
    def __init__(self, code: str, relative_path: str | None = None):
        self.code = code
        self.relative_path = relative_path


def require(condition: bool, code: str, path: str | None = None) -> None:
    if not condition:
        raise AttestationFailure(code, path)


def digest(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK_INPUT")
    result = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def targets(relative: str) -> tuple[Path, ...]:
    if relative in FILE_TARGETS:
        return FILE_TARGETS[relative]
    for prefix, roots in PREFIX_TARGETS.items():
        if relative.startswith(prefix):
            suffix = relative[len(prefix):]
            require(bool(suffix), "INVALID_INPUT_PATH", relative)
            return tuple(root / suffix for root in roots)
    raise AttestationFailure("UNSUPPORTED_BUILD_INPUT", relative)


def regular_files(root: Path, *, generated_egg_info: bool = False) -> set[str]:
    require(root.is_dir() and not root.is_symlink(), "MISSING_SOURCE_DIRECTORY")
    result = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if generated_egg_info and any(part.endswith(".egg-info") for part in relative.parts):
            continue
        require(not path.is_symlink(), "SOURCE_SYMLINK", relative.as_posix())
        if path.is_file():
            result.add(relative.as_posix())
    return result


def validate_identity(identity: dict) -> dict[str, str]:
    require(isinstance(identity, dict) and identity.get("schema") == "c2-source-identity-v1",
            "IDENTITY_SCHEMA_MISMATCH")
    sources = identity.get("sources")
    require(isinstance(sources, dict) and set(sources) == set(SOURCE_ENV),
            "SOURCE_IDENTITY_SET_MISMATCH")
    for owner, env_names in SOURCE_ENV.items():
        source = sources[owner]
        require(isinstance(source, dict), "INVALID_SOURCE_IDENTITY", owner)
        values = (source.get("revision"), source.get("tree"))
        require(all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value)
                    for value in values), "INVALID_SOURCE_REVISION_OR_TREE", owner)
        if owner in FIXED_OWNERS:
            require(values == FIXED_OWNERS[owner], "OWNER_REVISION_NOT_SELECTED", owner)
        require(tuple(os.environ.get(key) for key in env_names) == values,
                "SOURCE_ENV_IDENTITY_MISMATCH", owner)
    base = identity.get("base_image")
    require(isinstance(base, dict) and base.get("image_id") == BASE_IMAGE_ID,
            "BASE_IMAGE_DECLARATION_MISMATCH")
    require(base.get("image_id") == os.environ.get("C2_BASE_IMAGE_ID")
            and base.get("reference") == os.environ.get("C2_BASE_IMAGE_REF"),
            "BASE_IMAGE_ENV_MISMATCH")
    hashes = identity.get("build_input_sha256")
    require(isinstance(hashes, dict) and bool(hashes), "MISSING_BUILD_INPUT_HASHES")
    for relative, value in hashes.items():
        require(isinstance(relative, str) and "\\" not in relative
                and not PurePosixPath(relative).is_absolute()
                and all(part not in {"", ".", ".."} for part in relative.split("/")),
                "INVALID_BUILD_INPUT_PATH")
        require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
                "INVALID_BUILD_INPUT_DIGEST", relative)
        targets(relative)
    require(all(path in hashes for path in FILE_TARGETS), "MISSING_REQUIRED_INPUT")
    archive_hashes = identity.get("archive_sha256")
    require(isinstance(archive_hashes, dict) and bool(archive_hashes)
            and all(isinstance(name, str) and isinstance(value, str)
                    and re.fullmatch(r"[0-9a-f]{64}", value)
                    for name, value in archive_hashes.items()),
            "INVALID_ARCHIVE_DIGEST_DECLARATION")
    require(hashes["watt/uv.lock"] == LOCK_SHA256, "DEPENDENCY_LOCK_MISMATCH")
    return hashes


def verify_build_inputs(hashes: dict[str, str]) -> dict:
    verified = {}
    for relative, expected in sorted(hashes.items()):
        image_files = []
        for target in targets(relative):
            observed = digest(target)
            require(observed == expected, "BUILD_INPUT_CONTENT_MISMATCH", relative)
            image_files.append({"path": str(target), "sha256": observed})
        verified[relative] = {"sha256": expected, "image_files": image_files}
    # Prove complete COPY source sets, not merely the subset listed by the caller.
    for prefix, roots in PREFIX_TARGETS.items():
        expected = {path[len(prefix):] for path in hashes if path.startswith(prefix)}
        require(bool(expected), "MISSING_INPUT_DIRECTORY", prefix)
        for root in roots:
            actual = regular_files(root, generated_egg_info=prefix == "watt/src/")
            require(actual == expected, "BUILD_INPUT_INVENTORY_MISMATCH", prefix)
    return verified


def verify_imported_packages(hashes: dict[str, str]) -> dict:
    result = {}
    for owner, prefix, fixed_root in (
        ("spg", "watt/src/spg/", None),
        ("guardian", "guardian/src/guardian/", Path("/opt/c2-owners/guardian/src/guardian")),
        ("ecf", "ecf/src/ecf/", Path("/opt/c2-owners/ecf/src/ecf")),
    ):
        module = importlib.import_module(owner)
        module_file = Path(module.__file__).resolve()
        actual_root = module_file.parent
        if owner == "spg":
            distribution = importlib.metadata.distribution("spg-runtime")
            expected_root = Path(distribution.locate_file("spg")).resolve()
            venv_root = Path("/opt/spg-venv").resolve()
            require(expected_root.is_relative_to(venv_root), "SPG_NOT_INSTALLED_IN_VENV")
            require(actual_root == expected_root, "SPG_SOURCE_OVERLAY_DETECTED")
        else:
            require(actual_root == fixed_root, "OWNER_SOURCE_OVERLAY_DETECTED", owner)
        expected = {path[len(prefix):]: value for path, value in hashes.items()
                    if path.startswith(prefix)}
        require(bool(expected) and regular_files(actual_root) == set(expected),
                "IMPORTED_PACKAGE_INVENTORY_MISMATCH", owner)
        observed = {}
        for relative, value in sorted(expected.items()):
            actual = digest(actual_root / relative)
            require(actual == value, "IMPORTED_PACKAGE_CONTENT_MISMATCH", owner + "/" + relative)
            observed[relative] = actual
        result[owner] = {"module_file": str(module_file), "package_root": str(actual_root),
                         "verified_file_count": len(observed), "file_sha256": observed}
    pytest = importlib.import_module("pytest")
    require(Path(pytest.__file__).resolve().is_relative_to(Path("/opt/c2-test-deps")),
            "PYTEST_DEPENDENCY_OVERLAY_DETECTED")
    result["pytest"] = {"module_file": str(Path(pytest.__file__).resolve()),
                        "version": pytest.__version__}
    return result


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "UNKNOWN: distribution metadata unavailable"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("/opt/c2-build/c2-source-identity.json"))
    parser.add_argument("--build-inputs-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--image-id")
    args = parser.parse_args()
    try:
        if args.image_id is not None:
            require(re.fullmatch(r"sha256:[0-9a-f]{64}", args.image_id) is not None,
                    "INVALID_CALLER_IMAGE_ID")
        identity = json.loads(args.manifest.read_text(encoding="utf-8"))
        hashes = validate_identity(identity)
        verified = verify_build_inputs(hashes)
        imported = {} if args.build_inputs_only else verify_imported_packages(hashes)
        receipt = {
            "schema": "c2-built-image-attestation-v1",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS",
            "scope": "build-inputs-only" if args.build_inputs_only else "actual-installed-imports",
            "manifest_sha256": digest(args.manifest),
            "sources": identity["sources"],
            "base_image_declared": identity["base_image"],
            "base_image_requires_separate_host_inspect": True,
            "caller_observed_image_id": args.image_id,
            "archive_sha256_declared": identity["archive_sha256"],
            "build_input_sha256_verified": verified,
            "actual_imports": imported,
            "python": sys.version,
            "uid": os.getuid(),
            "gid": os.getgid(),
            "groups": os.getgroups(),
            "package_versions": {} if args.build_inputs_only else {
                name: package_version(name) for name in
                ("spg-runtime", "pytest", "sqlalchemy", "psycopg", "pydantic", "alembic", "httpx")
            },
            "not_runtime_or_work_qualification": True,
        }
        encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        if args.output:
            require(args.output != args.manifest, "OUTPUT_WOULD_REPLACE_MANIFEST")
            args.output.write_text(encoded, encoding="utf-8")
            print(json.dumps({"status": "PASS", "scope": receipt["scope"],
                              "build_input_count": len(verified),
                              "actual_package_counts": {
                                  name: item.get("verified_file_count") for name, item in imported.items()
                              }, "receipt_path": str(args.output)}, sort_keys=True))
        else:
            print(encoded, end="")
        return 0
    except AttestationFailure as error:
        print(json.dumps({"status": "FAIL", "finding_code": error.code,
                          "relative_path": error.relative_path}, sort_keys=True))
    except Exception as error:
        # Never print exception text or the environment; either may contain secrets.
        print(json.dumps({"status": "FAIL", "finding_code": "ATTESTATION_UNAVAILABLE",
                          "exception_type": type(error).__name__}, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())