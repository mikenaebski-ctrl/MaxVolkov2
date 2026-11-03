"""Compute the order in which dependencies have to be loaded."""

from typing import Dict, List

from . import constants as c
from .graph import Graph


def load_order(graph: Graph) -> List[str]:
    """Return package keys so that dependencies come before dependents.

    This is an iterative post-order depth-first walk that follows the
    dependencies in declaration order. An edge that leads back to a
    package still being visited closes a cycle and is ignored.
    """
    root = graph.root.key
    state: Dict[str, str] = {root: c.STATE_ACTIVE}
    order: List[str] = []
    stack = [(root, iter(graph.children(root)))]
    while stack:
        key, remaining = stack[-1]
        child = next(remaining, None)
        if child is None:
            state[key] = c.STATE_DONE
            order.append(key)
            stack.pop()
        elif child not in state:
            state[child] = c.STATE_ACTIVE
            stack.append((child, iter(graph.children(child))))
    return order
