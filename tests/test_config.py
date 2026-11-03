"""Tests for reading and validating the CSV configuration."""

from src.config import load_config
from src.errors import ConfigError
from tests.support import WorkspaceCase


class ValidConfigTests(WorkspaceCase):
    """Valid configuration files are converted to a Config object."""

    def test_reads_all_parameters(self) -> None:
        """Every parameter is available after loading."""
        config = load_config(self.write_config())
        self.assertEqual(config.package_name, "A")
        self.assertEqual(config.repository_mode, "test")
        self.assertEqual(config.package_version, "1.0")
        self.assertEqual(config.output_image, "graph.png")
        self.assertTrue(config.ascii_tree)
        self.assertEqual(config.max_depth, 3)

    def test_pairs_keep_the_documented_order(self) -> None:
        """Key-value pairs follow the parameter list order."""
        pairs = load_config(self.write_config()).as_pairs()
        names = [name for name, _ in pairs]
        self.assertEqual(names[0], "package_name")
        self.assertEqual(names[-1], "max_depth")
        self.assertIn(("ascii_tree", "true"), pairs)

    def test_maven_coordinates_in_real_mode(self) -> None:
        """Real mode expects groupId:artifactId and a URL."""
        path = self.write_config(
            package_name="org.slf4j:slf4j-simple",
            repository_mode="real",
            repository_url="https://repo1.maven.org/maven2/",
            package_version="2.0.9",
        )
        config = load_config(path)
        self.assertFalse(config.is_test_mode)

    def test_flag_words_and_blank_rows(self) -> None:
        """Flags are case-insensitive and blank rows are skipped."""
        text = self.config_text(ascii_tree="NO") + "\n,\n"
        path = self.root / "config.csv"
        path.write_text(text, encoding="utf-8")
        self.assertFalse(load_config(str(path)).ascii_tree)


class InvalidConfigTests(WorkspaceCase):
    """Every kind of bad input produces a clear message."""

    def problems(self, **overrides: str) -> str:
        """Load a broken configuration and return the error text."""
        with self.assertRaises(ConfigError) as caught:
            load_config(self.write_config(**overrides))
        return "\n".join(caught.exception.problems)

    def test_missing_file(self) -> None:
        """A missing config file is reported."""
        with self.assertRaises(ConfigError) as caught:
            load_config(str(self.root / "nope.csv"))
        self.assertIn("not found", caught.exception.problems[0])

    def test_directory_instead_of_file(self) -> None:
        """A directory cannot be used as the config file."""
        with self.assertRaises(ConfigError) as caught:
            load_config(str(self.root))
        self.assertIn("not a file", caught.exception.problems[0])

    def test_empty_and_wrong_header(self) -> None:
        """An empty file and a wrong header are rejected."""
        path = self.root / "bad.csv"
        for text, word in (("", "empty"), ("a,b\n1,2\n", "header")):
            path.write_text(text, encoding="utf-8")
            with self.subTest(text=text):
                with self.assertRaises(ConfigError) as caught:
                    load_config(str(path))
                self.assertIn(word, caught.exception.problems[0])

    def test_unreadable_encoding(self) -> None:
        """A file that is not UTF-8 text is reported."""
        path = self.root / "bad.csv"
        path.write_bytes(b"\xff\xfe\x00\x80\x81")
        with self.assertRaises(ConfigError) as caught:
            load_config(str(path))
        self.assertIn("cannot read", caught.exception.problems[0])

    def test_unknown_duplicate_and_short_rows(self) -> None:
        """Unknown names, duplicates and rows without a value fail."""
        text = self.config_text() + "colour,red\nmax_depth,5\nlonely\n"
        path = self.root / "bad.csv"
        path.write_text(text, encoding="utf-8")
        with self.assertRaises(ConfigError) as caught:
            load_config(str(path))
        joined = "\n".join(caught.exception.problems)
        self.assertIn("unknown parameter 'colour'", joined)
        self.assertIn("duplicate parameter 'max_depth'", joined)
        self.assertIn("expected parameter,value", joined)

    def test_missing_parameters(self) -> None:
        """Each absent parameter is named."""
        text = self.problems(max_depth=None, package_version=None)
        self.assertIn("missing parameter: max_depth", text)
        self.assertIn("missing parameter: package_version", text)

    def test_empty_values(self) -> None:
        """Empty values are rejected for every parameter."""
        text = self.problems(package_name="", output_image="")
        self.assertIn("package_name: the value must not be empty", text)
        self.assertIn("output_image: the value must not be empty", text)

    def test_bad_package_names(self) -> None:
        """Names must match the selected mode."""
        self.assertIn("capital Latin", self.problems(package_name="a1"))
        text = self.problems(repository_mode="real", package_name="x")
        self.assertIn("groupId:artifactId", text)

    def test_bad_mode(self) -> None:
        """Only real and test modes exist."""
        self.assertIn("one of: real, test", self.problems(repository_mode="x"))

    def test_bad_urls_and_files(self) -> None:
        """URLs and test repository paths are checked."""
        real = {"repository_mode": "real", "package_name": "a:b"}
        for url, word in (
            ("ftp://example.org/m2", "http://"),
            ("http://", "host"),
            ("file://", "path"),
            ("not a url", "http://"),
        ):
            with self.subTest(url=url):
                text = self.problems(repository_url=url, **real)
                self.assertIn(word, text)
        self.assertIn("not found", self.problems(repository_url="/x/y.txt"))
        self.assertIn("directory", self.problems(repository_url=str(self.root)))

    def test_bad_version(self) -> None:
        """A version with spaces or symbols is rejected."""
        self.assertIn("version", self.problems(package_version="1 2"))
        self.assertIn("version", self.problems(package_version="-1"))

    def test_bad_image_names(self) -> None:
        """The image file must be a named .png file."""
        self.assertIn(".png", self.problems(output_image="graph.jpg"))
        self.assertIn("base name", self.problems(output_image=".png"))

    def test_bad_flag(self) -> None:
        """The ASCII switch accepts only boolean words."""
        self.assertIn("one of", self.problems(ascii_tree="maybe"))

    def test_bad_depth(self) -> None:
        """The depth must be a positive whole number."""
        for value in ("abc", "-1", "2.5", "0"):
            with self.subTest(value=value):
                self.assertIn("max_depth", self.problems(max_depth=value))

    def test_all_problems_are_reported_together(self) -> None:
        """One run lists every invalid parameter."""
        text = self.problems(max_depth="x", ascii_tree="y", package_name="1")
        self.assertEqual(len(text.splitlines()), len(set(text.splitlines())))
        self.assertIn("max_depth", text)
        self.assertIn("ascii_tree", text)
        self.assertIn("package_name", text)
