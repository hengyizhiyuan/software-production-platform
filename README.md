# SPG Runtime

This repository contains the controlled implementation of the Software Production Governor Runtime.

The current implementation is limited to the FVS-1 / S1-A project foundation. Production governance lifecycle, persistence, Executor integration, repository integration, and Runtime Commit are not implemented.

## Local setup

The supported local workflow uses uv:

    uv sync --extra test

Run the CLI:

    uv run spg --help
    uv run spg status

Run tests:

    uv run pytest

