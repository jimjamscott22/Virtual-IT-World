"""Guards for the spec's core principle: tools read world state, never faults.

A violation here is not a style problem — it is the one change that would
collapse multiple fix paths, honest distractors, and the later WinRM backend
all at once, so it is checked mechanically rather than by review.
"""

import ast
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "src" / "vitsc" / "tools"


def imported_modules(source: Path) -> set[str]:
    tree = ast.parse(source.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_tool_imports_a_fault():
    for source in TOOLS.glob("*.py"):
        for module in imported_modules(source):
            assert not module.startswith("vitsc.faults"), (
                f"{source.name} imports {module}; tools must read world state "
                "through Environment only"
            )


def test_no_tool_imports_the_world_model_directly():
    """Tools go through `Environment`, so they never need world types."""
    for source in TOOLS.glob("*.py"):
        for module in imported_modules(source):
            assert not module.startswith("vitsc.world"), (
                f"{source.name} imports {module}; tools should only touch "
                "Query/Action/Observation"
            )
