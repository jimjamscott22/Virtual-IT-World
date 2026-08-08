import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.tools.ad import ADConsole
from vitsc.tools.base import ToolLog
from vitsc.world.seed import load_world


@pytest.fixture
def env():
    return SimulatedEnvironment(load_world())


@pytest.fixture
def log():
    return ToolLog()


def test_get_user_renders_attributes(env, log):
    call = ADConsole().invoke(env, log, "get-user", {"sam": "m.alvarez"})
    assert "LockedOut" in call.rendered
    assert call.mutating is False


def test_unlock_is_recorded_as_mutating(env, log):
    env.world.org.users["m.alvarez"].locked_out = True
    call = ADConsole().invoke(env, log, "unlock", {"sam": "m.alvarez"})
    assert call.mutating is True
    assert env.world.org.users["m.alvarez"].locked_out is False


def test_group_commands_target_the_group(env, log):
    call = ADConsole().invoke(env, log, "get-group", {"group": "ACC-Share-RW"})
    assert call.ok and "m.alvarez" in call.rendered


def test_add_member_restores_a_stripped_membership(env, log):
    env.world.org.groups["ACC-Share-RW"].members.remove("m.alvarez")
    call = ADConsole().invoke(
        env, log, "add-member", {"group": "ACC-Share-RW", "member": "m.alvarez"}
    )
    assert call.ok
    assert "m.alvarez" in env.world.org.groups["ACC-Share-RW"].members


def test_every_call_is_logged(env, log):
    ADConsole().invoke(env, log, "get-user", {"sam": "m.alvarez"})
    ADConsole().invoke(env, log, "get-user", {"sam": "d.okafor"})
    assert len(log.calls) == 2
    assert log.calls[0].tool == "ad"


def test_unknown_command_returns_realistic_error(env, log):
    call = ADConsole().invoke(env, log, "frobnicate", {})
    assert call.ok is False
    assert "not recognized" in call.rendered.lower()


def test_missing_argument_does_not_raise(env, log):
    call = ADConsole().invoke(env, log, "get-user", {})
    assert call.ok is False
    assert call.mutating is False


def test_rejected_write_is_not_counted_as_a_mutation(env, log):
    call = ADConsole().invoke(env, log, "unlock", {})
    assert call.ok is False
    assert call.mutating is False
    assert log.first_mutating_index() is None


def test_mutating_calls_before_any_question_are_countable(env, log):
    ADConsole().invoke(env, log, "get-user", {"sam": "m.alvarez"})
    ADConsole().invoke(env, log, "unlock", {"sam": "m.alvarez"})
    assert log.first_mutating_index() == 1
