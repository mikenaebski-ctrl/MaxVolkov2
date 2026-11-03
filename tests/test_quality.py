"""Check the source restrictions using only the standard library."""

import ast
import io
import tokenize
import unittest
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIRS = ("src", "tests")
MAX_LINE_LENGTH = 80
MAX_FUNCTION_LINES = 40
MAX_PARAMETERS = 7
MAX_COMPLEXITY = 10
MAX_FILE_LINES = 1000
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
DOCUMENTED_NODES = (ast.Module, ast.ClassDef) + FUNCTION_NODES
NUMERIC_TYPES = (int, float, complex)
UNITTEST_HOOKS = ("setUp", "tearDown", "setUpClass", "tearDownClass")
BRANCH_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.IfExp,
    ast.comprehension,
)


def python_files() -> List[Path]:
    """Find the implementation and test modules."""
    return sorted(
        path
        for directory in PYTHON_DIRS
        for path in (ROOT / directory).rglob("*.py")
    )


def complexity(node: ast.AST) -> int:
    """Count branches, handlers, loops, and Boolean alternatives."""
    value = 1
    for child in ast.walk(node):
        if isinstance(child, BRANCH_NODES):
            value += 1
        if isinstance(child, ast.BoolOp):
            value += len(child.values) - 1
    return value


class QualityTests(unittest.TestCase):
    """Enforce measurable source limits and documentation rules."""

    def test_line_and_file_lengths(self) -> None:
        """Limit physical Python lines and module sizes."""
        for path in python_files():
            lines = path.read_text(encoding="utf-8").splitlines()
            with self.subTest(path=path):
                self.assertLessEqual(len(lines), MAX_FILE_LINES)
            for number, line in enumerate(lines, start=1):
                with self.subTest(path=path, line=number):
                    self.assertLessEqual(len(line), MAX_LINE_LENGTH)

    def test_function_limits(self) -> None:
        """Limit function length, parameter count, and branch count."""
        for path in python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, FUNCTION_NODES):
                    args = node.args
                    count = len(
                        args.posonlyargs + args.args + args.kwonlyargs
                    )
                    count += bool(args.vararg) + bool(args.kwarg)
                    with self.subTest(path=path, function=node.name):
                        self.assertLessEqual(
                            node.end_lineno - node.lineno + 1,
                            MAX_FUNCTION_LINES,
                        )
                        self.assertLessEqual(count, MAX_PARAMETERS)
                        self.assertLessEqual(
                            complexity(node), MAX_COMPLEXITY
                        )

    def test_docstrings(self) -> None:
        """Require module, class, and function docstrings."""
        for path in python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, DOCUMENTED_NODES):
                    with self.subTest(path=path, node=type(node).__name__):
                        self.assertIsNotNone(ast.get_docstring(node))

    def test_no_python_comments(self) -> None:
        """Use docstrings instead of Python comment tokens."""
        for path in python_files():
            source = path.read_text(encoding="utf-8")
            tokens = tokenize.generate_tokens(io.StringIO(source).readline)
            for token in tokens:
                with self.subTest(path=path, line=token.start[0]):
                    self.assertNotEqual(token.type, tokenize.COMMENT)

    def test_comparison_constants(self) -> None:
        """Reject numeric literals within comparison operands."""
        for path in python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    operands = [node.left, *node.comparators]
                    for operand in operands:
                        for child in ast.walk(operand):
                            if isinstance(child, ast.Constant):
                                with self.subTest(path=path):
                                    self.assertNotIn(
                                        type(child.value), NUMERIC_TYPES
                                    )

    def test_snake_case_names(self) -> None:
        """Use PEP 8 names for functions, arguments and variables."""
        pattern = ast.Name
        for path in python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, FUNCTION_NODES):
                    name = node.name
                    if name in UNITTEST_HOOKS:
                        continue
                    with self.subTest(path=path, function=name):
                        self.assertEqual(name, name.lower())
                if isinstance(node, pattern) and isinstance(
                    node.ctx, ast.Store
                ):
                    name = node.id.strip("_") or "x"
                    with self.subTest(path=path, name=node.id):
                        self.assertTrue(name.islower() or name.isupper())
