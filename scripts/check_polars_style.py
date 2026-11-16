"""Check repository-specific Polars style rules."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Violation:
    """A prohibited Polars expression alias."""

    path: Path
    line: int
    column: int


def iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    """Yield Python files below explicit input paths."""
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(path.rglob("*.py"))


def imports_polars(tree: ast.Module) -> bool:
    """Return whether a module imports Polars."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name == "polars" for alias in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "polars" or node.module.startswith("polars."):
                return True
    return False


def find_alias_violations(path: Path) -> list[Violation]:
    """Find method calls named ``alias`` in a Polars module."""
    tree = ast.parse(path.read_text(), filename=str(path))
    if not imports_polars(tree):
        return []

    violations = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "alias"
        ):
            violations.append(
                Violation(
                    path=path,
                    line=node.lineno,
                    column=node.col_offset + 1,
                )
            )
    return violations


def parse_args() -> argparse.Namespace:
    """Parse checker targets."""
    parser = argparse.ArgumentParser(
        description="Reject .alias() calls in modules that import Polars."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("src"), Path("tests")],
    )
    return parser.parse_args()


def main() -> int:
    """Run the checker and return a process exit code."""
    args = parse_args()
    violations = [
        violation
        for path in iter_python_files(args.paths)
        for violation in find_alias_violations(path)
    ]
    for violation in violations:
        print(
            f"{violation.path}:{violation.line}:{violation.column}: "
            "PBR001 use a named Polars expression instead of .alias()"
        )
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main())
