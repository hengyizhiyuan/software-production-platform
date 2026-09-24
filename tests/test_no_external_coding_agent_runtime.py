"""Permanent guard against restoring an external coding-agent runtime."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from spg.config import Settings


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_FILES = (
    ROOT / "pyproject.toml",
    ROOT / "uv.lock",
    ROOT / "Dockerfile",
    ROOT / ".env.example",
    ROOT / "compose.yaml",
    ROOT / "compose.native-executor.yaml",
    ROOT / "compose.e2e.yaml",
    ROOT / "compose.delivery.yaml",
    ROOT / "README.md",
)


def test_external_coding_agent_sdk_is_absent_from_runtime_and_deployment() -> None:
    sources = tuple((ROOT / "src" / "spg").rglob("*.py"))
    for path in (*ACTIVE_FILES, *sources):
        text = path.read_text(encoding="utf-8").lower()
        assert "openai-codex" not in text, path
        assert "codex-sdk" not in text, path
        assert "codex_executor" not in text, path
        assert "codex-executor" not in text, path
        assert "codex_home" not in text, path
        assert "codex_auth" not in text, path
    assert not tuple((ROOT / "src" / "spg").rglob("*codex*.py"))


@pytest.mark.parametrize(
    "option",
    (
        {"executor_adapter": "codex-sdk"},
        {"native_executor_backend": "codex-sdk"},
        {"wic_provider_adapter": "codex-sdk"},
        {"conversation_provider_adapter": "codex-sdk"},
    ),
)
def test_runtime_configuration_rejects_external_coding_agent(option: dict) -> None:
    with pytest.raises(ValidationError):
        Settings(**option)
