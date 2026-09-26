import json
from uuid import uuid4

import pytest

from spg.domain.production_environment import EnvironmentProviderError
from spg.infrastructure.candidate_preview_runtime import DockerCandidatePreviewRuntime


def test_bounded_supporting_service_declaration_fails_explicitly(tmp_path):
    provider = DockerCandidatePreviewRuntime(tmp_path)
    preview_id = uuid4()
    assert provider._supporting_services(preview_id) == ()
    declaration = provider._workspace(preview_id) / ".watt" / "preview-topology.json"
    declaration.parent.mkdir(parents=True)
    declaration.write_text(json.dumps({"schema_version": 1,
        "supporting_services": ["redis"]}))
    assert provider._supporting_services(preview_id) == ("redis",)
    declaration.write_text(json.dumps({"schema_version": 1,
        "supporting_services": ["arbitrary-container"]}))
    with pytest.raises(EnvironmentProviderError, match="unsupported preview topology"):
        provider._supporting_services(preview_id)
