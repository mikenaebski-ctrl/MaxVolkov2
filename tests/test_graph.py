"""Tests for the breadth-first graph builder."""

import unittest
from typing import List

from src.ascii_tree import tree_lines
from src.errors import PackageNotFoundError, RepositoryError
from src.graph import build_graph
from src.graph_file import TestRepository, parse_graph_text
from src.maven_repo import MavenRepository
from src.models import Package
from src.repository import Repository
from tests.maven_support import MavenRepoCase


def graph_of(text: str, root: str, depth: int):
    """Build a graph from test repository text."""
    repo = TestRepository(parse_graph_text(text))
    return build_graph(repo, Package(root), depth)


class BreadthFirstTests(unittest.TestCase):
    """Order, depth limit and shared dependencies."""

    TEXT = "A: B C\nB: D\nC: D E\nD: F\nE: F\nF:\n"

    def test_discovery_order_is_breadth_first(self) -> None:
        """Nodes are found level by level."""
        graph = graph_of(self.TEXT, "A", 10)
        self.assertEqual(list(graph.nodes), ["A", "B", "C", "D", "E", "F"])
        self.assertEqual(
            [graph.depths[key] for key in graph.nodes], [0, 1, 1, 2, 2, 3]
        )

    def test_edges_keep_declaration_order(self) -> None:
        """Shared dependencies get one node and several edges."""
        graph = graph_of(self.TEXT, "A", 10)
        self.assertEqual(graph.edges["C"], ["D", "E"])
        self.assertEqual(graph.edge_count(), 7)

    def test_depth_limit(self) -> None:
        """Packages deeper than the limit are not visited."""
        for depth, expected in ((1, "ABC"), (2, "ABCDE"), (3, "ABCDEF")):
            with self.subTest(depth=depth):
                graph = graph_of(self.TEXT, "A", depth)
                self.assertEqual("".join(graph.nodes), expected)

    def test_limit_does_not_read_last_level(self) -> None:
        """Nodes on the last level are shown without their edges."""
        graph = graph_of(self.TEXT, "A", 1)
        self.assertNotIn("B", graph.edges)
        self.assertEqual(graph.edges["A"], ["B", "C"])

    def test_leaf_root(self) -> None:
        """A root without dependencies is a graph with one node."""
        graph = graph_of("A:\n", "A", 3)
        self.assertEqual(list(graph.nodes), ["A"])
        self.assertEqual(graph.cycles, [])


class CycleTests(unittest.TestCase):
    """Cyclic dependencies must not loop forever."""

    def test_simple_cycle(self) -> None:
        """A -> B -> C -> A is reported once."""
        graph = graph_of("A: B\nB: C\nC: A D\nD:\n", "A", 10)
        self.assertEqual(graph.cycles, [["A", "B", "C", "A"]])
        self.assertEqual(len(graph.nodes), 4)

    def test_self_dependency(self) -> None:
        """A package that needs itself is a one-element cycle."""
        graph = graph_of("A: A B\nB: A\n", "A", 10)
        self.assertIn(["A", "A"], graph.cycles)
        self.assertIn(["A", "B", "A"], graph.cycles)

    def test_cycle_not_through_the_root(self) -> None:
        """A cycle deeper in the graph is found too."""
        graph = graph_of("A: B\nB: C\nC: B\n", "A", 10)
        self.assertEqual(graph.cycles, [["B", "C", "B"]])

    def test_cycle_cut_by_depth(self) -> None:
        """The closing edge is not seen when the limit stops first."""
        graph = graph_of("A: B\nB: C\nC: A\n", "A", 2)
        self.assertEqual(graph.cycles, [])

    def test_diamond_is_not_a_cycle(self) -> None:
        """Two paths to one package are not a cycle."""
        graph = graph_of("A: B C\nB: D\nC: D\nD:\n", "A", 10)
        self.assertEqual(graph.cycles, [])


class ChainRepository(Repository):
    """A very long chain P0 -> P1 -> ... without recursion limits."""

    def __init__(self, length: int) -> None:
        """Remember the chain length."""
        self.length = length

    def check_root(self, package: Package) -> None:
        """Every package exists."""

    def dependencies(self, package: Package) -> List[Package]:
        """Return the next package in the chain."""
        number = int(package.name[1:])
        if number >= self.length:
            return []
        return [Package(f"P{number + 1}")]


class NoRecursionTests(unittest.TestCase):
    """The algorithms must work on graphs deeper than the stack limit."""

    def test_very_deep_graph(self) -> None:
        """A chain of 5000 packages does not raise RecursionError."""
        length = 5000
        graph = build_graph(ChainRepository(length), Package("P0"), length)
        self.assertEqual(len(graph.nodes), length + 1)
        self.assertEqual(len(tree_lines(graph)), length + 1)


class ErrorHandlingTests(MavenRepoCase):
    """Failures of unreadable packages."""

    def test_unknown_root_fails_in_the_repository(self) -> None:
        """The caller checks the root before building the graph."""
        repo = TestRepository(parse_graph_text("A: B\n"))
        with self.assertRaises(PackageNotFoundError):
            repo.check_root(Package("Z"))

    def test_missing_transitive_pom_is_a_warning(self) -> None:
        """An unreadable POM below the root is skipped with a warning."""
        self.add_simple("org.x", "lib", "1.0", [("g", "gone", "1")])
        repo = MavenRepository(self.repo_url)
        graph = build_graph(repo, Package("org.x:lib", "1.0"), 3)
        self.assertEqual(list(graph.nodes), ["org.x:lib", "g:gone"])
        self.assertIn("g:gone:1", graph.warnings[0])

    def test_root_failure_is_raised(self) -> None:
        """A failure for the root itself is not hidden."""
        repo = MavenRepository(self.repo_url)
        with self.assertRaises(RepositoryError):
            build_graph(repo, Package("org.x:lib", "1.0"), 3)

    def test_nearest_version_wins(self) -> None:
        """The first version found by BFS is kept, the other is noted."""
        self.add_simple("org.x", "lib", "1.0",
                        [("g", "mid", "1"), ("g", "util", "2")])
        self.add_simple("g", "mid", "1", [("g", "util", "1")])
        self.add_simple("g", "util", "1")
        self.add_simple("g", "util", "2")
        repo = MavenRepository(self.repo_url)
        graph = build_graph(repo, Package("org.x:lib", "1.0"), 5)
        self.assertEqual(graph.nodes["g:util"].version, "2")
        self.assertEqual(graph.conflicts, [("g:util", "2", "1")])
        self.assertEqual(graph.edges["g:mid"], ["g:util"])


if __name__ == "__main__":
    unittest.main()
