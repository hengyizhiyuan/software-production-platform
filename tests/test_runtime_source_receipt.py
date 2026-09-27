from benchmarks.intent_realization.runtime.evidence import source_receipt


def test_packaging_metadata_is_not_runtime_source_but_all_executable_roots_are(tmp_path, monkeypatch):
    paths = ["src/spg/owner.py", "migrations/versions/revision.py", "docker/entrypoint.sh",
        "src/spg.egg-info/PKG-INFO", "src/spg.egg-info/SOURCES.txt",
        "src/spg/__pycache__/owner.pyc"]
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path)
    monkeypatch.setattr("benchmarks.intent_realization.runtime.evidence.subprocess.check_output",
        lambda argv, **kwargs: "" if "status" in argv else "qualified-revision")
    first = source_receipt(tmp_path)
    assert set(first["source_hashes"]) == set(paths[:3])
    (tmp_path / paths[3]).write_text("regenerated packaging metadata")
    assert source_receipt(tmp_path)["source_fingerprint"] == first["source_fingerprint"]
    (tmp_path / paths[0]).write_text("changed owner implementation")
    assert source_receipt(tmp_path)["source_fingerprint"] != first["source_fingerprint"]
