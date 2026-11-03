"""Command-line interface of the dependency graph tool."""

import argparse
import sys
from typing import List, Optional

from . import constants as c
from .ascii_tree import tree_lines
from .config import Config, load_config
from .errors import ConfigError, ToolError
from .graph import Graph, build_graph
from .order import load_order
from .report import (
    legend_lines, note_lines, order_lines, summary_lines
)
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
    parser.add_argument(
        "--direct",
        action="store_true",
        help="only print the direct dependencies (stage 2)",
    )
    parser.add_argument(
        "--load-order",
        action="store_true",
        help="only print the order of loading the dependencies (stage 4)",
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


def print_lines(lines: List[str]) -> None:
    """Print each line on its own row."""
    for line in lines:
        print(line)


def make_graph(config: Config, repository: Repository) -> Graph:
    """Check the root package and build the dependency graph."""
    package = root_package(config)
    repository.check_root(package)
    return build_graph(repository, package, config.max_depth)


def print_graph_warnings(graph: Graph) -> None:
    """Print the non-fatal problems met while building the graph."""
    for warning in graph.warnings:
        print(f"warning: {warning}", file=sys.stderr)


def show_graph(config: Config, repository: Repository) -> None:
    """Build the whole graph and print it (stage 3)."""
    graph = make_graph(config, repository)
    if config.ascii_tree:
        tree = tree_lines(graph)
        print_lines(tree)
        print_lines(legend_lines(tree))
    print_lines(summary_lines(graph, config.max_depth))
    print_lines(note_lines(graph))
    print_graph_warnings(graph)


def show_order(config: Config, repository: Repository) -> None:
    """Build the graph and print the dependency load order (stage 4)."""
    graph = make_graph(config, repository)
    print_lines(order_lines(graph, load_order(graph)))
    print_lines(note_lines(graph))
    print_graph_warnings(graph)


def run(config: Config, args: argparse.Namespace) -> None:
    """Perform the action selected on the command line."""
    if args.show_config:
        for name, value in config.as_pairs():
            print(f"{name}: {value}")
        return
    repository = make_repository(config)
    if args.direct:
        show_direct(config, repository)
    elif args.load_order:
        show_order(config, repository)
    else:
        show_graph(config, repository)


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
