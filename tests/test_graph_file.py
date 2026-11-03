"""Tests for the test repository described by a text file."""

from src.errors import PackageNotFoundError, RepositoryError
from src.graph_file import TestRepository, parse_graph_text
from src.models import Package
from tests.support import WorkspaceCase


class ParseGraphTextTests(WorkspaceCase):
    """The file format is 'NAME: DEP DEP'."""

    def test_parses_lines_comments_and_blanks(self) -> None:
        """Comments and blank lines are ignored."""
        text = "# comment\n\nA: B C\nB:\nC :  D\n"
        self.assertEqual(
            parse_graph_text(text), {"A": ["B", "C"], "B": [], "C": ["D"]}
        )

    def test_rejects_bad_lines(self) -> None:
        """Lowercase names and missing colons are reported."""
        for text in ("a: B", "A B", "A: b", "A: B;C"):
            with self.subTest(text=text):
                with self.assertRaises(RepositoryError) as caught:
                    parse_graph_text(text)
                self.assertIn("line 1", str(caught.exception))

    def test_rejects_duplicate_packages(self) -> None:
        """A package may be described only once."""
        with self.assertRaises(RepositoryError) as caught:
            parse_graph_text("A: B\nA: C")
        self.assertIn("described twice", str(caught.exception))


class TestRepositoryTests(WorkspaceCase):
    """Dependencies come from the parsed dictionary."""

    def test_dependencies_in_file_order(self) -> None:
        """Direct dependencies keep the order of the file."""
        repo = TestRepository.from_file(str(self.repo_file))
        names = [p.name for p in repo.dependencies(Package("A"))]
        self.assertEqual(names, ["B", "C"])
        self.assertEqual(repo.dependencies(Package("D")), [])

    def test_unknown_root_is_an_error(self) -> None:
        """A root that appears nowhere in the file is not found."""
        repo = TestRepository.from_file(str(self.repo_file))
        repo.check_root(Package("D"))
        with self.assertRaises(PackageNotFoundError):
            repo.check_root(Package("Z"))

    def test_unreadable_file(self) -> None:
        """A missing file is a repository error."""
        with self.assertRaises(RepositoryError):
            TestRepository.from_file(str(self.root / "none.txt"))
