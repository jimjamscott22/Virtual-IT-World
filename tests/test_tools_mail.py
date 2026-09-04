from vitsc.env.simulated import SimulatedEnvironment
from vitsc.tools.base import ToolLog
from vitsc.tools.registry import get_tool
from vitsc.world.seed import load_world


def test_get_mailbox_renders_like_the_real_cmdlet():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "get-mailbox", {"sam": "m.alvarez"})
    assert call.ok and call.mutating is False
    assert "PrimarySmtpAddress" in call.rendered


def test_writes_are_flagged_mutating():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "set-quota", {"sam": "m.alvarez", "quota_mb": "102400"})
    assert call.ok and call.mutating is True


def test_a_missing_parameter_is_reported_not_raised():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "set-quota", {"sam": "m.alvarez"})
    assert call.ok is False and "quota_mb" in call.rendered


def test_an_unknown_command_matches_the_shell_s_own_error():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "Get-Everything", {})
    assert call.ok is False and "not recognized" in call.rendered


def test_every_call_is_logged():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    tool.invoke(env, log, "get-mailbox", {"sam": "m.alvarez"})
    tool.invoke(env, log, "nope", {})
    assert len(log.calls) == 2


def test_get_queue_targets_the_mail_server_by_host():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "get-queue", {"host": "MER-MB-01"})
    assert call.ok
    assert "Running" in call.rendered


def test_restart_transport_targets_the_mail_server_by_host():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "restart-transport", {"host": "MER-MB-01"})
    assert call.ok and call.mutating is True


def test_get_queue_on_an_unknown_host_fails_cleanly():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "get-queue", {"host": "MER-WS-001"})
    assert call.ok is False
