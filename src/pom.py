"""Parse Maven pom.xml text into plain data classes (no network)."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Optional

from . import constants as c
from .errors import RepositoryError


class Coordinates(NamedTuple):
    """The Maven coordinates groupId, artifactId and version."""

    group: str
    artifact: str
    version: str

    @property
    def key(self) -> str:
        """The groupId:artifactId pair."""
        return f"{self.group}:{self.artifact}"


@dataclass(frozen=True)
class PomDependency:
    """One <dependency> element exactly as written in a POM."""

    group: str
    artifact: str
    version: str
    scope: str
    optional: bool

    @property
    def key(self) -> str:
        """The groupId:artifactId pair."""
        return f"{self.group}:{self.artifact}"


@dataclass
class Pom:
    """The parts of a POM needed to find dependencies."""

    group: str = ""
    artifact: str = ""
    version: str = ""
    parent: Optional[Coordinates] = None
    properties: Dict[str, str] = field(default_factory=dict)
    managed: Dict[str, str] = field(default_factory=dict)
    imports: List[Coordinates] = field(default_factory=list)
    dependencies: List[PomDependency] = field(default_factory=list)


def strip_namespaces(root: ET.Element) -> None:
    """Remove XML namespaces so tags can be searched by plain name."""
    for element in root.iter():
        if isinstance(element.tag, str):
            element.tag = element.tag.rsplit("}", 1)[-1]


def text_of(element: Optional[ET.Element], name: str) -> str:
    """Return the stripped text of a child element or an empty string."""
    if element is None:
        return ""
    child = element.find(name)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def read_dependency(element: ET.Element) -> PomDependency:
    """Convert a <dependency> element."""
    return PomDependency(
        group=text_of(element, "groupId"),
        artifact=text_of(element, "artifactId"),
        version=text_of(element, "version"),
        scope=text_of(element, "scope") or c.SCOPE_COMPILE,
        optional=text_of(element, "optional").lower() == "true",
    )


def read_dependency_list(parent: Optional[ET.Element]) -> List[ET.Element]:
    """Return the <dependency> children of a <dependencies> element."""
    if parent is None:
        return []
    return parent.findall("dependency")


def read_properties(root: ET.Element) -> Dict[str, str]:
    """Collect the <properties> section."""
    section = root.find("properties")
    if section is None:
        return {}
    return {
        child.tag: (child.text or "").strip()
        for child in section
        if isinstance(child.tag, str)
    }


def read_parent(root: ET.Element) -> Optional[Coordinates]:
    """Read the <parent> reference if there is one."""
    parent = root.find("parent")
    if parent is None:
        return None
    return Coordinates(
        text_of(parent, "groupId"),
        text_of(parent, "artifactId"),
        text_of(parent, "version"),
    )


def read_management(root: ET.Element, pom: Pom) -> None:
    """Fill versions and BOM imports from <dependencyManagement>."""
    section = root.find("dependencyManagement/dependencies")
    for element in read_dependency_list(section):
        dep = read_dependency(element)
        is_import = dep.scope == c.SCOPE_IMPORT
        if is_import and text_of(element, "type") == "pom":
            pom.imports.append(
                Coordinates(dep.group, dep.artifact, dep.version)
            )
        elif dep.version:
            pom.managed[dep.key] = dep.version


def parse_pom(text: str) -> Pom:
    """Parse the text of a pom.xml file."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise RepositoryError(f"invalid pom.xml: {error}")
    strip_namespaces(root)
    if root.tag != c.POM_ROOT_TAG:
        raise RepositoryError("invalid pom.xml: the root is not <project>")
    pom = Pom(
        group=text_of(root, "groupId"),
        artifact=text_of(root, "artifactId"),
        version=text_of(root, "version"),
        parent=read_parent(root),
        properties=read_properties(root),
    )
    read_management(root, pom)
    declared = read_dependency_list(root.find("dependencies"))
    pom.dependencies = [read_dependency(item) for item in declared]
    return pom
