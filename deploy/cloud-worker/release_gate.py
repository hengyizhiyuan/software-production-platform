"""Three-project release-unit gate: run inside the built image before deploy.

Proves the baked Guardian/ECF sources are the ones pinned in owners.lock and
that every cross-Owner contract construct Watt depends on is accepted by them.
Network-free and side-effect free. Exit code is the gate.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path


def tree_digest(src: Path) -> str:
    digest = hashlib.sha256()
    files = [p for p in src.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    for path in sorted(files, key=lambda p: p.relative_to(src).as_posix().encode()):
        digest.update(path.relative_to(src).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def check_lock(results: dict) -> None:
    lock = json.loads(Path("/app/owners.lock").read_text(encoding="utf-8"))
    import ecf
    import guardian
    for name, module in (("ecf", ecf), ("guardian", guardian)):
        src = Path(inspect.getfile(module)).parents[1]
        expected = lock["owners"][name]
        actual = tree_digest(src)
        assert str(src) == f"/opt/watt-owners/{name}/src", (name, str(src))
        assert actual == expected["source_digest"], (name, actual)
        results[name] = {"commit": expected["commit"], "source_digest": actual, "import_root": str(src)}


def check_guardian_contract(results: dict) -> None:
    """Every AssuranceRequest field and companion type Watt sends must exist."""
    from guardian.contracts import software_assurance as sa
    from guardian.runtime import JsonAssuranceIntakeStore, JsonSoftwareAssuranceStore
    import spg.application.guardian_assurance as watt
    source = inspect.getsource(watt)
    imported = {name for line in source.splitlines() if "from guardian.contracts.software_assurance import" in line
        for name in line.split("import", 1)[1].replace("(", " ").replace(")", " ").replace(",", " ").split()}
    missing_types = sorted(name for name in imported if not hasattr(sa, name))
    assert not missing_types, ("guardian types missing", missing_types)
    start = source.index("request = AssuranceRequest(")
    block = source[start:source.index("results.append(", start)]
    import re
    sent = set(re.findall(r"\b([a-z_]+)=", block)) - {"if", "else"}
    sent |= {"production_lineage"} if "production_lineage" in block else set()
    unknown = sorted(name for name in sent if name not in sa.AssuranceRequest.model_fields)
    assert not unknown, ("AssuranceRequest fields rejected by Guardian", unknown)
    versions = sa.AssuranceRequest.model_fields["evidence_contract_version"].metadata
    assert any("governed-obligation-v2" in str(item) for item in versions), "evidence_contract_version v2 unsupported"
    assert hasattr(JsonSoftwareAssuranceStore, "assess") and JsonAssuranceIntakeStore is not None
    resolver = "owner_evidence_resolver" in inspect.signature(JsonSoftwareAssuranceStore).parameters
    assert resolver, "Guardian store lacks owner_evidence_resolver"
    from guardian.production_brief import CONTRACTS as guardian_briefs, source_preserving_plan, review_readiness_evidence
    from spg.application.production_brief import CONTRACTS as watt_briefs
    assert guardian_briefs == watt_briefs and callable(source_preserving_plan) and callable(review_readiness_evidence), "unchanged production brief unsupported"
    results["guardian_production_brief"] = {"contracts": sorted(guardian_briefs), "independent_source_validation": True}
    results["guardian_contract"] = {"types": sorted(imported), "request_fields": sorted(sent), "owner_evidence_resolver": resolver}


def check_ecf_contract(results: dict) -> None:
    import ecf.decision_context as dc
    from ecf.runtime import ECFRealityRuntime, JsonRealityStore
    import spg.application.decision_context as watt
    assert dc.VERSION == "0.1", dc.VERSION
    assert callable(dc.assemble_context)
    managed = getattr(watt, "MANAGED_WEB_SURFACE", None)
    if managed:
        text = inspect.getsource(dc)
        assert "MANAGED_GREENFIELD_PRODUCTION" in text, "ECF lacks managed greenfield contract"
    for method in ("discover_repository", "admit_workspace"):
        assert hasattr(ECFRealityRuntime, method), method
    assert JsonRealityStore is not None
    results["ecf_contract"] = {"version": dc.VERSION, "managed_greenfield": bool(managed)}


def main() -> int:
    results: dict = {}
    failures = []
    for check in (check_lock, check_guardian_contract, check_ecf_contract):
        try:
            check(results)
        except Exception as error:  # report every failed gate, not only the first
            failures.append({"check": check.__name__, "error": repr(error)[:600]})
    print(json.dumps({"status": "PASS" if not failures else "FAIL", "results": results, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
