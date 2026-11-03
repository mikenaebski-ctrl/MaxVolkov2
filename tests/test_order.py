"""Tests for the dependency load order."""

import unittest
from typing import Dict, List

from src.graph import build_graph
from src.graph_file import TestRepository, parse_graph_text
from src.models import Package
from src.order import load_order
from tests.test_cli import run_cli
from tests.support import WorkspaceCase


def order_of(text: str, root: str = "A", depth: int = 10) -> List[str]:
    """Return the load order of a graph described by test repo text."""
    repo = TestRepository(parse_graph_text(text))
    graph = build_graph(repo, Package(root), depth)
    return load_order(graph)


def positions(order: List[str]) -> Dict[str, int]:
    """Map every package to its position in the order."""
    return {key: number for number, key in enumerate(order)}


class OrderTests(unittest.TestCase):
    """Dependencies must be loaded before the packages that need them."""

    TEXT = "A: B C\nB: D\nC: D E\nD: F\nE: F\nF:\n"

    def test_exact_order(self) -> None:
        """Post-order walk in declaration order."""
        self.assertEqual(order_of(self.TEXT), list("FDBECA"))

    def test_every_dependency_comes_first(self) -> None:
        """For each edge the target is loaded earlier than the source."""
        repo = TestRepository(parse_graph_text(self.TEXT))
        graph = build_graph(repo, Package("A"), 10)
        place = positions(load_order(graph))
        for source, targets in graph.edges.items():
            for target in targets:
                self.assertLess(place[target], place[source])

    def test_each_package_once(self) -> None:
        """A shared dependency is loaded only once."""
        order = order_of(self.TEXT)
        self.assertEqual(len(order), len(set(order)))

    def test_root_is_last(self) -> None:
        """The requested package is loaded after all its dependencies."""
        self.assertEqual(order_of(self.TEXT)[-1], "A")

    def test_leaf_root(self) -> None:
        """A package without dependencies is only itself."""
        self.assertEqual(order_of("A:\n"), ["A"])

    def test_cycle_edge_is_ignored(self) -> None:
        """The back edge of a cycle does not stop the ordering."""
        self.assertEqual(order_of("A: B\nB: C\nC: A\n"), ["C", "B", "A"])

    def test_self_dependency(self) -> None:
        """A package that needs itself is listed once."""
        self.assertEqual(order_of("A: A B\nB:\n"), ["B", "A"])

    def test_depth_limit(self) -> None:
        """Only packages inside the depth limit are ordered."""
        self.assertEqual(order_of(self.TEXT, depth=1), list("BCA"))


class OrderCommandTests(WorkspaceCase):
    """The --load-order command line option."""

    def test_output_format(self) -> None:
        """The order is printed as a numbered list."""
        path = self.write_config()
        code, out, _ = run_cli(["--load-order", "--config", path])
        self.assertEqual(code, 0)
        self.assertEqual(
            out.splitlines(),
            [
                "Load order (dependencies first):",
                "  1. D",
                "  2. B",
                "  3. C",
                "  4. A",
            ],
        )

    def test_cycle_is_explained(self) -> None:
        """A cycle is named below the list."""
        self.write_repo("A: B\nB: A\n")
        path = self.write_config()
        _, out, _ = run_cli(["--load-order", "--config", path])
        self.assertIn("cycle: A -> B -> A", out)

    def test_unknown_package(self) -> None:
        """A missing root is a clean error."""
        path = self.write_config(package_name="Z")
        code, out, _ = run_cli(["--load-order", "--config", path])
        self.assertEqual((code, out), (1, ""))


if __name__ == "__main__":
    unittest.main()
