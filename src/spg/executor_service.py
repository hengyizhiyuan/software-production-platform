"""Command entrypoint for the dedicated local Executor boundary."""

import os
import sys

from spg.infrastructure.executor_boundary import (
    DedicatedExecutorRequest,
    execute_deterministic_request,
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
        else:
            raise ValueError(f"Unsupported dedicated Executor fixture binding: {binding or 'missing'}")
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 2
    print(response.model_dump_json(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
