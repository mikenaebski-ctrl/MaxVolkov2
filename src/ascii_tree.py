"""Draw a dependency graph as an ASCII tree."""

from typing import List, Set, Tuple

from . import constants as c
from .graph import Graph


def child_entries(
    graph: Graph, key: str, prefix: str, ancestors: Tuple[str, ...]
) -> List[Tuple[str, str, bool, Tuple[str, ...]]]:
    """Build stack entries for the children of a node (last first)."""
    keys = graph.children(key)
    last_index = len(keys) - 1
    entries = [
        (child, prefix, index == last_index, ancestors)
        for index, child in enumerate(keys)
    ]
    return list(reversed(entries))


def tree_lines(graph: Graph) -> List[str]:
    """Return the lines of the tree.

    A package that closes a cycle gets " (cycle)". A package whose
    dependencies were already printed gets " (*)" and is not expanded.
    """
    lines = [graph.root.label]
    shown: Set[str] = {graph.root.key}
    root_key = graph.root.key
    stack = child_entries(graph, root_key, "", (root_key,))
    while stack:
        key, prefix, is_last, ancestors = stack.pop()
        branch = c.BRANCH_LAST if is_last else c.BRANCH_MIDDLE
        text = prefix + branch + graph.nodes[key].label
        if key in ancestors:
            lines.append(text + c.MARK_CYCLE)
        elif key in shown and graph.children(key):
            lines.append(text + c.MARK_REPEAT)
        else:
            lines.append(text)
            shown.add(key)
            indent = c.INDENT_BLANK if is_last else c.INDENT_BAR
            stack.extend(
                child_entries(graph, key, prefix + indent, ancestors + (key,))
            )
    return lines
