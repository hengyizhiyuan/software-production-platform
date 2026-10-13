"""Export integrity, authority boundaries and missing-stage semantics."""
from hashlib import sha256
from io import BytesIO
import json
from uuid import uuid4
from zipfile import ZipFile

import pytest

from spg.evaluation.contracts import QualityError
from spg.evaluation.work_diagnostic_export import WorkDiagnosticExportService, Redactor


class Registry:
    def __init__(self, expected):
        self.expected = expected
        self.calls = []

    def get(self, owner, work_id):
        self.calls.append((owner, work_id))
        if owner != "human:owner" or work_id != self.expected:
            raise QualityError("TRACE_SOURCE_NOT_FOUND")
        return {"work_id":str(work_id),"product_id":str(uuid4()),
            "title":"停在 DESIGN 的 Work", "state":"BLOCKED", "state_label":"受阻",
            "stage_label":"设计", "stop_reason":"HUMAN_ATTENTION"}


class Traces:
    def __init__(self):
        self.calls = []

    def entity_trace(self, kind, work_id, *, work, detail, max_rows_per_table):
        self.calls.append((kind, work_id, detail, max_rows_per_table))
        return {"schema_version":"production-trace-v1", "scene":work["title"],
            "work":work,"story":{"latest_activity_at":"2026-10-09T01:00:00Z"},
            "basis":{"mode":"LIVE_ENTITY_LOOKUP","at":"2026-10-09T01:00:01Z"},
            "first_human_input":"请做设计。password=secret-fixture-123 and user@example.com",
            "conversation":[{"actor":"HUMAN","text":"请做设计。Bearer fixture-long-secret-1234567890",
                "source_ref":"interaction-record:first","timestamp":"2026-10-09T01:00:00Z"}],
            "semantic":[],"contexts":[],"steering":[{"id":"step","state":"CURRENT"}],
            "units":[],"queue":[],"model_calls":[],"recovery":[],"verification":[],
            "candidate":[],"guardian":[],"governance":[],"manifests":[],
            "timeline":[{"title":"Human 决定待处理","owner":"STEERING","state":"BLOCKED",
                "source_ref":"steering_decisions:decision","timestamp":"2026-10-09T01:00:02Z",
                "detail":{"note":"token=secret-fixture-123","nested":{"api_key":"fixture-key"}}}],
            "advanced":{"owners":{"steering_decisions":[{"id":"decision","reason":"缺少 Human 决定"}]}} if detail else {}}


def service():
    work_id = uuid4()
    exporter = object.__new__(WorkDiagnosticExportService)
    exporter.registry = Registry(work_id)
    exporter.traces = Traces()
    return exporter, work_id


@pytest.mark.parametrize("mode", ["compact", "full"])
def test_design_stall_zip_has_matching_hashes_and_no_fabricated_production(mode):
    exporter, work_id = service()
    data = exporter.zip("human:owner", work_id, mode=mode)
    with ZipFile(BytesIO(data)) as archive:
        assert set(archive.namelist()) == {"report.md", "trace.json", "diagnosis-context.md", "evidence-manifest.json"}
        manifest = json.loads(archive.read("evidence-manifest.json"))
        for name, item in manifest["exported_files"].items():
            assert sha256(archive.read(name)).hexdigest() == item["sha256"]
            assert len(archive.read(name)) == item["bytes"]
        report = archive.read("report.md").decode()
        trace = json.loads(archive.read("trace.json"))
    assert "PWU: NOT_REACHED_OR_NOT_OBSERVED" in report
    assert "Candidate: NOT_REACHED_OR_NOT_OBSERVED" in report
    assert "steering_decisions:decision" in report
    assert trace["lifecycle"]["units"] == [] and trace["lifecycle"]["candidate"] == []
    assert "secret-fixture-123" not in str(trace) + report
    assert "user@example.com" not in str(trace) + report
    assert manifest["capture_consistency"] == "NON_ATOMIC_ACROSS_OWNERS"
    assert manifest["source_revision"] is None and manifest["source_tree"] is None
    assert exporter.traces.calls[0][2] == (mode == "full")


def test_wrong_owner_is_rejected_before_trace_read():
    exporter, work_id = service()
    with pytest.raises(QualityError, match="TRACE_SOURCE_NOT_FOUND"):
        exporter.zip("human:other", work_id)
    assert exporter.traces.calls == []


def test_productless_work_has_no_export_owner_proof():
    exporter, work_id = service()
    exporter.registry.get = lambda _owner, _wid: {'work_id':str(work_id),'product_id':None}
    with pytest.raises(QualityError) as error:
        exporter.zip('human:owner', work_id)
    assert error.value.code == 'TRACE_SOURCE_NOT_FOUND'
    assert exporter.traces.calls == []


def test_only_fixed_file_names_are_downloadable():
    exporter, work_id = service()
    with pytest.raises(QualityError, match="DIAGNOSTIC_FILE_NOT_SUPPORTED"):
        exporter.file("human:owner", work_id, mode="compact", name="../../qa.env")
    assert exporter.registry.calls == []


def test_nested_secrets_and_large_text_are_marked():
    clean = Redactor(text_limit=40)
    result = clean.clean({"headers":{"Authorization":"Bearer abcdefghijklmnopqrstuvwxyz",
        "X-API-KEY":"nested-fixture-key", "Set-Cookie":"sessionid=nested-fixture-cookie"},
        "payload":{"api_key":"hidden","safe":"x" * 100},
        "url":"https://alice:password@example.test/path?X-Amz-Signature=abc123456789",
        "log":"OPENAI_API_KEY=environment-fixture-secret"})
    assert "hidden" not in str(result) and "alice:password" not in str(result)
    assert "nested-fixture" not in str(result) and "environment-fixture-secret" not in str(result)
    assert "abc123456789" not in str(result)
    assert "TRUNCATED_TEXT" in str(result)
    assert clean.redacted >= 2 and clean.shortened >= 1


def test_size_limit_fails_explicitly_without_partial_false_complete(monkeypatch):
    exporter, work_id = service()
    monkeypatch.setenv("SPG_DIAGNOSTIC_EXPORT_MAX_BYTES", "1024")
    with pytest.raises(QualityError) as error:
        exporter.zip("human:owner", work_id)
    assert error.value.code == "DIAGNOSTIC_EXPORT_SIZE_LIMIT"


def test_full_overflow_yields_explicit_partial_package_with_failure_chain(monkeypatch):
    exporter, work_id = service()
    original = exporter.traces.entity_trace
    def verbose(*args, **kwargs):
        trace = original(*args, **kwargs)
        trace['advanced'] = {'owners':{'execution_events':[
            {'id':str(uuid4()),'payload':'x'*1000} for _ in range(100)]}}
        trace['timeline'].append({'title':'真实失败','state':'FAIL','source_ref':'execution_events:failure',
            'timestamp':'2026-10-09T01:00:03Z','detail':{'event_type':'ExecutionFailed'}})
        return trace
    exporter.traces.entity_trace = verbose
    monkeypatch.setenv('SPG_DIAGNOSTIC_EXPORT_MAX_BYTES','25000')
    body = exporter.capture('human:owner', work_id, mode='full')
    manifest = json.loads(body['evidence-manifest.json'])
    trace = json.loads(body['trace.json'])
    assert manifest['truncated_records']['advanced_owner_rows']['execution_events'] == 100
    assert 'Full owner row bodies excluded' in str(manifest['capture_warnings'])
    assert 'execution_events:failure' in body['report.md'].decode()
    assert sum(map(len, body.values())) <= 25000
