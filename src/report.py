"""Text reports about a dependency graph."""

from typing import List

from . import constants as c
from .graph import Graph


def summary_lines(graph: Graph, max_depth: int) -> List[str]:
    """Return a short summary of the graph."""
    return [
        f"Packages: {len(graph.nodes)}, dependencies: {graph.edge_count()}, "
        f"cycles: {len(graph.cycles)}, depth limit: {max_depth}"
    ]


def note_lines(graph: Graph) -> List[str]:
    """Explain cycles and version conflicts found in the graph."""
    lines = []
    for cycle in graph.cycles:
        names = " -> ".join(graph.nodes[key].label for key in cycle)
        lines.append(f"cycle: {names}")
    for name, kept, ignored in graph.conflicts:
        lines.append(
            f"version conflict: {name} {kept} kept (nearest), "
            f"{ignored} ignored"
        )
    return lines


def legend_lines(tree: List[str]) -> List[str]:
    """Explain the marks used in the ASCII tree when they appear."""
    text = "\n".join(tree)
    lines = []
    if c.MARK_REPEAT in text:
        lines.append("(*) its dependencies are already shown above")
    if c.MARK_CYCLE in text:
        lines.append("(cycle) the package is its own ancestor")
    return lines
