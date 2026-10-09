"""Capture an immutable development overlay, not a baked-image qualification."""
from pathlib import Path
from datetime import UTC, datetime
from hashlib import sha256
import ast, json, subprocess, tarfile

WATT = Path(__file__).resolve().parents[4]
GUARDIAN = Path("D:/hy/c3-open-obligation-convergence/guardian")
DEST = WATT / ".c3-development-inputs" / "dev-regression-2"
assert not DEST.exists(), "Never overwrite a prior snapshot"
DEST.mkdir()

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

manifest = {"schema": "c3-development-inputs-v1", "directory": "dev-regression-2",
    "captured_at_utc": datetime.now(UTC).isoformat(), "sources": {}, "ast": {},
    "ecf_supported_revision": "5aa4f8833c359c15bd059eda5972aa3915bcc18c",
    "scope": "Targeted development regression; fixture records only; no live AI Work"}
for owner, root in (("watt", WATT), ("guardian", GUARDIAN)):
    prefixes = ("src/", "tests/", "migrations/", "docker/") if owner == "watt" else ("src/", "tests/")
    allowed_root = {"pyproject.toml", "uv.lock", "README.md", "alembic.ini"}
    paths = sorted(set(name for name in git(root, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()
        if name.startswith(prefixes) or name in allowed_root))
    changed = set(git(root, "diff", "--name-only", "HEAD").splitlines()) | set(git(root, "ls-files", "--others", "--exclude-standard").splitlines())
    ast_paths = [name for name in paths if name.endswith(".py") and name in changed]
    for name in ast_paths:
        ast.parse((root/name).read_text(encoding="utf-8"), filename=name)
    manifest["ast"][owner] = {"changed_python_files": ast_paths, "result": "PASS"}
    archive = DEST / (owner + "-dev-regression-2.tar")
    digests = {}
    with tarfile.open(archive, "w") as output:
        for name in paths:
            source = root/name
            assert source.is_file() and not source.is_symlink(), name
            raw = source.read_bytes()
            digests[name] = sha256(raw).hexdigest()
            output.add(source, arcname=name, recursive=False)
    manifest[owner] = {"archive": archive.name, "sha256": sha256(archive.read_bytes()).hexdigest(),
        "file_count": len(digests), "file_sha256": digests}
    manifest["sources"][owner] = {"head": git(root,"rev-parse","HEAD"), "head_tree":git(root,"rev-parse","HEAD^{tree}"),
        "uncommitted_overlay": bool(git(root,"status","--short")),
        "python_paths_sha256": sha256("".join(name + " " + digests[name] + "\n" for name in sorted(digests) if name.endswith(".py")).encode()).hexdigest()}
manifest["groups"] = [
    {"name": "watt-scoped", "nodes": [
        "tests/test_fulfillment_projection.py::test_source_scope_phase_and_method_rejections[current-future-MIXED_FACT_CURRENT_COMPONENT_LOST]",
        "tests/test_governed_obligation_fulfillment.py::test_delivery_owner_rechecks_current_admitted_prohibition",
        "tests/test_fulfillment_projection.py::test_original_scope_value_and_qualifiers_cannot_be_replaced_by_contract_paths",
        "tests/test_n1_static_html_semantics.py::test_model_repairs_only_derived_method_against_exact_human_source",
        "tests/test_n1_static_html_semantics.py::test_model_plan_exhaustion_cannot_invent_source_or_pass",
        "tests/test_c3_verification_receipts.py",
        "tests/test_c3_evidence_projection.py::test_planning_replacement_preserves_pending_observations_and_replay_budget"]},
    {"name": "guardian-scoped", "owner": "guardian", "nodes": ["tests/test_c3_phase_evidence.py",
        "tests/test_c1_governed_evidence_continuity.py", "tests/test_governed_obligation_evidence.py"]},
    {"name": "c1-chain", "nodes": ["tests/integration/test_c1_contract_continuity.py"]},
    {"name": "c3-carrier", "nodes": ["tests/integration/test_c3_fulfillment_receipts.py"]}]
manifest["prior_harness_gap"] = {"classification": "HARNESS_CONFIGURATION_ERROR",
    "snapshot": "dev-regression-1", "cause": "SPG_TEST_POSTGRES_DSN did not configure postgres_database; it requires SPG_TEST_DATABASE_URL",
    "observed": "C1 50 SKIPPED and carrier 2 SKIPPED, never counted PASS",
    "correction": "explicit isolated c1_contract_continuity SPG_TEST_DATABASE_URL in Snapshot 2"}
(DEST/"development-inputs.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
public = WATT/"docs/evidence/core-production-semantic-convergence-c3-20261009/dev-regression-2"
public.mkdir(exist_ok=False)
(public/"development-inputs.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"directory": manifest["directory"], "sources": manifest["sources"],
    "archives": {owner:{k:v for k,v in manifest[owner].items() if k!="file_sha256"} for owner in ("watt","guardian")},
    "ast_changed_count":{owner:len(manifest["ast"][owner]["changed_python_files"]) for owner in ("watt","guardian")}},indent=2))
