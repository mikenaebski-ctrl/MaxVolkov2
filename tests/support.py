"""Helpers shared by the tests."""

import tempfile
import unittest
from pathlib import Path
from typing import Dict

REPO_TEXT = "A: B C\nB: D\nC: D\nD:\n"
DEFAULTS = {
    "package_name": "A",
    "repository_mode": "test",
    "package_version": "1.0",
    "output_image": "graph.png",
    "ascii_tree": "true",
    "max_depth": "3",
}


class WorkspaceCase(unittest.TestCase):
    """A test case with a temporary directory and a test repository."""

    def setUp(self) -> None:
        """Create the temporary directory and the repository file."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo_file = self.root / "repo.txt"
        self.repo_file.write_text(REPO_TEXT, encoding="utf-8")

    def write_repo(self, text: str) -> str:
        """Store a test repository description and return its path."""
        self.repo_file.write_text(text, encoding="utf-8")
        return str(self.repo_file)

    def config_text(self, **overrides: str) -> str:
        """Build CSV text; a value of None removes the parameter."""
        values: Dict[str, str] = dict(DEFAULTS)
        values["repository_url"] = str(self.repo_file)
        values.update(overrides)
        lines = ["parameter,value"]
        for name, value in values.items():
            if value is not None:
                lines.append(f"{name},{value}")
        return "\n".join(lines) + "\n"

    def write_config(self, **overrides: str) -> str:
        """Write a configuration file and return its path."""
        path = self.root / "config.csv"
        path.write_text(self.config_text(**overrides), encoding="utf-8")
        return str(path)
