"""Command-line interface of the dependency graph tool."""

import argparse
import sys
from typing import List, Optional

from . import constants as c
from .config import load_config
from .errors import ConfigError


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
    return parser


def report_config_errors(error: ConfigError) -> int:
    """Print every configuration problem and return the exit code."""
    for problem in error.problems:
        print(f"error: {problem}", file=sys.stderr)
    return c.EXIT_USER_ERROR


def main(argv: Optional[List[str]] = None) -> int:
    """Run the tool and return the process exit code."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        return report_config_errors(error)
    for name, value in config.as_pairs():
        print(f"{name}: {value}")
    return c.EXIT_OK
