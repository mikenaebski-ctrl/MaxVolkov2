"""Build the dependency graph with a breadth-first search."""

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple

from . import constants as c
from .errors import RepositoryError
from .models import Package
from .repository import Repository


@dataclass
class Graph:
    """A dependency graph; nodes are stored in discovery (BFS) order."""

    root: Package
    nodes: Dict[str, Package] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=dict)
    depths: Dict[str, int] = field(default_factory=dict)
    cycles: List[List[str]] = field(default_factory=list)
    conflicts: List[Tuple[str, str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_node(self, package: Package, depth: int) -> None:
        """Register a package found at the given depth."""
        self.nodes[package.key] = package
        self.depths[package.key] = depth

    def children(self, key: str) -> List[str]:
        """Return the keys of the direct dependencies of a node."""
        return self.edges.get(key, [])

    def edge_count(self) -> int:
        """Count all dependency edges."""
        return sum(len(targets) for targets in self.edges.values())


def read_children(
    repository: Repository, package: Package, graph: Graph
) -> List[Package]:
    """Read dependencies; a failure below the root only gives a warning."""
    if package.key == graph.root.key:
        return repository.dependencies(package)
    try:
        return repository.dependencies(package)
    except RepositoryError as error:
        graph.warnings.append(
            f"cannot read dependencies of {package.label}: {error}"
        )
        return []


def connect(
    graph: Graph, parent: Package, children: List[Package],
    queue: Deque[str],
) -> None:
    """Add edges from a parent and queue the packages seen first."""
    targets = graph.edges.setdefault(parent.key, [])
    depth = graph.depths[parent.key] + 1
    for child in children:
        known = graph.nodes.get(child.key)
        if known is None:
            graph.add_node(child, depth)
            queue.append(child.key)
        elif known.version != child.version:
            graph.conflicts.append((child.name, known.version, child.version))
        if child.key not in targets:
            targets.append(child.key)


def build_graph(
    repository: Repository, root: Package, max_depth: int
) -> Graph:
    """Collect transitive dependencies up to max_depth levels (BFS)."""
    graph = Graph(root)
    graph.add_node(root, 0)
    queue: Deque[str] = deque([root.key])
    while queue:
        package = graph.nodes[queue.popleft()]
        if graph.depths[package.key] >= max_depth:
            continue
        children = read_children(repository, package, graph)
        connect(graph, package, children, queue)
    graph.cycles = find_cycles(graph)
    graph.warnings.extend(repository.take_warnings())
    return graph


def find_cycles(graph: Graph) -> List[List[str]]:
    """Find cycles with an iterative depth-first search."""
    state: Dict[str, str] = {graph.root.key: c.STATE_ACTIVE}
    path = [graph.root.key]
    stack = [(graph.root.key, iter(graph.children(graph.root.key)))]
    cycles: List[List[str]] = []
    while stack:
        key, remaining = stack[-1]
        child = next(remaining, None)
        if child is None:
            state[key] = c.STATE_DONE
            path.pop()
            stack.pop()
        elif state.get(child) == c.STATE_ACTIVE:
            cycles.append(path[path.index(child):] + [child])
        elif child not in state:
            state[child] = c.STATE_ACTIVE
            path.append(child)
            stack.append((child, iter(graph.children(child))))
    return cycles

