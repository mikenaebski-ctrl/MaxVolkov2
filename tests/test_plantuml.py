"""Tests for the PlantUML text and its URL encoding."""

import unittest
import zlib

from src.graph import build_graph
from src.graph_file import TestRepository, parse_graph_text
from src.models import Package
from src.plantuml import (
    back_edges,
    encode_plantuml,
    plantuml_lines,
    plantuml_text,
)

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"


def graph_of(text: str):
    """Build a graph with root A from test repository text."""
    repo = TestRepository(parse_graph_text(text))
    return build_graph(repo, Package("A"), 10)


def decode_plantuml(code: str) -> str:
    """Reverse encode_plantuml to check the round trip."""
    value = 0
    for char in code:
        value = value * len(ALPHABET) + ALPHABET.index(char)
    bits = len(code) * 6
    data = value.to_bytes(bits // 8, "big")
    return zlib.decompressobj(-15).decompress(data).decode("utf-8")


class TextTests(unittest.TestCase):
    """The PlantUML source of a graph."""

    def test_simple_graph(self) -> None:
        """Components for all nodes, arrows for all edges."""
        graph = graph_of("A: B C\nB: C\nC:\n")
        self.assertEqual(
            plantuml_lines(graph),
            [
                "@startuml",
                "skinparam componentStyle rectangle",
                'component "A" as n0',
                'component "B" as n1',
                'component "C" as n2',
                "n0 --> n1",
                "n0 --> n2",
                "n1 --> n2",
                "@enduml",
            ],
        )

    def test_cycle_edge_is_red(self) -> None:
        """Only the edge that closes the cycle is red."""
        graph = graph_of("A: B\nB: A\n")
        self.assertEqual(back_edges(graph), {("B", "A")})
        text = plantuml_text(graph)
        self.assertIn("n0 --> n1", text)
        self.assertIn("n1 -[#red]-> n0", text)

    def test_text_ends_with_newline(self) -> None:
        """The text is ready to be written to a file."""
        self.assertTrue(plantuml_text(graph_of("A:\n")).endswith("@enduml\n"))

    def test_version_in_label(self) -> None:
        """The label contains the version when there is one."""
        repo = TestRepository(parse_graph_text("A:\n"))
        graph = build_graph(repo, Package("A", "1.0"), 1)
        self.assertIn('component "A:1.0" as n0', plantuml_text(graph))


class EncodingTests(unittest.TestCase):
    """The deflate + base64 variant used in PlantUML server URLs."""

    def test_official_example(self) -> None:
        """The example from the PlantUML documentation."""
        self.assertEqual(
            encode_plantuml("Bob -> Alice : hello"),
            "SyfFKj2rKt3CoKnELR1Io4ZDoSa70000",
        )

    def test_round_trip(self) -> None:
        """Decoding gives back the original text."""
        text = plantuml_text(graph_of("A: B C\nB: C\nC: A\n"))
        decoded = decode_plantuml(encode_plantuml(text))
        self.assertEqual(decoded, text)

    def test_only_url_safe_characters(self) -> None:
        """The code uses only letters, digits, minus and underscore."""
        code = encode_plantuml("A" * 200)
        self.assertTrue(set(code) <= set(ALPHABET))


if __name__ == "__main__":
    unittest.main()
