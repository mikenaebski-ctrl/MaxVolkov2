"""Helpers that build a small Maven repository on disk for tests."""

from typing import Dict, Iterable, Optional, Tuple

from tests.support import WorkspaceCase


def dependency_xml(group: str, artifact: str, version: Optional[str],
                   extra: str = "") -> str:
    """Return one <dependency> element."""
    text = f"<groupId>{group}</groupId><artifactId>{artifact}</artifactId>"
    if version:
        text += f"<version>{version}</version>"
    return f"<dependency>{text}{extra}</dependency>"


def pom_xml(group: str, artifact: str, version: str, deps: str = "",
            extra: str = "") -> str:
    """Return a POM with the given <dependencies> body and extra XML."""
    body = f"<dependencies>{deps}</dependencies>" if deps else ""
    return (
        '<project xmlns="http://maven.apache.org/POM/4.0.0">'
        f"<modelVersion>4.0.0</modelVersion><groupId>{group}</groupId>"
        f"<artifactId>{artifact}</artifactId><version>{version}</version>"
        f"{extra}{body}</project>"
    )


def parent_xml(group: str, artifact: str, version: str) -> str:
    """Return a <parent> element."""
    return (
        f"<parent><groupId>{group}</groupId>"
        f"<artifactId>{artifact}</artifactId>"
        f"<version>{version}</version></parent>"
    )


class MavenRepoCase(WorkspaceCase):
    """A test case that owns an empty Maven repository directory."""

    def setUp(self) -> None:
        """Create the repository directory."""
        super().setUp()
        self.m2 = self.root / "m2"
        self.m2.mkdir()

    @property
    def repo_url(self) -> str:
        """The file:// URL of the repository."""
        return self.m2.as_uri()

    def add_pom(self, group: str, artifact: str, version: str,
                text: str) -> None:
        """Store a POM under the standard repository layout."""
        folder = self.m2 / group.replace(".", "/") / artifact / version
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{artifact}-{version}.pom").write_text(
            text, encoding="utf-8"
        )

    def add_simple(self, group: str, artifact: str, version: str,
                   deps: Iterable[Tuple[str, str, str]] = ()) -> None:
        """Store a POM with plain compile dependencies."""
        body = "".join(dependency_xml(*dep) for dep in deps)
        self.add_pom(group, artifact, version,
                     pom_xml(group, artifact, version, body))


def versions(packages: Iterable) -> Dict[str, str]:
    """Map package names to versions for easy assertions."""
    return {package.name: package.version for package in packages}

