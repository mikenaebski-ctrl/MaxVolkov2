"""Tests for the ASCII tree and the text reports."""

import unittest

from src.ascii_tree import tree_lines
from src.graph import build_graph
from src.graph_file import TestRepository, parse_graph_text
from src.models import Package
from src.report import legend_lines, note_lines, summary_lines


def graph_of(text: str, depth: int = 10):
    """Build a graph with root A from test repository text."""
    repo = TestRepository(parse_graph_text(text))
    return build_graph(repo, Package("A"), depth)


class TreeTests(unittest.TestCase):
    """The exact shape of the drawn tree."""

    def test_single_node(self) -> None:
        """Only the root is printed for a leaf package."""
        self.assertEqual(tree_lines(graph_of("A:\n")), ["A"])

    def test_branches_and_repeats(self) -> None:
        """Middle and last branches, bars, and (*) for repeats."""
        graph = graph_of("A: B C\nB: D\nC: D E\nD: F\nE:\nF:\n")
        self.assertEqual(
            tree_lines(graph),
            [
                "A",
                "├── B",
                "│   └── D",
                "│       └── F",
                "└── C",
                "    ├── D (*)",
                "    └── E",
            ],
        )

    def test_repeated_leaf_has_no_mark(self) -> None:
        """A leaf shown twice is not marked because nothing is hidden."""
        lines = tree_lines(graph_of("A: B C\nB: D\nC: D\nD:\n"))
        self.assertEqual(lines[-1], "    └── D")

    def test_cycle_mark(self) -> None:
        """A package that is its own ancestor is marked, not expanded."""
        lines = tree_lines(graph_of("A: B\nB: A\n"))
        self.assertEqual(lines, ["A", "└── B", "    └── A (cycle)"])

    def test_depth_limit_in_tree(self) -> None:
        """The tree stops at the depth limit."""
        lines = tree_lines(graph_of("A: B\nB: C\nC: D\nD:\n", depth=2))
        self.assertEqual(lines, ["A", "└── B", "    └── C"])


class ReportTests(unittest.TestCase):
    """Summary, notes and the legend."""

    def test_summary(self) -> None:
        """The summary counts packages, edges and cycles."""
        graph = graph_of("A: B\nB: A\n")
        self.assertEqual(
            summary_lines(graph, 10),
            ["Packages: 2, dependencies: 2, cycles: 1, depth limit: 10"],
        )

    def test_cycle_note(self) -> None:
        """A cycle is explained with an arrow chain."""
        self.assertEqual(
            note_lines(graph_of("A: B\nB: A\n")), ["cycle: A -> B -> A"]
        )

    def test_legend_only_for_used_marks(self) -> None:
        """Marks that do not appear are not explained."""
        self.assertEqual(legend_lines(["A", "└── B"]), [])
        self.assertEqual(len(legend_lines(["A (*)", "B (cycle)"])), 2)


if __name__ == "__main__":
    unittest.main()
