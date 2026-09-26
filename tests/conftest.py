"""Legacy service/API tests explicitly exercise the pre-authenticated test seam.

The production default remains fail-closed.  Authentication and ownership
have their own required-mode integration tests.
"""

import pytest


@pytest.fixture(autouse=True)
def _legacy_test_auth_mode(monkeypatch):
    monkeypatch.setenv("SPG_AUTH_MODE", "test-only-disabled")
