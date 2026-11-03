"""Exceptions raised by the tool for expected, user-facing failures."""

from typing import List


class ToolError(Exception):
    """Base class for failures that are reported without a traceback."""


class ConfigError(ToolError):
    """The configuration file is missing, malformed, or invalid."""

    def __init__(self, problems: List[str]) -> None:
        """Keep every detected problem so all of them can be reported."""
        super().__init__("; ".join(problems))
        self.problems = list(problems)
