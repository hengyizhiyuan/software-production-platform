"""Bounded Quality campaign runner. Existing production recipes use a separate test DB."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from xml.etree import ElementTree

from sqlalchemy.engine import make_url

from spg.config import Settings
from spg.evaluation.catalog import recipes
from spg.evaluation.contracts import Evaluation, Evaluator, QualityError, Stage, fingerprint
from spg.evaluation.service import QualityService
from spg.infrastructure.persistence import Database


def assert_isolated_database(settings):
    if not settings.quality_test_database_url or not settings.database_url:
        raise QualityError("QUALITY_TEST_DATABASE_REQUIRED")
    p, t = make_url(settings.database_url), make_url(settings.quality_test_database_url)
    if (p.host, p.port, p.database) == (t.host, t.port, t.database):
        raise QualityError("QUALITY_CANNOT_USE_PRODUCTION_DATABASE")
    if not t.database or not t.database.endswith("_quality_test"):
        raise QualityError("QUALITY_TEST_DATABASE_NOT_EXPLICIT")


def recipe_result(settings, run, case, attempt_id):
    assert_isolated_database(settings)
    root = settings.quality_recipe_root
    r = recipes()[case["definition"]["runner_key"]]
    if r.key == "unqualified-scenario":
        raise QualityError("SCENARIO_RECIPE_NOT_QUALIFIED")
    selector = r.selector
    revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10, check=False)
    if revision.returncode or revision.stdout.strip() != run["watt_revision"]:
        raise QualityError("QUALIFICATION_EXACT_SOURCE_UNAVAILABLE")
    test_path = root / selector.split("::", 1)[0]
    if not test_path.is_file():
        raise QualityError("QUALIFICATION_RECIPE_UNAVAILABLE")
    variant = run["configuration"].get("experiment_variant")
    timeout = 600
    if variant:
        # v1 supports explicit bounded qualification policy experiments. It
        # cannot pretend that changing metadata applied an unimplemented model
        # route, production prompt or planning policy.
        if variant["provider"] != "qualification-fixture" or variant["model"] != "NOT_APPLICABLE":
            raise QualityError("EXPERIMENT_MODEL_ROUTE_NOT_QUALIFIED")
        policy = variant["policy"]
        if set(policy) != {"case_timeout_seconds"} or not isinstance(policy["case_timeout_seconds"], int):
            raise QualityError("EXPERIMENT_POLICY_NOT_QUALIFIED")
        timeout = policy["case_timeout_seconds"]
        if not 30 <= timeout <= 900:
            raise QualityError("EXPERIMENT_POLICY_OUT_OF_BOUNDS")
    env = dict(os.environ, SPG_DATABASE_URL=settings.quality_test_database_url,
        SPG_TEST_DATABASE_URL=settings.quality_test_database_url,
        PYTHONPATH=str(root / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""))
    if r.key not in {"brownfield", "promotion-recovery", "pilot-greenfield", "pilot-brownfield", "pilot-repository-only", "pilot-continuous-work"}:
        env["SPG_MANAGED_SOURCE_PROVIDER"] = "disabled"
    # Child test Applications are isolated and never start the Admin observer.
    env["SPG_ADMIN_ENABLED"] = "false"
    started = monotonic()
    with TemporaryDirectory(prefix="watt-quality-") as directory:
        xml, trace = Path(directory) / "result.xml", Path(directory) / "lineage.json"
        case_file = Path(directory) / "case.json"
        case_file.write_text(json.dumps(case["definition"]))
        case_file.chmod(0o600)
        env["WATT_QUALITY_CASE_FILE"] = str(case_file)
        env["WATT_QUALITY_LINEAGE_FILE"] = str(trace)
        product_file = Path(directory) / "product-evidence.json"
        env["WATT_QUALITY_PRODUCT_EVIDENCE_FILE"] = str(product_file)
        # Drain output with a hard cap; never retain provider credentials or
        # unbounded pytest output. Child process group is killed on quota/timeout.
        import selectors
        import signal
        process = subprocess.Popen([sys.executable, "-m", "pytest", selector, "-q",
            "-p", "spg.evaluation.pytest_lineage", "-p", "no:cacheprovider", "--disable-warnings", "--junitxml=" + str(xml)],
            cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        emitted = 0
        forced = None
        with selectors.DefaultSelector() as reader:
            reader.register(process.stdout, selectors.EVENT_READ)
            while process.poll() is None or reader.get_map():
                if monotonic() - started > timeout:
                    forced = 124
                    break
                for key, _ in reader.select(timeout=.2):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        reader.unregister(key.fileobj)
                    emitted += len(chunk)
                    if emitted > 2_000_000:
                        forced = 125
                        break
                if forced is not None:
                    break
        if forced is not None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        code = forced if forced is not None else process.wait()
        process.stdout.close()
        counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        if xml.exists() and xml.stat().st_size <= 2_000_000:
            for suite in ElementTree.parse(xml).iter("testsuite"):
                for key in counts:
                    counts[key] += int(suite.get(key, "0"))
        passed = code == 0 and counts["tests"] > 0 and counts["failures"] == counts["errors"] == counts["skipped"] == 0
        observed = json.loads(trace.read_text()) if trace.exists() and trace.stat().st_size <= 8_000_000 else []
        # An isolated PostgreSQL recipe must retain observed owner lineage.
        integration = selector.startswith("tests/integration/")
        lineage_present = any(x.get("owners") for x in observed)
        proof = "quality:case-run:" + str(attempt_id)
        details = {"oracle_id": r.key, "test_counts": counts, "exit_code": code,
            "isolated_database": True, "recipe_selector": selector,
            "managed_source_provider": env["SPG_MANAGED_SOURCE_PROVIDER"]}
        result = Evaluation(evaluator=Evaluator.DETERMINISTIC, outcome="PASS" if passed else "BLOCKED" if counts["errors"] or forced or counts["skipped"] or not counts["tests"] else "FAIL",
            evidence_refs=(proof,), evaluator_version="watt-canonical-recipe-v1",
            # A failing multi-stage test proves its oracle failed, not which
            # earlier semantic component caused it. Do not label fake precision.
            stage=None if not passed else r.stage,
            finding_code=None if passed else "QUALIFICATION_INFRASTRUCTURE_BLOCKED" if counts["errors"] or forced or counts["skipped"] or not counts["tests"] else "RECIPE_ORACLE_FAILED", details=details)
        runtime = Evaluation(evaluator=Evaluator.RUNTIME,
            outcome="PASS" if not integration or lineage_present else "BLOCKED",
            evidence_refs=(proof,), evaluator_version="isolated-owner-lineage-v1",
            finding_code=None if not integration or lineage_present else "OWNER_LINEAGE_UNAVAILABLE",
            details={"scope": "ISOLATED_QUALIFICATION", "owner_observations": len(observed),
                "observation_kind": "OWNER_SNAPSHOT" if integration else "PROCESS_EXIT", "exit_code": code})
        lineage = {"recipe": r.key, "recipe_fingerprint": fingerprint(r.__dict__),
            "watt_revision": run["watt_revision"], "configuration_fingerprint": run["policy_fingerprint"],
            "execution_environment": "ISOLATED_QUALIFICATION", "owner_observations": observed,
            "applied_experiment_variables": {} if variant is None else {"policy": {"case_timeout_seconds": timeout}},
            "model_observation": "configured WIC purpose profiles" if r.key == "sealed-live-intent" else "NOT_APPLICABLE",
            "provider_observation": settings.wic_provider_adapter if r.key == "sealed-live-intent" else "qualification-fixture"}
        if product_file.exists() and product_file.stat().st_size <= 500_000:
            lineage["product_evidence"] = json.loads(product_file.read_text())
        if r.key == "pilot-live-search":
            lineage["provider_observation"] = "aliyun-opensearch:live"
            lineage["model_observation"] = settings.wic_provider_adapter + ":live-semantic-compiler-and-research"
        results = [result, runtime]
        guardian = [g for o in observed for g in o.get("guardian_results", [])]
        if r.key in {"guardian-acceptance", "pilot-guardian"}:
            known_match = bool(guardian) and all(g["gate"] == "PASS" for g in guardian)
            results.append(Evaluation(evaluator=Evaluator.GUARDIAN,
                outcome="PASS" if known_match else "FAIL" if guardian else "BLOCKED",
                evidence_refs=tuple("guardian:assurance-result:" + str(g["request_id"]) for g in guardian) or (proof,),
                evaluator_version="independent-default-gate-oracle-v1", stage=Stage.GUARDIAN,
                finding_code=None if known_match else "GUARDIAN_KNOWN_CASE_MISMATCH",
                details={"expected_outcome": "PASS", "observed_results": guardian,
                    "independent_oracle": result.outcome, "sole_oracle": False,
                    "potential_false_positive": bool(guardian) and not passed,
                    "potential_false_negative": bool(guardian) and any(g["gate"] != "PASS" for g in guardian)}))
        return tuple(results), lineage, monotonic() - started


def run_once(service):
    run = service.claim_run()
    if run is None:
        return None
    for case in service.run_members(run["id"]):
        if not service.checkpoint(run):
            return service.run_detail(run["id"])
        aid = service.begin_case(run, case["id"])
        if aid is None:
            continue
        try:
            results, lineage, elapsed = recipe_result(service.settings, run, case, aid)
        except Exception as error:
            code = error.code if isinstance(error, QualityError) else "QUALITY_RUNNER_ERROR"
            results = (Evaluation(evaluator=Evaluator.DETERMINISTIC, outcome="BLOCKED",
                evidence_refs=("quality:case-run:" + str(aid),), evaluator_version="quality-runner-v1",
                finding_code=code, details={"error_type": type(error).__name__}),)
            lineage, elapsed = {"runner_error": code}, 0
        service.finish_case(run, aid, results, lineage, elapsed)
        print(json.dumps({"campaign_run": str(run["id"]), "case": case["definition"]["title"],
            "observations": [e.outcome for e in results]}, ensure_ascii=False), flush=True)
    if not service.checkpoint(run):
        return service.run_detail(run["id"])
    return service.finish_run(run)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    s = Settings()
    assert_isolated_database(s)
    d = Database.from_settings(s)
    service = QualityService(d, s)
    try:
        while True:
            run_once(service)
            if args.once:
                break
            sleep(5)
    finally:
        d.dispose()


if __name__ == "__main__":
    main()
