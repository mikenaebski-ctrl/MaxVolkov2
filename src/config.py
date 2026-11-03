"""Read and validate the CSV configuration file."""

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from . import constants as c
from .errors import ConfigError


@dataclass(frozen=True)
class Config:
    """Validated user parameters."""

    package_name: str
    repository_url: str
    repository_mode: str
    package_version: str
    output_image: str
    ascii_tree: bool
    max_depth: int

    @property
    def is_test_mode(self) -> bool:
        """Tell whether a test repository file is used."""
        return self.repository_mode == c.MODE_TEST

    def as_pairs(self) -> List[Tuple[str, str]]:
        """Return the parameters as printable key-value pairs."""
        flag = str(self.ascii_tree).lower()
        values = {
            c.PARAM_PACKAGE: self.package_name,
            c.PARAM_REPO_URL: self.repository_url,
            c.PARAM_REPO_MODE: self.repository_mode,
            c.PARAM_VERSION: self.package_version,
            c.PARAM_OUTPUT: self.output_image,
            c.PARAM_ASCII: flag,
            c.PARAM_DEPTH: str(self.max_depth),
        }
        return [(name, values[name]) for name in c.PARAMETERS]


def check_package(value: str, mode: str) -> Optional[str]:
    """Validate the package name for the selected mode."""
    if mode == c.MODE_TEST:
        if not re.match(c.TEST_NAME_PATTERN, value):
            return "test packages use capital Latin letters, e.g. A"
    elif mode == c.MODE_REAL:
        if not re.match(c.MAVEN_NAME_PATTERN, value):
            return "expected Maven coordinates groupId:artifactId"
    return None


def check_url(value: str, mode: str) -> Optional[str]:
    """Validate a repository URL or a test repository file path."""
    if mode == c.MODE_TEST:
        return check_test_file(value)
    if mode != c.MODE_REAL:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in c.URL_SCHEMES:
        return "expected an http://, https:// or file:// URL"
    if parsed.scheme in c.WEB_SCHEMES and not parsed.netloc:
        return "the URL has no host name"
    if not parsed.netloc and not parsed.path:
        return "the URL has no path"
    return None


def check_test_file(value: str) -> Optional[str]:
    """Validate that the test repository path is an existing file."""
    path = Path(value)
    if path.is_dir():
        return "expected a test repository file, got a directory"
    if not path.is_file():
        return "test repository file not found"
    return None


def check_mode(value: str, mode: str) -> Optional[str]:
    """Validate the repository mode."""
    if value not in c.MODES:
        return "expected one of: " + ", ".join(c.MODES)
    return None


def check_version(value: str, mode: str) -> Optional[str]:
    """Validate the package version."""
    if not re.match(c.VERSION_PATTERN, value):
        return "expected a version such as 1.2.3 (no spaces)"
    return None


def check_output(value: str, mode: str) -> Optional[str]:
    """Validate the name of the generated image file."""
    name = Path(value).name
    if not name.lower().endswith(c.IMAGE_SUFFIX):
        return "the image file name must end with " + c.IMAGE_SUFFIX
    if name.lower() == c.IMAGE_SUFFIX:
        return "the image file name has no base name"
    return None


def check_flag(value: str, mode: str) -> Optional[str]:
    """Validate a true/false switch."""
    if value.lower() not in c.TRUE_WORDS + c.FALSE_WORDS:
        words = c.TRUE_WORDS + c.FALSE_WORDS
        return "expected one of: " + ", ".join(words)
    return None


def check_depth(value: str, mode: str) -> Optional[str]:
    """Validate the maximum analysis depth."""
    if not re.match(c.DEPTH_PATTERN, value):
        return "expected a whole number, e.g. 3"
    if int(value) < c.MIN_DEPTH:
        return f"the depth must be at least {c.MIN_DEPTH}"
    return None


CHECKS: Tuple[Tuple[str, Callable[[str, str], Optional[str]]], ...] = (
    (c.PARAM_REPO_MODE, check_mode),
    (c.PARAM_PACKAGE, check_package),
    (c.PARAM_REPO_URL, check_url),
    (c.PARAM_VERSION, check_version),
    (c.PARAM_OUTPUT, check_output),
    (c.PARAM_ASCII, check_flag),
    (c.PARAM_DEPTH, check_depth),
)


def collect_problems(values: Dict[str, str]) -> List[str]:
    """Check every parameter and return all detected problems."""
    problems = [
        f"missing parameter: {name}"
        for name in c.PARAMETERS
        if name not in values
    ]
    mode = values.get(c.PARAM_REPO_MODE, "")
    for name, check in CHECKS:
        if name not in values:
            continue
        if not values[name]:
            problems.append(f"{name}: the value must not be empty")
            continue
        message = check(values[name], mode)
        if message:
            problems.append(f"{name}: {message}")
    return problems


def split_rows(text: str) -> List[List[str]]:
    """Split CSV text into trimmed, non-blank rows."""
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as error:
        raise ConfigError([f"malformed CSV: {error}"])
    cleaned = [[cell.strip() for cell in row] for row in rows]
    return [row for row in cleaned if any(row)]


def parse_values(text: str) -> Dict[str, str]:
    """Turn CSV text with a parameter,value header into a dictionary."""
    rows = split_rows(text)
    if not rows:
        raise ConfigError(["the config file is empty"])
    header_row, *data_rows = rows
    if tuple(header_row) != c.CSV_HEADER:
        header = ",".join(c.CSV_HEADER)
        raise ConfigError([f"the first row must be the header: {header}"])
    values: Dict[str, str] = {}
    problems: List[str] = []
    for number, row in enumerate(data_rows, start=1):
        add_row(values, problems, number, row)
    if problems:
        raise ConfigError(problems)
    return values


def add_row(
    values: Dict[str, str], problems: List[str], number: int, row: List[str]
) -> None:
    """Store one data row or record why it is invalid."""
    if len(row) != len(c.CSV_HEADER):
        problems.append(f"data row {number}: expected parameter,value")
        return
    name, value = row
    if name not in c.PARAMETERS:
        problems.append(f"data row {number}: unknown parameter '{name}'")
    elif name in values:
        problems.append(f"data row {number}: duplicate parameter '{name}'")
    else:
        values[name] = value


def read_text(path: str) -> str:
    """Read the configuration file or explain why it cannot be read."""
    file = Path(path)
    if not file.exists():
        raise ConfigError([f"config file not found: {path}"])
    if not file.is_file():
        raise ConfigError([f"config path is not a file: {path}"])
    try:
        return file.read_text(encoding=c.ENCODING)
    except (OSError, UnicodeDecodeError) as error:
        raise ConfigError([f"cannot read config file {path}: {error}"])


def build_config(values: Dict[str, str]) -> Config:
    """Convert validated text values to a Config object."""
    return Config(
        package_name=values[c.PARAM_PACKAGE],
        repository_url=values[c.PARAM_REPO_URL],
        repository_mode=values[c.PARAM_REPO_MODE],
        package_version=values[c.PARAM_VERSION],
        output_image=values[c.PARAM_OUTPUT],
        ascii_tree=values[c.PARAM_ASCII].lower() in c.TRUE_WORDS,
        max_depth=int(values[c.PARAM_DEPTH]),
    )


def load_config(path: str) -> Config:
    """Read, validate, and convert the configuration file."""
    values = parse_values(read_text(path))
    problems = collect_problems(values)
    if problems:
        raise ConfigError(problems)
    return build_config(values)
