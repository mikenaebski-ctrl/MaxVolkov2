"""Turn PlantUML text into a PNG file with a jar file or a server."""

import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

from . import constants as c
from .errors import RenderError
from .plantuml import encode_plantuml


def fetch_bytes(url: str) -> bytes:
    """Download a binary file."""
    request = urllib.request.Request(
        url, headers={"User-Agent": c.USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=c.RENDER_TIMEOUT) as reply:
            return reply.read()
    except urllib.error.HTTPError as error:
        raise RenderError(f"PlantUML server answered HTTP {error.code}")
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise RenderError(f"cannot reach the PlantUML server: {error}")


def render_with_jar(
    text: str, jar: str, runner: Callable[..., Any] = subprocess.run
) -> bytes:
    """Run java -jar plantuml.jar and return the PNG it prints."""
    command = ["java", "-jar", jar, "-pipe", "-tpng"]
    try:
        done = runner(
            command,
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=c.RENDER_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RenderError(f"cannot run PlantUML: {error}")
    if done.returncode:
        detail = done.stderr.decode("utf-8", "replace").strip()
        raise RenderError(f"PlantUML failed: {detail}")
    return done.stdout


def render_with_server(
    text: str, server: str, fetch: Callable[[str], bytes] = fetch_bytes
) -> bytes:
    """Ask a PlantUML server for the PNG of the text."""
    url = f"{server.rstrip('/')}/png/{encode_plantuml(text)}"
    return fetch(url)


def check_png(data: bytes) -> bytes:
    """Return the data if it is a PNG image, otherwise raise an error."""
    if not data.startswith(c.PNG_SIGNATURE):
        raise RenderError("the renderer did not return a PNG image")
    return data


def render_png(
    text: str, jar: Optional[str], server: Optional[str]
) -> bytes:
    """Render with the jar file if given, otherwise with the server."""
    if jar:
        return check_png(render_with_jar(text, jar))
    if server:
        return check_png(render_with_server(text, server))
    raise RenderError("no renderer: use --plantuml-jar or --plantuml-server")


def save_files(text: str, png: bytes, image_path: str) -> Path:
    """Write the PNG and the .puml source next to it; return the .puml."""
    target = Path(image_path)
    source = target.with_suffix(".puml")
    try:
        target.write_bytes(png)
        source.write_text(text, encoding="utf-8")
    except OSError as error:
        raise RenderError(f"cannot write {error.filename}: {error.strerror}")
    return source
