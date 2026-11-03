"""Command-line interface of the dependency graph tool."""

import argparse
import sys
from typing import List, Optional

from . import constants as c
from .config import Config, load_config
from .errors import ConfigError, ToolError
from .repository import Repository, make_repository, root_package


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="python3 -m src",
        description="Visualize the dependency graph of a Maven package.",
    )
    parser.add_argument(
        "--config",
        default=c.DEFAULT_CONFIG,
        help="CSV file with the parameters (default: %(default)s)",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="only print the parameters as key: value (stage 1)",
    )
    return parser


def report_config_errors(error: ConfigError) -> int:
    """Print every configuration problem and return the exit code."""
    for problem in error.problems:
        print(f"error: {problem}", file=sys.stderr)
    return c.EXIT_USER_ERROR


def print_warnings(repository: Repository) -> None:
    """Print the non-fatal problems collected by the repository."""
    for warning in repository.take_warnings():
        print(f"warning: {warning}", file=sys.stderr)


def show_direct(config: Config, repository: Repository) -> None:
    """Print the direct dependencies of the requested package (stage 2)."""
    package = root_package(config)
    repository.check_root(package)
    found = repository.dependencies(package)
    print(f"Direct dependencies of {package.label}:")
    for item in found:
        print(f"  - {item.label}")
    if not found:
        print("  (none)")
    print_warnings(repository)


def run(config: Config, args: argparse.Namespace) -> None:
    """Perform the action selected on the command line."""
    if args.show_config:
        for name, value in config.as_pairs():
            print(f"{name}: {value}")
        return
    show_direct(config, make_repository(config))


def main(argv: Optional[List[str]] = None) -> int:
    """Run the tool and return the process exit code."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        return report_config_errors(error)
    try:
        run(config, args)
    except ToolError as error:
        print(f"error: {error}", file=sys.stderr)
        return c.EXIT_RUNTIME_ERROR
    return c.EXIT_OK
