"""Generate PlantUML text for a dependency graph and encode it."""

import zlib
from typing import List, Set, Tuple

from . import constants as c
from .graph import Graph

RAW_DEFLATE_BITS = -15
DEFLATE_LEVEL = 9
SIX_BITS = 63
TRIPLE_SHIFTS = (18, 12, 6, 0)


def back_edges(graph: Graph) -> Set[Tuple[str, str]]:
    """Return the edges that close a cycle."""
    return {(cycle[-2], cycle[-1]) for cycle in graph.cycles}


def alias_map(graph: Graph) -> dict:
    """Give every node a short PlantUML identifier."""
    return {key: f"n{number}" for number, key in enumerate(graph.nodes)}


def plantuml_lines(graph: Graph) -> List[str]:
    """Return the PlantUML source of the graph, one line per element."""
    aliases = alias_map(graph)
    lines = [c.PLANTUML_START, "skinparam componentStyle rectangle"]
    for key, package in graph.nodes.items():
        label = package.label.replace('"', "'")
        lines.append(f'component "{label}" as {aliases[key]}')
    cyclic = back_edges(graph)
    for key in graph.nodes:
        for target in graph.children(key):
            arrow = c.PLANTUML_ARROW
            if (key, target) in cyclic:
                arrow = c.PLANTUML_CYCLE_ARROW
            lines.append(f"{aliases[key]} {arrow} {aliases[target]}")
    lines.append(c.PLANTUML_END)
    return lines


def plantuml_text(graph: Graph) -> str:
    """Return the PlantUML source as one text."""
    return "\n".join(plantuml_lines(graph)) + "\n"


def encode_triple(chunk: bytes) -> str:
    """Encode up to three bytes as four characters of the PlantUML alphabet."""
    value = int.from_bytes(chunk.ljust(len(TRIPLE_SHIFTS) - 1, b"\0"), "big")
    return "".join(
        c.PLANTUML_ALPHABET[(value >> shift) & SIX_BITS]
        for shift in TRIPLE_SHIFTS
    )


def encode_plantuml(text: str) -> str:
    """Encode text for a PlantUML server URL (deflate + base64 variant)."""
    packer = zlib.compressobj(DEFLATE_LEVEL, zlib.DEFLATED, RAW_DEFLATE_BITS)
    data = packer.compress(text.encode("utf-8")) + packer.flush()
    step = len(TRIPLE_SHIFTS) - 1
    return "".join(
        encode_triple(data[start:start + step])
        for start in range(0, len(data), step)
    )
