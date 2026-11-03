"""Tests for POM parsing, property substitution and versions."""

import unittest

from src.errors import RepositoryError
from src.maven_repo import interpolate, normalize_version, pom_url
from src.pom import Coordinates, parse_pom
from tests.maven_support import dependency_xml, parent_xml, pom_xml


class ParsePomTests(unittest.TestCase):
    """parse_pom reads the interesting parts of a pom.xml."""

    def test_reads_identity_and_dependencies(self) -> None:
        """Namespaces are ignored and scope defaults to compile."""
        deps = dependency_xml("g", "a", "1.0")
        deps += dependency_xml("g", "b", "2", "<scope>test</scope>")
        deps += dependency_xml("g", "c", "3", "<optional>true</optional>")
        pom = parse_pom(pom_xml("org.x", "lib", "9", deps))
        self.assertEqual((pom.group, pom.artifact, pom.version),
                         ("org.x", "lib", "9"))
        self.assertEqual([d.artifact for d in pom.dependencies],
                         ["a", "b", "c"])
        self.assertEqual(pom.dependencies[0].scope, "compile")
        self.assertEqual(pom.dependencies[1].scope, "test")
        self.assertTrue(pom.dependencies[2].optional)

    def test_reads_parent_and_properties(self) -> None:
        """The parent reference and <properties> are kept."""
        extra = parent_xml("org.p", "parent", "5")
        extra += "<properties><k.v>1.2</k.v></properties>"
        pom = parse_pom(pom_xml("org.x", "lib", "9", extra=extra))
        self.assertEqual(pom.parent, Coordinates("org.p", "parent", "5"))
        self.assertEqual(pom.properties, {"k.v": "1.2"})

    def test_reads_management_and_imports(self) -> None:
        """Managed versions and BOM imports are separated."""
        managed = dependency_xml("g", "m", "4")
        managed += dependency_xml(
            "org.bom", "bom", "7", "<type>pom</type><scope>import</scope>"
        )
        extra = (
            "<dependencyManagement><dependencies>"
            f"{managed}</dependencies></dependencyManagement>"
        )
        pom = parse_pom(pom_xml("org.x", "lib", "9", extra=extra))
        self.assertEqual(pom.managed, {"g:m": "4"})
        self.assertEqual(pom.imports, [Coordinates("org.bom", "bom", "7")])

    def test_invalid_xml_and_wrong_root(self) -> None:
        """Broken XML and non-POM XML are repository errors."""
        for text in ("<project>", "not xml", "<other/>"):
            with self.subTest(text=text):
                with self.assertRaises(RepositoryError):
                    parse_pom(text)


class HelperTests(unittest.TestCase):
    """URL building, placeholders and version ranges."""

    def test_pom_url(self) -> None:
        """The URL follows the Maven repository layout."""
        coords = Coordinates("org.slf4j", "slf4j-api", "2.0.9")
        self.assertEqual(
            pom_url("https://repo.example/maven2/", coords),
            "https://repo.example/maven2/org/slf4j/slf4j-api/2.0.9/"
            "slf4j-api-2.0.9.pom",
        )

    def test_interpolate(self) -> None:
        """Nested placeholders are resolved, unknown ones are kept."""
        props = {"a": "${b}.1", "b": "2"}
        self.assertEqual(interpolate("v${a}", props), "v2.1")
        self.assertEqual(interpolate("${missing}", props), "${missing}")

    def test_interpolate_stops_on_self_reference(self) -> None:
        """A property that refers to itself does not loop forever."""
        self.assertEqual(interpolate("${a}", {"a": "${a}x"}).count("x"), 10)

    def test_normalize_version(self) -> None:
        """Ranges become a single version."""
        self.assertEqual(normalize_version("1.0"), "1.0")
        self.assertEqual(normalize_version("[1.2,2.0)"), "1.2")
        self.assertEqual(normalize_version("(,3.0]"), "3.0")
        self.assertEqual(normalize_version("[1.5]"), "1.5")
        self.assertEqual(normalize_version(" "), "")
