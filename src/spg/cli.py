"""CLI-first control surface for the SPG project foundation."""

import argparse
from collections.abc import Sequence
import sys

from sqlalchemy.exc import SQLAlchemyError

from spg.application import bootstrap
from spg.infrastructure.persistence import DatabaseConfigurationError


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
    database = subcommands.add_parser(
        "db",
        help="perform non-destructive persistence operations",
    )
    database_commands = database.add_subparsers(dest="database_command", required=True)
    database_commands.add_parser(
        "check",
        help="check configured PostgreSQL connectivity",
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

    if arguments.command == "db" and arguments.database_command == "check":
        application = bootstrap()
        database = None
        try:
            database = application.persistence()
            health = database.check()
        except (DatabaseConfigurationError, SQLAlchemyError) as error:
            print(f"database check failed: {error}", file=sys.stderr)
            return 1
        finally:
            if database is not None:
                database.dispose()

        print("database=reachable")
        print("dialect=postgresql")
        print(f"database_name={health.database_name}")
        print(f"server_version_num={health.server_version_num}")
        return 0

    parser.error(f"unsupported command: {arguments.command}")
    return 2
