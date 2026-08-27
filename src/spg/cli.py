"""CLI-first control surface for the SPG project foundation."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from spg.application import bootstrap
from spg.domain.runtime import (
    BootstrapRequest,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
    RuntimeDomainError,
)
from spg.infrastructure.persistence import DatabaseConfigurationError


def build_parser() -> argparse.ArgumentParser:
    """Build the bounded project-foundation and S1-C inspection surface."""

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
    bootstrap_command = subcommands.add_parser(
        "bootstrap",
        help="explicitly admit the initial Trusted Baseline",
    )
    bootstrap_command.add_argument("--repository-path", type=Path, required=True)
    bootstrap_command.add_argument("--repository-identity", required=True)
    bootstrap_command.add_argument("--repository-ref", required=True)
    bootstrap_command.add_argument("--authority-identity", required=True)
    bootstrap_command.add_argument("--rationale")

    baseline = subcommands.add_parser("baseline", help="inspect baseline state")
    baseline_commands = baseline.add_subparsers(
        dest="baseline_command",
        required=True,
    )
    baseline_commands.add_parser("show", help="show the Current Trusted Baseline")

    run = subcommands.add_parser("run", help="construct or inspect a Production Run")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    run_create = run_commands.add_parser(
        "create",
        help="construct Run, Plan Revision 1, and proposed PWU",
    )
    run_create.add_argument("--intent-ref", required=True)
    run_create.add_argument("--goal", required=True)
    run_create.add_argument(
        "--horizon",
        required=True,
        choices=[horizon.value for horizon in ProductionHorizon],
    )
    run_create.add_argument("--pwu-objective", required=True)
    run_create.add_argument(
        "--completion-contract",
        type=Path,
        required=True,
        help="path to a structured Completion Contract JSON document",
    )
    run_inspect = run_commands.add_parser("inspect", help="inspect one Runtime spine")
    run_inspect.add_argument("run_id", type=UUID)
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

    if arguments.command in {"bootstrap", "baseline", "run"}:
        application = bootstrap()
        database = None
        try:
            database = application.persistence()
            runtime = application.runtime(database)
            if arguments.command == "bootstrap":
                result = runtime.bootstrap_trusted_baseline(
                    BootstrapRequest(
                        repository_path=arguments.repository_path,
                        repository_identity=arguments.repository_identity,
                        repository_ref=arguments.repository_ref,
                        authority_identity=arguments.authority_identity,
                        rationale=arguments.rationale,
                    )
                )
                _print_json(result)
                return 0
            if arguments.command == "baseline":
                _print_json(runtime.current_baseline())
                return 0
            if arguments.run_command == "create":
                completion_contract = CompletionContract.model_validate_json(
                    arguments.completion_contract.read_text(encoding="utf-8")
                )
                result = runtime.create_initial_runtime_spine(
                    InitialRunRequest(
                        intent_ref=arguments.intent_ref,
                        goal=arguments.goal,
                        production_horizon=arguments.horizon,
                        initial_work_unit_objective=arguments.pwu_objective,
                        completion_contract=completion_contract,
                    )
                )
                _print_json(result)
                return 0
            if arguments.run_command == "inspect":
                _print_json(runtime.inspect_run(arguments.run_id))
                return 0
        except (
            DatabaseConfigurationError,
            RuntimeDomainError,
            SQLAlchemyError,
            ValidationError,
            OSError,
            json.JSONDecodeError,
        ) as error:
            print(f"runtime operation failed: {error}", file=sys.stderr)
            return 1
        finally:
            if database is not None:
                database.dispose()

    parser.error(f"unsupported command: {arguments.command}")
    return 2


def _print_json(value) -> None:
    print(value.model_dump_json(indent=2))
