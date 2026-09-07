from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from spg.domain.interaction import (
    WorkAdmissionReadiness,
    WorkAdmissionReadinessStatus,
    WorkFocusClassification,
    WorkImpactDisposition,
)
from spg.providers.codex_interaction import CodexSdkWorkInteractionCapability


def _object_schemas(value: object, path: str = "$") -> Iterator[tuple[str, dict]]:
    if isinstance(value, dict):
        if "properties" in value:
            yield path, value
        for key, nested in value.items():
            yield from _object_schemas(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _object_schemas(nested, f"{path}[{index}]")


def _schema_nodes(value: object) -> Iterator[dict]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _schema_nodes(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _schema_nodes(nested)


def test_wic_provider_schema_is_recursively_strict_and_ref_safe() -> None:
    schema = CodexSdkWorkInteractionCapability.output_schema()
    for path, object_schema in _object_schemas(schema):
        assert set(object_schema["properties"]) == set(
            object_schema.get("required", [])
        ), path
        assert object_schema.get("additionalProperties") is False, path
    for node in _schema_nodes(schema):
        if "$ref" in node:
            assert set(node) == {"$ref"}


def test_ready_readiness_cannot_hide_material_questions() -> None:
    with pytest.raises(ValidationError, match="cannot retain material blockers"):
        WorkAdmissionReadiness(
            status=WorkAdmissionReadinessStatus.READY,
            profile="LONG_LIVED_STEERING",
            profile_version="v0",
            satisfied_requirements=("MOTIVE", "DESIRED_OUTCOME"),
            missing_information=(),
            unresolved_material_questions=("Which repository?",),
            reasons=("invalid",),
            basis_fingerprint="a" * 64,
        )


def test_wic3_provider_contract_exposes_bounded_focus_and_impact_taxonomies() -> None:
    schema = CodexSdkWorkInteractionCapability.output_schema()
    encoded = str(schema)
    assert {item.value for item in WorkFocusClassification} == {
        "ON_TOPIC",
        "RELEVANT_EXPLORATION",
        "SIDE_QUESTION",
        "MATERIAL_BRANCH",
        "UNRELATED_NEW_DEMAND",
    }
    assert {item.value for item in WorkImpactDisposition} == {
        "NO_GOVERNED_CHANGE",
        "CURRENT_CYCLE_REMAINS_VALID",
        "DEFER_TO_PRODUCTION_BOUNDARY",
        "CURRENT_RESULT_MAY_BE_INSUFFICIENT",
        "HUMAN_GOVERNANCE_REQUIRED",
        "NEW_WORK_RECOMMENDED",
    }
    assert "focus_classification" in encoded
    assert "impact_disposition" in encoded
    assert "supporting_references" in encoded
