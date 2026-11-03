"""Tests for the command-line interface."""

import contextlib
import io
from typing import List, Tuple

from src.cli import main
from tests.maven_support import MavenRepoCase
from tests.support import WorkspaceCase


def run_cli(args: List[str]) -> Tuple[int, str, str]:
    """Run main() and capture its exit code and output streams."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(args)
        except SystemExit as exit_request:
            code = int(exit_request.code)
    return code, out.getvalue(), err.getvalue()


class ParameterOutputTests(WorkspaceCase):
    """The stage 1 behaviour: print all parameters as key: value."""

    def test_prints_every_parameter(self) -> None:
        """All seven parameters are printed in key: value form."""
        path = self.write_config()
        code, out, _ = run_cli(["--show-config", "--config", path])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertIn("package_name: A", lines)
        self.assertIn("repository_mode: test", lines)
        self.assertIn("max_depth: 3", lines)

    def test_invalid_config_reports_errors(self) -> None:
        """Problems go to stderr and the exit code is 2."""
        path = self.write_config(max_depth="0", ascii_tree="x")
        code, out, err = run_cli(["--config", path])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(len(err.splitlines()), 2)
        self.assertTrue(err.startswith("error: "))

    def test_missing_config_file(self) -> None:
        """A missing file does not crash the program."""
        code, _, err = run_cli(["--config", str(self.root / "no.csv")])
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_unknown_option(self) -> None:
        """argparse rejects unknown command-line options."""
        code, _, err = run_cli(["--bogus"])
        self.assertEqual(code, 2)
        self.assertIn("unrecognized arguments", err)


class DirectDependencyOutputTests(MavenRepoCase):
    """The stage 2 behaviour: print the direct dependencies."""

    def test_test_repository(self) -> None:
        """Direct dependencies of A come from the test file."""
        code, out, _ = run_cli(["--config", self.write_config()])
        self.assertEqual(code, 0)
        self.assertEqual(
            out.splitlines(),
            ["Direct dependencies of A:", "  - B", "  - C"],
        )

    def test_leaf_package_has_no_dependencies(self) -> None:
        """A leaf prints (none)."""
        path = self.write_config(package_name="D")
        _, out, _ = run_cli(["--config", path])
        self.assertIn("(none)", out)

    def test_unknown_package_is_an_error(self) -> None:
        """A package missing from the test repository exits with 1."""
        path = self.write_config(package_name="Z")
        code, out, err = run_cli(["--config", path])
        self.assertEqual((code, out), (1, ""))
        self.assertIn("not in the test repository", err)

    def test_maven_file_repository(self) -> None:
        """The real mode reads POM files through a file:// URL."""
        self.add_simple("org.x", "lib", "1.0", [("g", "a", "1.5")])
        path = self.write_config(
            repository_mode="real",
            repository_url=self.repo_url,
            package_name="org.x:lib",
            package_version="1.0",
        )
        code, out, _ = run_cli(["--config", path])
        self.assertEqual(code, 0)
        self.assertIn("Direct dependencies of org.x:lib:1.0:", out)
        self.assertIn("  - g:a:1.5", out)

    def test_maven_package_not_found(self) -> None:
        """A missing Maven package is a clean error."""
        path = self.write_config(
            repository_mode="real",
            repository_url=self.repo_url,
            package_name="org.x:none",
        )
        code, _, err = run_cli(["--config", path])
        self.assertEqual(code, 1)
        self.assertIn("was not found", err)
