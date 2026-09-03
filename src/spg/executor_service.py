"""Command entrypoint for the dedicated local Executor boundary."""

import os
import sys

from spg.infrastructure.executor_boundary import (
    DedicatedExecutorRequest,
    MAX_PROVIDER_TIMEOUT_SECONDS,
    execute_deterministic_request,
)
from spg.infrastructure.codex_executor_binding import (
    CODEX_BINDING,
    CODEX_REAL_BINDING,
    execute_codex_binding,
    preflight_codex_binding,
    unsupported_provider_binding,
)
from spg.providers.deterministic_executor import DeterministicExecutionSpecification


def main() -> int:
    try:
        request = DedicatedExecutorRequest.model_validate_json(sys.stdin.read())
        binding = os.environ.get("SPG_EXECUTOR_PROVIDER_BINDING", "")
        if binding == "deterministic-fixture":
            specification = DeterministicExecutionSpecification.model_validate_json(
                os.environ["SPG_EXECUTOR_DETERMINISTIC_SPEC"]
            )
            response = execute_deterministic_request(request, specification)
        elif binding == CODEX_BINDING:
            response = preflight_codex_binding(request, environment=os.environ)
        elif binding == CODEX_REAL_BINDING:
            response = execute_codex_binding(
                request,
                environment=os.environ,
                timeout_seconds=_provider_timeout_seconds(),
            )
        else:
            response = unsupported_provider_binding(request, binding or "missing")
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 2
    print(response.model_dump_json(), flush=True)
    return 0


def _provider_timeout_seconds() -> float:
    raw = os.environ.get("SPG_EXECUTOR_PROVIDER_TIMEOUT_SECONDS")
    if raw is None:
        return 120.0
    value = float(raw)
    if not 0 < value <= MAX_PROVIDER_TIMEOUT_SECONDS:
        raise ValueError("Executor Provider timeout must be within (0, 600]")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
