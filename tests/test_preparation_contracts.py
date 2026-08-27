from pydantic import ValidationError
import pytest

from spg.domain.preparation import (
    ContextArtifactSelection,
    ContextPackageRequest,
    ContextSemanticRole,
    ExecutorBinding,
    PreparedExecutionRequest,
)


def test_s2a_03_context_input_has_no_raw_conversation_path() -> None:
    with pytest.raises(ValidationError, match="conversation_text"):
        ContextPackageRequest.model_validate(
            {
                "artifacts": [
                    {
                        "semantic_role": "PROJECT_CONTEXT",
                        "repository_relative_path": "AI_context.md",
                    }
                ],
                "conversation_text": "raw chat must not become execution context",
            }
        )

    with pytest.raises(ValidationError):
        ContextArtifactSelection(
            semantic_role="RAW_CONVERSATION",
            repository_relative_path="conversation.txt",
        )


def test_s2a_context_paths_are_repository_relative() -> None:
    with pytest.raises(ValidationError, match="repository-relative"):
        ContextArtifactSelection(
            semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
            repository_relative_path="../outside.md",
        )


def test_s2a_06_executor_binding_and_request_are_provider_neutral() -> None:
    binding = ExecutorBinding(
        binding_ref="binding:documentation-default",
        capability_identity="capability:executor",
        profile_identity="profile:local-fvs",
    )

    assert binding.capability_identity == "capability:executor"
    assert set(ExecutorBinding.model_fields) == {
        "binding_ref",
        "capability_identity",
        "profile_identity",
    }
    assert not {
        "vendor",
        "model",
        "cli_flags",
        "prompt",
        "conversation",
    } & set(PreparedExecutionRequest.model_fields)
