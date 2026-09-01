from vitsc.env.simulated import SimulatedEnvironment
from vitsc.tools.base import ToolLog
from vitsc.tools.registry import get_tool
from vitsc.world.seed import load_world


def test_kb_search_renders_hits():
    tool, env, log = get_tool("kb"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "search", {"text": "printer"})
    assert call.ok and "printing-nothing-prints" in call.rendered


def test_kb_read_renders_the_body():
    tool, env, log = get_tool("kb"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "read", {"id": "general-triage-first-questions"})
    assert call.ok and "## Check" in call.rendered


def test_kb_calls_are_never_mutating():
    tool, env, log = get_tool("kb"), SimulatedEnvironment(load_world()), ToolLog()
    calls = [("search", {"text": "printer"}), ("read", {"id": "general-meridian-estate"})]
    for command, args in calls:
        assert tool.invoke(env, log, command, args).mutating is False


def test_a_missing_article_fails_without_raising():
    tool, env, log = get_tool("kb"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "read", {"id": "nope"})
    assert call.ok is False


def test_the_kb_tool_does_not_import_faults_or_world():
    """The architecture rule binds this tool like every other."""
    import ast
    import pathlib
    src = pathlib.Path("src/vitsc/tools/kb.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith(("vitsc.faults", "vitsc.world"))
