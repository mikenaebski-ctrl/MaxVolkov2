"""Tests for PNG rendering (the renderers are replaced by fakes)."""

import subprocess
import unittest
from pathlib import Path
from typing import Any, List
from unittest import mock

from src.errors import RenderError
from src.render import (
    check_png,
    render_png,
    render_with_jar,
    render_with_server,
    save_files,
)
from tests.support import WorkspaceCase
from tests.test_cli import run_cli

PNG = b"\x89PNG\r\n\x1a\n" + b"data"


class FakeRunner:
    """Replaces subprocess.run and remembers how it was called."""

    def __init__(self, code: int = 0, out: bytes = PNG,
                 err: bytes = b"") -> None:
        """Prepare the answer."""
        self.answer = subprocess.CompletedProcess([], code, out, err)
        self.calls: List[Any] = []

    def __call__(self, command: List[str], **kwargs: Any) -> Any:
        """Record the call and return the prepared answer."""
        self.calls.append((command, kwargs))
        return self.answer


class JarTests(unittest.TestCase):
    """Rendering with java -jar."""

    def test_command_and_input(self) -> None:
        """The text goes to stdin of java -jar FILE -pipe -tpng."""
        runner = FakeRunner()
        data = render_with_jar("@startuml\n@enduml\n", "p.jar", runner)
        command, kwargs = runner.calls[0]
        self.assertEqual(
            command, ["java", "-jar", "p.jar", "-pipe", "-tpng"]
        )
        self.assertEqual(kwargs["input"], b"@startuml\n@enduml\n")
        self.assertEqual(data, PNG)

    def test_failure_exit_code(self) -> None:
        """A non-zero exit code becomes a RenderError with the message."""
        runner = FakeRunner(code=1, out=b"", err=b"boom")
        with self.assertRaises(RenderError) as caught:
            render_with_jar("x", "p.jar", runner)
        self.assertIn("boom", str(caught.exception))

    def test_java_missing(self) -> None:
        """A missing java program is reported, not raised as OSError."""
        def runner(*_args: Any, **_kwargs: Any) -> Any:
            """Behave like a system without java."""
            raise FileNotFoundError("java")

        with self.assertRaises(RenderError):
            render_with_jar("x", "p.jar", runner)


class ServerTests(unittest.TestCase):
    """Rendering with a PlantUML server."""

    def test_url(self) -> None:
        """The address is SERVER/png/ENCODED_TEXT."""
        urls: List[str] = []

        def fetch(url: str) -> bytes:
            """Remember the address and return a PNG."""
            urls.append(url)
            return PNG

        render_with_server("Bob -> Alice : hello", "http://h/plantuml/", fetch)
        self.assertEqual(
            urls,
            ["http://h/plantuml/png/SyfFKj2rKt3CoKnELR1Io4ZDoSa70000"],
        )


class CheckTests(unittest.TestCase):
    """PNG validation and the choice of the renderer."""

    def test_png_signature(self) -> None:
        """Only data with the PNG signature is accepted."""
        self.assertEqual(check_png(PNG), PNG)
        with self.assertRaises(RenderError):
            check_png(b"<html>")

    def test_no_renderer(self) -> None:
        """Without a jar and a server nothing can be rendered."""
        with self.assertRaises(RenderError):
            render_png("x", None, None)


class SaveTests(WorkspaceCase):
    """Writing the PNG and the .puml file."""

    def test_files_are_written_together(self) -> None:
        """The source gets the .puml suffix next to the image."""
        image = str(self.root / "out.png")
        source = save_files("text\n", PNG, image)
        self.assertEqual(source, self.root / "out.puml")
        self.assertEqual(Path(image).read_bytes(), PNG)
        self.assertEqual(source.read_text(encoding="utf-8"), "text\n")

    def test_unwritable_folder(self) -> None:
        """A missing folder is a RenderError."""
        with self.assertRaises(RenderError):
            save_files("t", PNG, str(self.root / "no" / "out.png"))


class CommandTests(WorkspaceCase):
    """The stage 5 command line options."""

    def test_print_plantuml(self) -> None:
        """--plantuml prints only the PlantUML source."""
        code, out, _ = run_cli(["--plantuml", "--config", self.write_config()])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("@startuml\n"))
        self.assertTrue(out.endswith("@enduml\n"))

    def test_render_with_jar(self) -> None:
        """The image and the source are saved and announced."""
        image = str(self.root / "graph.png")
        path = self.write_config(output_image=image)
        with mock.patch("src.cli.render_png", return_value=PNG) as fake:
            code, out, _ = run_cli(
                ["--plantuml-jar", "p.jar", "--config", path]
            )
        self.assertEqual(code, 0)
        self.assertEqual(fake.call_args[0][1:], ("p.jar", None))
        self.assertIn(f"Image saved: {image}", out)
        self.assertTrue((self.root / "graph.puml").exists())
        self.assertIn("└── ", out)

    def test_render_error_exit_code(self) -> None:
        """A renderer failure is a clean runtime error."""
        path = self.write_config(output_image=str(self.root / "g.png"))
        with mock.patch("src.cli.render_png", side_effect=RenderError("no")):
            code, _, err = run_cli(
                ["--plantuml-server", "http://x", "--config", path]
            )
        self.assertEqual(code, 1)
        self.assertIn("error: no", err)


if __name__ == "__main__":
    unittest.main()
