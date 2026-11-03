"""The common interface of package repositories and a factory."""

from typing import List

from .config import Config
from .models import Package


class Repository:
    """A source of direct dependencies for packages."""

    def check_root(self, package: Package) -> None:
        """Raise an error if the package does not exist."""
        raise NotImplementedError

    def dependencies(self, package: Package) -> List[Package]:
        """Return the direct dependencies of a package in order."""
        raise NotImplementedError

    def take_warnings(self) -> List[str]:
        """Return and clear the non-fatal problems seen so far."""
        return []


def root_package(config: Config) -> Package:
    """Build the package requested in the configuration."""
    if config.is_test_mode:
        return Package(config.package_name)
    return Package(config.package_name, config.package_version)


def make_repository(config: Config) -> Repository:
    """Create the repository selected by the configuration."""
    from .graph_file import TestRepository
    from .maven_repo import MavenRepository

    if config.is_test_mode:
        return TestRepository.from_file(config.repository_url)
    return MavenRepository(config.repository_url)
