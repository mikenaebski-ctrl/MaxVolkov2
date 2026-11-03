"""Tests for finding dependencies in a Maven repository layout."""

import functools
import http.server
import threading
import unittest
import urllib.error
from typing import Dict
from unittest import mock

from src.errors import PackageNotFoundError, RepositoryError
from src.maven_repo import MavenRepository, fetch_text
from src.models import Package
from tests.maven_support import (
    MavenRepoCase,
    dependency_xml,
    parent_xml,
    pom_xml,
    versions,
)

ROOT = Package("org.x:lib", "1.0")


def found(repo: MavenRepository, package: Package = ROOT) -> Dict[str, str]:
    """Return name -> version of the direct dependencies."""
    return versions(repo.dependencies(package))


class DirectDependencyTests(MavenRepoCase):
    """Direct dependencies with explicit versions."""

    def test_plain_dependencies(self) -> None:
        """Dependencies are returned in declaration order."""
        self.add_simple("org.x", "lib", "1.0",
                        [("g", "a", "1"), ("g", "b", "2")])
        repo = MavenRepository(self.repo_url)
        self.assertEqual(
            [p.label for p in repo.dependencies(ROOT)], ["g:a:1", "g:b:2"]
        )

    def test_scopes_and_optional(self) -> None:
        """Only compile and runtime non-optional dependencies stay."""
        deps = dependency_xml("g", "compile", "1")
        deps += dependency_xml("g", "runtime", "1", "<scope>runtime</scope>")
        deps += dependency_xml("g", "test", "1", "<scope>test</scope>")
        deps += dependency_xml("g", "prov", "1", "<scope>provided</scope>")
        deps += dependency_xml("g", "opt", "1", "<optional>true</optional>")
        text = pom_xml("org.x", "lib", "1.0", deps)
        self.add_pom("org.x", "lib", "1.0", text)
        repo = MavenRepository(self.repo_url)
        self.assertEqual(set(found(repo)), {"g:compile", "g:runtime"})

    def test_no_dependencies(self) -> None:
        """A POM without dependencies gives an empty list."""
        self.add_simple("org.x", "lib", "1.0")
        self.assertEqual(MavenRepository(self.repo_url).dependencies(ROOT), [])

    def test_missing_root_package(self) -> None:
        """A package that is not in the repository is not found."""
        repo = MavenRepository(self.repo_url)
        with self.assertRaises(PackageNotFoundError) as caught:
            repo.check_root(ROOT)
        self.assertIn("org.x:lib:1.0", str(caught.exception))

    def test_broken_pom(self) -> None:
        """Invalid XML in the POM is a repository error."""
        self.add_pom("org.x", "lib", "1.0", "<project>")
        with self.assertRaises(RepositoryError):
            MavenRepository(self.repo_url).dependencies(ROOT)


class VersionResolutionTests(MavenRepoCase):
    """Properties, parents, BOM imports and ranges."""

    def test_property_versions(self) -> None:
        """${...} placeholders use the <properties> of the POM."""
        extra = "<properties><a.ver>3.1</a.ver></properties>"
        deps = dependency_xml("g", "a", "${a.ver}")
        deps += dependency_xml("g", "self", "${project.version}")
        self.add_pom("org.x", "lib", "1.0",
                     pom_xml("org.x", "lib", "1.0", deps, extra))
        self.assertEqual(
            found(MavenRepository(self.repo_url)),
            {"g:a": "3.1", "g:self": "1.0"},
        )

    def test_parent_dependencies_and_management(self) -> None:
        """A child inherits dependencies, properties and managed versions."""
        managed = (
            "<properties><m.ver>8</m.ver></properties>"
            "<dependencyManagement><dependencies>"
            + dependency_xml("g", "managed", "${m.ver}")
            + "</dependencies></dependencyManagement>"
        )
        self.add_pom("org.p", "parent", "5", pom_xml(
            "org.p", "parent", "5", dependency_xml("g", "shared", "2"),
            managed))
        child = pom_xml("org.x", "lib", "1.0",
                        dependency_xml("g", "managed", None),
                        parent_xml("org.p", "parent", "5"))
        self.add_pom("org.x", "lib", "1.0", child)
        self.assertEqual(
            found(MavenRepository(self.repo_url)),
            {"g:managed": "8", "g:shared": "2"},
        )

    def test_bom_import(self) -> None:
        """Versions from an imported BOM use the BOM's own properties."""
        bom_extra = (
            "<properties><b.ver>6</b.ver></properties>"
            "<dependencyManagement><dependencies>"
            + dependency_xml("g", "bommed", "${b.ver}")
            + "</dependencies></dependencyManagement>"
        )
        self.add_pom("org.bom", "bom", "1", pom_xml(
            "org.bom", "bom", "1", extra=bom_extra))
        imported = dependency_xml(
            "org.bom", "bom", "1", "<type>pom</type><scope>import</scope>")
        extra = (
            "<dependencyManagement><dependencies>"
            f"{imported}</dependencies></dependencyManagement>"
        )
        self.add_pom("org.x", "lib", "1.0", pom_xml(
            "org.x", "lib", "1.0", dependency_xml("g", "bommed", None), extra))
        self.assertEqual(found(MavenRepository(self.repo_url)),
                         {"g:bommed": "6"})

    def test_version_range(self) -> None:
        """A range is replaced by its lower bound."""
        self.add_simple("org.x", "lib", "1.0", [("g", "a", "[2.0,3.0)")])
        self.assertEqual(found(MavenRepository(self.repo_url)),
                         {"g:a": "2.0"})

    def test_missing_version_is_a_warning(self) -> None:
        """A dependency without any version is skipped with a warning."""
        deps = dependency_xml("g", "ok", "1")
        deps += dependency_xml("g", "nover", None)
        text = pom_xml("org.x", "lib", "1.0", deps)
        self.add_pom("org.x", "lib", "1.0", text)
        repo = MavenRepository(self.repo_url)
        self.assertEqual(found(repo), {"g:ok": "1"})
        self.assertIn("g:nover", repo.take_warnings()[0])
        self.assertEqual(repo.take_warnings(), [])

    def test_parent_cycle(self) -> None:
        """A parent chain that loops is reported."""
        self.add_pom("org.x", "lib", "1.0", pom_xml(
            "org.x", "lib", "1.0", extra=parent_xml("org.x", "lib", "1.0")))
        with self.assertRaises(RepositoryError):
            MavenRepository(self.repo_url).dependencies(ROOT)

    def test_missing_parent(self) -> None:
        """An absent parent POM is a not-found error."""
        self.add_pom("org.x", "lib", "1.0", pom_xml(
            "org.x", "lib", "1.0", extra=parent_xml("org.p", "gone", "1")))
        with self.assertRaises(PackageNotFoundError):
            MavenRepository(self.repo_url).dependencies(ROOT)

    def test_downloads_are_cached(self) -> None:
        """Each POM is fetched only once."""
        self.add_simple("org.x", "lib", "1.0", [("g", "a", "1")])
        calls = []

        def counting(url: str) -> str:
            """Record the URL and read it normally."""
            calls.append(url)
            return fetch_text(url)

        repo = MavenRepository(self.repo_url, counting)
        repo.dependencies(ROOT)
        repo.dependencies(ROOT)
        self.assertEqual(len(calls), 1)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files from a directory without printing request logs."""

    def log_message(self, *args: object) -> None:
        """Do not print request logs."""


class HttpFetchTests(MavenRepoCase):
    """fetch_text works with real HTTP responses."""

    def setUp(self) -> None:
        """Start a local HTTP server for the repository directory."""
        super().setUp()
        handler = functools.partial(QuietHandler, directory=str(self.m2))
        address = ("127.0.0.1", 0)
        self.server = http.server.ThreadingHTTPServer(address, handler)
        self.addCleanup(self.server.server_close)
        thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.05}
        )
        thread.daemon = True
        thread.start()
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def test_http_success_and_dependencies(self) -> None:
        """A repository served over HTTP works like a file repository."""
        self.add_simple("org.x", "lib", "1.0", [("g", "a", "1")])
        self.assertEqual(found(MavenRepository(self.base)), {"g:a": "1"})

    def test_http_404(self) -> None:
        """HTTP 404 becomes PackageNotFoundError."""
        with self.assertRaises(PackageNotFoundError):
            fetch_text(self.base + "/nothing.pom")

    def test_http_500(self) -> None:
        """Other HTTP errors are repository errors, not crashes."""
        failure = urllib.error.HTTPError(self.base, 500, "boom", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=failure):
            with self.assertRaises(RepositoryError) as caught:
                fetch_text(self.base + "/broken")
        self.assertNotIsInstance(caught.exception, PackageNotFoundError)
        self.assertIn("HTTP 500", str(caught.exception))

    def test_unreachable_server(self) -> None:
        """A refused connection is a repository error."""
        refused = urllib.error.URLError(ConnectionRefusedError("refused"))
        with mock.patch("urllib.request.urlopen", side_effect=refused):
            with self.assertRaises(RepositoryError) as caught:
                fetch_text(self.base + "/x.pom")
        self.assertIn("refused", str(caught.exception))

    def test_non_text_answer(self) -> None:
        """Bytes that are not UTF-8 are rejected."""
        (self.m2 / "bad.pom").write_bytes(b"\xff\xfe\xfa")
        with self.assertRaises(RepositoryError):
            fetch_text(self.base + "/bad.pom")


if __name__ == "__main__":
    unittest.main()
