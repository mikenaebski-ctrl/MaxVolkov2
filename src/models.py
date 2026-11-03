"""Small data classes shared by the repositories and the graph."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Package:
    """A package identified by its name and, for Maven, its version."""

    name: str
    version: str = ""

    @property
    def key(self) -> str:
        """Identity used to detect that two nodes are the same package."""
        return self.name

    @property
    def label(self) -> str:
        """Text shown to the user, e.g. org.x:lib:1.0 or A."""
        if self.version:
            return f"{self.name}:{self.version}"
        return self.name
