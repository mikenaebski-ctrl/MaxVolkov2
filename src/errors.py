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


class RepositoryError(ToolError):
    """A package repository cannot be read or has invalid contents."""


class PackageNotFoundError(RepositoryError):
    """The requested package or POM file does not exist."""


class RenderError(ToolError):
    """The PlantUML text could not be turned into a PNG image."""
