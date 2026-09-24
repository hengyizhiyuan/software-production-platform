import json
from collections.abc import Iterator
from typing import Any

import pytest

from spg.domain.change import ProductionTargetKind
from spg.domain.planning import PlannedArtifactOperation
from spg.domain.steering import SemanticProductionProposal, SteeringInvariantViolation
from spg.providers.semantic_wire import (
    SemanticStepWireContract,
    _admitted_derived_constraints,
    _provider_strict_output_schema,
)


def _payload(proposed_production: object = None) -> dict[str, object]:
    return {
        "bounded_summary": "A bounded semantic direction grounded in current Reality.",
        "decisions": ["Reuse the existing governed Work and Steering seams."],
        "derived_constraints": [],
        "proposed_production": proposed_production,
        "disposition": {
            "state": "RESOLVED",
            "authority_assessment": "WITHIN_AUTHORITY",
            "unresolved_questions": [],
            "human_attention_recommendation": None,
            "completion_claimed": True,
        },
    }


def _object_schemas(value: object, path: str = "$") -> Iterator[tuple[str, dict]]:
    if isinstance(value, dict):
        if "properties" in value:
            yield path, value
        for key, nested in value.items():
            yield from _object_schemas(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _object_schemas(nested, f"{path}[{index}]")


def _schema_nodes(value: object, path: str = "$") -> Iterator[tuple[str, dict]]:
    if isinstance(value, dict):
        yield path, value
        for key, nested in value.items():
            yield from _schema_nodes(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _schema_nodes(nested, f"{path}[{index}]")


def _proposal_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return schema["$defs"]["_SemanticProviderProductionProposal"]


def test_sem_wire_01_03_04_05_08_09_10_15_schema_is_recursively_strict() -> None:
    schema = SemanticStepWireContract.output_schema()

    object_schemas = tuple(_object_schemas(schema))
    assert object_schemas
    for path, object_schema in object_schemas:
        assert set(object_schema["properties"]) == set(
            object_schema.get("required", [])
        ), path
        assert object_schema.get("additionalProperties") is False, path

    ref_schemas = tuple(
        (path, node) for path, node in _schema_nodes(schema) if "$ref" in node
    )
    assert ref_schemas
    for path, ref_schema in ref_schemas:
        assert set(ref_schema) == {"$ref"}, path

    assert set(schema["properties"]) == set(schema["required"])
    assert "anyOf" not in schema
    disposition = schema["properties"]["disposition"]
    assert len(disposition["anyOf"]) == 3
    assert all(set(branch) == {"$ref"} for branch in disposition["anyOf"])
    resolved = schema["$defs"]["_SemanticProviderResolvedDisposition"]
    resolved_questions = resolved["properties"]["unresolved_questions"]
    assert resolved_questions["items"] == {"type": "string"}
    assert resolved_questions["maxItems"] == 0
    proposal = _proposal_schema(schema)
    assert set(proposal["properties"]) == set(proposal["required"])
    assert "artifact_targets" in proposal["required"]
    assert schema["$defs"]["ProductionTargetKind"]["enum"] == [
        "DOCUMENTATION_WORK",
        "CODE_WORK",
    ]
    assert proposal["properties"]["artifact_targets"]["items"] == {
        "$ref": "#/$defs/ProductionPlanArtifactTarget"
    }
    assert proposal["properties"]["allowed_areas"]["items"]["pattern"] == (
        r"^[^/]+/[^/]+(?:/[^/]+)*/\*\*$"
    )


def test_sem_ref_01_02_03_04_16_dogfood_6_ref_sibling_is_normalized() -> None:
    observed_dogfood_schema = {
        "properties": {
            "target_kind": {
                "$ref": "#/$defs/ProductionTargetKind",
                "description": (
                    "Existing Watt production target kind; "
                    "no provider-defined aliases."
                ),
            }
        }
    }

    normalized = _provider_strict_output_schema(observed_dogfood_schema)

    assert observed_dogfood_schema["properties"]["target_kind"] == {
        "$ref": "#/$defs/ProductionTargetKind",
        "description": (
            "Existing Watt production target kind; no provider-defined aliases."
        ),
    }
    assert normalized["properties"]["target_kind"] == {
        "$ref": "#/$defs/ProductionTargetKind"
    }
    proposal = _proposal_schema(SemanticStepWireContract.output_schema())
    assert proposal["properties"]["target_kind"] == {
        "$ref": "#/$defs/ProductionTargetKind"
    }


def test_sem_wire_02_domain_defaults_remain_unchanged() -> None:
    proposal = SemanticProductionProposal(
        target_kind=ProductionTargetKind.CODE_WORK,
        objective="Improve bounded progress observability",
        code_targets=("src/spg/web/app.js",),
        verification_expectation="Focused API and UI tests",
    )

    assert proposal.artifact_targets == ()
    assert proposal.allowed_areas == ()
    assert proposal.forbidden_areas == ()


def test_semantic_code_proposal_rejects_the_same_allowed_and_forbidden_area() -> None:
    with pytest.raises(ValueError, match="allowed area conflicts"):
        SemanticProductionProposal(
            target_kind=ProductionTargetKind.CODE_WORK,
            objective="Add the Work navigation link",
            allowed_areas=("src/spg/application/**",),
            forbidden_areas=("src/spg/application/**",),
            verification_expectation="Check the rendered link",
        )


def test_sem_wire_03_04_06_no_production_round_trip_uses_explicit_values() -> None:
    wire = SemanticStepWireContract._parse_payload(json.dumps(_payload()))

    assert wire.derived_constraints == ()
    assert wire.unresolved_questions == ()
    assert wire.human_attention_recommendation is None
    assert wire.proposed_production is None
    assert wire.domain_production_proposal() is None


def test_provider_inference_cannot_become_unadmitted_constraint_truth() -> None:
    payload = _payload()
    payload["derived_constraints"] = [
        "Preserve data",
        "Use the model's preferred framework",
    ]
    wire = SemanticStepWireContract._parse_payload(json.dumps(payload))
    semantic_input = type(
        "ConstraintInput",
        (),
        {"constraints": ("Preserve data",)},
    )()

    assert _admitted_derived_constraints(wire, semantic_input) == (
        "Preserve data",
    )


def test_deepseek_annotation_tolerance_preserves_strict_semantic_fields() -> None:
    payload = _payload(
        {
            "target_kind": "CODE_WORK",
            "objective": "Create the bounded browser page",
            "artifact_targets": [],
            "code_targets": ["index.html", "verify/click-alert.mjs"],
            "code_targets_note": "Provider explanation, not semantic contract data.",
            "allowed_areas": [],
            "forbidden_areas": [],
            "verification_expectation": "Verify the click alert behavior",
        }
    )
    payload["provider_note"] = "Transport-only prose."

    parsed = SemanticStepWireContract._parse_payload_ignoring_annotations(
        json.dumps(payload)
    )

    assert parsed.domain_production_proposal().code_targets == (
        "index.html",
        "verify/click-alert.mjs",
    )

    del payload["proposed_production"]["verification_expectation"]
    with pytest.raises(SteeringInvariantViolation, match="invalid structured result"):
        SemanticStepWireContract._parse_payload_ignoring_annotations(
            json.dumps(payload)
        )


@pytest.mark.parametrize(
    "disposition",
    (
        {
            "state": "RESOLVED",
            "authority_assessment": "UNCERTAIN",
            "unresolved_questions": ["Which exact bounded path is supported?"],
            "human_attention_recommendation": None,
            "completion_claimed": True,
        },
        {
            "state": "UNRESOLVED",
            "authority_assessment": "WITHIN_AUTHORITY",
            "unresolved_questions": ["Which option should govern this current step?"],
            "human_attention_recommendation": "Choose a bounded direction.",
            "completion_claimed": False,
        },
        {
            "state": "AUTHORITY_EXPANSION",
            "authority_assessment": "EXPANDS_AUTHORITY",
            "unresolved_questions": [],
            "human_attention_recommendation": "",
            "completion_claimed": False,
        },
    ),
)
def test_sem_wire_dogfood_7_cross_field_incoherence_is_not_representable(
    disposition: dict[str, object],
) -> None:
    payload = _payload()
    payload["disposition"] = disposition

    with pytest.raises(SteeringInvariantViolation, match="invalid structured result"):
        SemanticStepWireContract._parse_payload(json.dumps(payload))


def test_sem_wire_04_06_code_work_round_trip_preserves_typed_values() -> None:
    wire = SemanticStepWireContract._parse_payload(
        json.dumps(
            _payload(
                {
                    "target_kind": "CODE_WORK",
                    "objective": "Improve bounded progress observability",
                    "artifact_targets": [],
                    "code_targets": ["src/spg/web/app.js"],
                    "allowed_areas": ["src/spg/web/**"],
                    "forbidden_areas": [],
                    "verification_expectation": "Focused API and UI tests",
                }
            )
        )
    )

    proposal = wire.domain_production_proposal()
    assert type(proposal) is SemanticProductionProposal
    assert proposal.target_kind is ProductionTargetKind.CODE_WORK
    assert proposal.artifact_targets == ()
    assert proposal.code_targets == ("src/spg/web/app.js",)
    assert proposal.allowed_areas == ("src/spg/web/**",)
    assert proposal.forbidden_areas == ()


def test_sem_wire_04_06_documentation_round_trip_preserves_typed_values() -> None:
    wire = SemanticStepWireContract._parse_payload(
        json.dumps(
            _payload(
                {
                    "target_kind": "DOCUMENTATION_WORK",
                    "objective": "Record bounded progress observability",
                    "artifact_targets": [
                        {
                            "path": "docs/architecture/progress-observability.md",
                            "operation": "CREATE",
                        }
                    ],
                    "code_targets": [],
                    "allowed_areas": [],
                    "forbidden_areas": [],
                    "verification_expectation": "Artifact path verification",
                }
            )
        )
    )

    proposal = wire.domain_production_proposal()
    assert type(proposal) is SemanticProductionProposal
    assert proposal.target_kind is ProductionTargetKind.DOCUMENTATION_WORK
    assert proposal.artifact_targets[0].path == (
        "docs/architecture/progress-observability.md"
    )
    assert proposal.artifact_targets[0].operation is PlannedArtifactOperation.CREATE
    assert proposal.code_targets == ()
    assert proposal.allowed_areas == ()
    assert proposal.forbidden_areas == ()


@pytest.mark.parametrize(
    "proposal",
    (
        {
            "target_kind": "BOUNDED_CODE_CHANGE",
            "objective": "Invalid alias",
            "artifact_targets": [],
            "code_targets": ["src/spg/web/app.js"],
            "allowed_areas": [],
            "forbidden_areas": [],
            "verification_expectation": "Focused tests",
        },
        {
            "target_kind": "DOCUMENTATION_WORK",
            "objective": "Invalid artifact shape",
            "artifact_targets": ["docs/not-a-typed-target.md"],
            "code_targets": [],
            "allowed_areas": [],
            "forbidden_areas": [],
            "verification_expectation": "Focused tests",
        },
        {
            "target_kind": "CODE_WORK",
            "objective": "Invalid natural-language area",
            "artifact_targets": [],
            "code_targets": [],
            "allowed_areas": ["frontend files related to observability"],
            "forbidden_areas": [],
            "verification_expectation": "Focused tests",
        },
        {
            "target_kind": "CODE_WORK",
            "objective": "Invalid broad source and test roots",
            "artifact_targets": [],
            "code_targets": [],
            "allowed_areas": ["src/**", "tests/**"],
            "forbidden_areas": [],
            "verification_expectation": "Focused tests",
        },
        {
            "target_kind": "CODE_WORK",
            "objective": "Invalid repository escape",
            "artifact_targets": [],
            "code_targets": ["../outside.py"],
            "allowed_areas": [],
            "forbidden_areas": [],
            "verification_expectation": "Focused tests",
        },
    ),
)
def test_sem_wire_07_malformed_semantic_values_remain_rejected(
    proposal: dict[str, object],
) -> None:
    with pytest.raises(SteeringInvariantViolation, match="invalid structured result"):
        SemanticStepWireContract._parse_payload(
            json.dumps(_payload(proposal))
        )


@pytest.mark.parametrize(
    "missing_key",
    (
        "derived_constraints",
        "proposed_production",
        "disposition",
    ),
)
def test_sem_wire_03_04_absent_wire_keys_are_not_defaulted(
    missing_key: str,
) -> None:
    payload = _payload()
    payload.pop(missing_key)

    with pytest.raises(SteeringInvariantViolation, match="invalid structured result"):
        SemanticStepWireContract._parse_payload(json.dumps(payload))


def test_dogfood_8_broad_fallback_is_rejected_before_candidate_admission() -> None:
    proposal = {
        "target_kind": "CODE_WORK",
        "objective": "Improve execution progress observability",
        "artifact_targets": [],
        "code_targets": [],
        "allowed_areas": (
            "src/spg/api/**",
            "src/spg/web/**",
            "tests/js/**",
            "tests/**",
        ),
        "forbidden_areas": [],
        "verification_expectation": "Focused API and UI tests",
    }

    with pytest.raises(SteeringInvariantViolation, match="invalid structured result"):
        SemanticStepWireContract._parse_payload(
            json.dumps(_payload(proposal))
        )

    proposal["allowed_areas"] = ["src/spg/web/**", "tests/js/**"]
    parsed = SemanticStepWireContract._parse_payload(
        json.dumps(_payload(proposal))
    )
    assert parsed.domain_production_proposal().allowed_areas == (
        "src/spg/web/**",
        "tests/js/**",
    )


@pytest.mark.parametrize(
    "missing_key",
    ("artifact_targets", "code_targets", "allowed_areas", "forbidden_areas"),
)
def test_sem_wire_04_15_absent_proposal_collections_are_not_defaulted(
    missing_key: str,
) -> None:
    proposal = {
        "target_kind": "CODE_WORK",
        "objective": "Improve bounded progress observability",
        "artifact_targets": [],
        "code_targets": ["src/spg/web/app.js"],
        "allowed_areas": ["src/spg/web/**"],
        "forbidden_areas": [],
        "verification_expectation": "Focused API and UI tests",
    }
    proposal.pop(missing_key)

    with pytest.raises(SteeringInvariantViolation, match="invalid structured result"):
        SemanticStepWireContract._parse_payload(
            json.dumps(_payload(proposal))
        )


def test_resolved_issue_cannot_silently_claim_incomplete_without_a_question():
    payload = _payload()
    payload["disposition"]["completion_claimed"] = False
    with pytest.raises(SteeringInvariantViolation, match="invalid structured result"):
        SemanticStepWireContract._parse_payload(json.dumps(payload))


def test_human_attention_wire_requires_missing_authority_and_material_step_question():
    unresolved = _payload()
    unresolved["disposition"] = {
        "state": "UNRESOLVED",
        "authority_assessment": "UNCERTAIN",
        "unresolved_questions": [
            "Should all users receive administrator access or only accountable owners?"
        ],
        "human_attention_recommendation": "Choose the authorized access boundary.",
        "completion_claimed": False,
    }
    parsed = SemanticStepWireContract._parse_payload(json.dumps(unresolved))
    assert parsed.authority_assessment.value == "UNCERTAIN"
    assert parsed.unresolved_questions

    for authority, questions in (
        ("WITHIN_AUTHORITY", ["Which routine implementation should Watt choose?"]),
        ("UNCERTAIN", []),
    ):
        invalid = _payload()
        invalid["disposition"] = {
            "state": "UNRESOLVED",
            "authority_assessment": authority,
            "unresolved_questions": questions,
            "human_attention_recommendation": "Ask the Human.",
            "completion_claimed": False,
        }
        with pytest.raises(
            SteeringInvariantViolation,
            match="invalid structured result",
        ):
            SemanticStepWireContract._parse_payload(json.dumps(invalid))
