"""A test repository described by a plain text graph file."""

import re
from pathlib import Path
from typing import Dict, List

from . import constants as c
from .errors import PackageNotFoundError, RepositoryError
from .models import Package
from .repository import Repository


def parse_graph_text(text: str) -> Dict[str, List[str]]:
    """Parse lines such as 'A: B C' into an adjacency dictionary."""
    graph: Dict[str, List[str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(c.TEST_REPO_LINE, line)
        if not match:
            raise RepositoryError(
                f"test repository line {number}: expected 'A: B C', "
                f"got '{line}'"
            )
        name, rest = match.group(1), match.group(2).split()
        if name in graph:
            raise RepositoryError(
                f"test repository line {number}: '{name}' is described twice"
            )
        graph[name] = rest
    return graph


class TestRepository(Repository):
    """Packages named by capital letters with dependencies from a file."""

    __test__ = False

    def __init__(self, graph: Dict[str, List[str]]) -> None:
        """Remember the adjacency dictionary."""
        self.graph = graph
        self.known = set(graph)
        for names in graph.values():
            self.known.update(names)

    @classmethod
    def from_file(cls, path: str) -> "TestRepository":
        """Read a test repository from a text file."""
        try:
            text = Path(path).read_text(encoding=c.ENCODING)
        except (OSError, UnicodeDecodeError) as error:
            raise RepositoryError(f"cannot read {path}: {error}")
        return cls(parse_graph_text(text))

    def check_root(self, package: Package) -> None:
        """Raise an error if the package is not mentioned in the file."""
        if package.name not in self.known:
            raise PackageNotFoundError(
                f"package '{package.name}' is not in the test repository"
            )

    def dependencies(self, package: Package) -> List[Package]:
        """Return the dependencies listed for the package."""
        return [Package(name) for name in self.graph.get(package.name, [])]
