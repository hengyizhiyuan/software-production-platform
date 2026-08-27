"""Allow the CLI to run with python -m spg."""

from spg.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

