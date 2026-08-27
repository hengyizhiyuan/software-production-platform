"""CLI-first control surface for the SPG project foundation."""

import argparse
from collections.abc import Sequence

from spg.application import bootstrap


def build_parser() -> argparse.ArgumentParser:
    """Build the small S1-A command surface."""

    parser = argparse.ArgumentParser(
        prog="spg",
        description="Software Production Governor runtime foundation",
    )
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser(
        "status",
        help="show harmless project-foundation metadata",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one controlled CLI command."""

    parser = build_parser()
    arguments = parser.parse_args(argv)

    if arguments.command is None:
        parser.print_help()
        return 0

    if arguments.command == "status":
        application = bootstrap()
        for key, value in application.status().items():
            print(f"{key}={value}")
        return 0

    parser.error(f"unsupported command: {arguments.command}")
    return 2

