"""Find direct dependencies of Maven packages by reading POM files.

POM files are downloaded with the standard library only (urllib) and
parsed with xml.etree. No package manager is used.
"""

import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from . import constants as c
from .errors import PackageNotFoundError, RepositoryError
from .models import Package
from .pom import Coordinates, Pom, PomDependency, parse_pom
from .repository import Repository

PROPERTY_PATTERN = re.compile(r"\$\{([^}]+)\}")


def fetch_text(url: str) -> str:
    """Download a text file from an http(s) or file URL."""
    request = urllib.request.Request(
        url, headers={"User-Agent": c.USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=c.HTTP_TIMEOUT) as reply:
            data = reply.read()
    except urllib.error.HTTPError as error:
        if error.code == c.HTTP_NOT_FOUND:
            raise PackageNotFoundError(f"not found: {url}")
        raise RepositoryError(f"cannot download {url}: HTTP {error.code}")
    except urllib.error.URLError as error:
        if isinstance(error.reason, FileNotFoundError):
            raise PackageNotFoundError(f"not found: {url}")
        raise RepositoryError(f"cannot download {url}: {error.reason}")
    except (OSError, ValueError) as error:
        raise RepositoryError(f"cannot download {url}: {error}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise RepositoryError(f"{url} is not UTF-8 text")


def pom_url(base: str, coords: Coordinates) -> str:
    """Build the address of a POM file in a Maven repository layout."""
    folder = coords.group.replace(".", "/")
    name = f"{coords.artifact}-{coords.version}.pom"
    path = f"{folder}/{coords.artifact}/{coords.version}/{name}"
    return base.rstrip("/") + "/" + path


def interpolate(text: str, properties: Dict[str, str]) -> str:
    """Replace ${name} placeholders using the property dictionary."""
    for _ in range(c.MAX_INTERPOLATION_PASSES):
        replaced = PROPERTY_PATTERN.sub(
            lambda match: properties.get(match.group(1), match.group(0)),
            text,
        )
        if replaced == text:
            break
        text = replaced
    return text


def normalize_version(text: str) -> str:
    """Turn a version range such as [1.0,2.0) into one version."""
    value = text.strip()
    if value.startswith(("[", "(")):
        parts = [part.strip() for part in value.strip("[]()").split(",")]
        return next((part for part in parts if part), "")
    return value


@dataclass
class Context:
    """Properties and managed versions in effect for one package."""

    properties: Dict[str, str] = field(default_factory=dict)
    managed: Dict[str, str] = field(default_factory=dict)


class MavenRepository(Repository):
    """A Maven repository reached by URL (http, https or file)."""

    def __init__(
        self,
        base_url: str,
        fetch: Callable[[str], str] = fetch_text,
    ) -> None:
        """Remember the base URL and the download function."""
        self.base_url = base_url
        self.fetch = fetch
        self.poms: Dict[Coordinates, Pom] = {}
        self.contexts: Dict[Coordinates, Context] = {}
        self.warnings: List[str] = []

    def load_pom(self, coords: Coordinates) -> Pom:
        """Download and parse one POM, remembering the result."""
        if coords not in self.poms:
            url = pom_url(self.base_url, coords)
            self.poms[coords] = parse_pom(self.fetch(url))
        return self.poms[coords]

    def lineage(self, coords: Coordinates) -> List[Pom]:
        """Return the POM and its chain of parents, child first."""
        chain: List[Pom] = []
        seen: Set[Coordinates] = set()
        current: Optional[Coordinates] = coords
        while current is not None:
            too_long = len(chain) >= c.MAX_PARENT_DEPTH
            if current in seen or too_long:
                raise RepositoryError(f"bad parent chain of {coords}")
            seen.add(current)
            pom = self.load_pom(current)
            chain.append(pom)
            current = pom.parent
        return chain

    def project_properties(
        self, coords: Coordinates, chain: List[Pom]
    ) -> Dict[str, str]:
        """Build the built-in project.* properties."""
        values = {
            "project.groupId": coords.group,
            "project.artifactId": coords.artifact,
            "project.version": coords.version,
            "groupId": coords.group,
            "artifactId": coords.artifact,
            "version": coords.version,
        }
        parent = chain[0].parent
        if parent is not None:
            values["project.parent.version"] = parent.version
            values["parent.version"] = parent.version
            values["project.parent.groupId"] = parent.group
        return values

    def context(
        self, coords: Coordinates, active: Tuple[Coordinates, ...] = ()
    ) -> Context:
        """Merge properties and managed versions along the parent chain."""
        if coords in self.contexts:
            return self.contexts[coords]
        chain = self.lineage(coords)
        properties: Dict[str, str] = {}
        managed: Dict[str, str] = {}
        for pom in reversed(chain):
            properties.update(pom.properties)
            properties.update(self.project_properties(coords, chain))
            for item in pom.imports:
                managed.update(self.import_bom(item, properties, active))
            managed.update(pom.managed)
        resolved = {
            key: interpolate(value, properties)
            for key, value in managed.items()
        }
        self.contexts[coords] = Context(properties, resolved)
        return self.contexts[coords]

    def import_bom(
        self,
        item: Coordinates,
        properties: Dict[str, str],
        active: Tuple[Coordinates, ...],
    ) -> Dict[str, str]:
        """Return the managed versions of an imported BOM."""
        version = interpolate(item.version, properties)
        bom = Coordinates(item.group, item.artifact, version)
        if bom in active or len(active) >= c.MAX_PARENT_DEPTH:
            return {}
        inner = self.context(bom, active + (bom,))
        return {
            key: interpolate(value, inner.properties)
            for key, value in inner.managed.items()
        }

    def convert(
        self, dep: PomDependency, context: Context, owner: str
    ) -> Optional[Package]:
        """Turn a POM dependency into a package or skip it."""
        if dep.optional or dep.scope not in c.INCLUDED_SCOPES:
            return None
        props = context.properties
        group = interpolate(dep.group, props)
        artifact = interpolate(dep.artifact, props)
        raw = dep.version or context.managed.get(f"{group}:{artifact}", "")
        version = normalize_version(interpolate(raw, props))
        if not version or "${" in version:
            self.warnings.append(
                f"{owner}: no version for {group}:{artifact}, skipped"
            )
            return None
        return Package(f"{group}:{artifact}", version)

    def check_root(self, package: Package) -> None:
        """Raise an error if the package POM cannot be found."""
        try:
            self.load_pom(coordinates_of(package))
        except PackageNotFoundError as error:
            raise PackageNotFoundError(
                f"package {package.label} was not found ({error})"
            )

    def dependencies(self, package: Package) -> List[Package]:
        """Return the compile and runtime dependencies of a package."""
        coords = coordinates_of(package)
        context = self.context(coords)
        result: List[Package] = []
        seen: Set[str] = set()
        for pom in self.lineage(coords):
            for dep in pom.dependencies:
                found = self.convert(dep, context, package.label)
                if found is not None and found.key not in seen:
                    seen.add(found.key)
                    result.append(found)
        return result

    def take_warnings(self) -> List[str]:
        """Return and clear the non-fatal problems seen so far."""
        warnings, self.warnings = self.warnings, []
        return warnings


def coordinates_of(package: Package) -> Coordinates:
    """Split a package name groupId:artifactId and add the version."""
    group, _, artifact = package.name.partition(":")
    return Coordinates(group, artifact, package.version)
