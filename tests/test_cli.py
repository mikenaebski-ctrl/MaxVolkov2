"""Tests for the command-line interface."""

import contextlib
import io
from typing import List, Tuple

from src.cli import main
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
        code, out, _ = run_cli(["--config", self.write_config()])
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
