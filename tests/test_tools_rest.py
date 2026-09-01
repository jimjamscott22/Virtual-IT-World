import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.tools.base import ToolLog
from vitsc.tools.eventlog import EventViewer
from vitsc.tools.network import NetworkTools
from vitsc.tools.powershell import PowerShellConsole
from vitsc.tools.printing import PrintManagement
from vitsc.tools.registry import all_tools, get_tool
from vitsc.tools.remote import RemoteSession
from vitsc.world.models import ServiceState
from vitsc.world.seed import load_world


@pytest.fixture
def env():
    return SimulatedEnvironment(load_world())


@pytest.fixture
def log():
    return ToolLog()


def test_ping_renders_replies(env, log):
    call = NetworkTools().invoke(env, log, "ping", {"host": "MER-FS-01", "from": "MER-WS-001"})
    assert call.ok and "Reply from" in call.rendered


def test_ping_fails_on_broken_dns(env, log):
    env.world.machines["MER-WS-001"].dns_servers = ["10.20.10.99"]
    call = NetworkTools().invoke(env, log, "ping", {"host": "MER-FS-01", "from": "MER-WS-001"})
    assert call.ok is False and "could not find host" in call.rendered


def test_ipconfig_shows_apipa_when_no_lease(env, log):
    env.world.machines["MER-WS-001"].ip = None
    call = NetworkTools().invoke(env, log, "ipconfig", {"from": "MER-WS-001"})
    assert "169.254." in call.rendered


def test_set_dns_is_mutating_and_takes_effect(env, log):
    call = NetworkTools().invoke(
        env, log, "set-dns", {"from": "MER-WS-001", "servers": "10.20.10.5"}
    )
    assert call.mutating is True
    assert env.world.machines["MER-WS-001"].dns_servers == ["10.20.10.5"]


def test_remote_session_reports_disk(env, log):
    env.world.machines["MER-WS-001"].disk_free_gb = 0.4
    call = RemoteSession().invoke(env, log, "inspect", {"host": "MER-WS-001"})
    assert "0.4" in call.rendered and call.mutating is False


def test_event_viewer_filters_by_log(env, log):
    call = EventViewer().invoke(
        env, log, "get", {"host": "MER-WS-001", "log": "System", "count": "5"}
    )
    assert call.ok


def test_printing_reports_driver_mismatch(env, log):
    env.world.machines["MER-WS-001"].printer_drivers["PRT-ACC-01"] = "Generic / Text Only"
    call = PrintManagement().invoke(
        env, log, "get-printer", {"printer": "PRT-ACC-01", "from": "MER-WS-001"}
    )
    assert "Generic / Text Only" in call.rendered


def test_restart_spooler_targets_the_workstation(env, log):
    env.world.machines["MER-WS-001"].services["Spooler"] = ServiceState.STOPPED
    call = PrintManagement().invoke(env, log, "restart-spooler", {"from": "MER-WS-001"})
    assert call.ok and call.mutating is True
    assert env.world.machines["MER-WS-001"].services["Spooler"] is ServiceState.RUNNING


def test_powershell_restart_service_is_mutating(env, log):
    env.world.machines["MER-WS-001"].services["Spooler"] = ServiceState.STOPPED
    call = PowerShellConsole().invoke(
        env, log, "Restart-Service", {"host": "MER-WS-001", "name": "Spooler"}
    )
    assert call.mutating is True
    assert env.world.machines["MER-WS-001"].services["Spooler"] is ServiceState.RUNNING


def test_powershell_matching_is_case_insensitive(env, log):
    call = PowerShellConsole().invoke(env, log, "get-service", {"host": "MER-WS-001"})
    assert call.ok and "Spooler" in call.rendered


def test_powershell_get_psdrive_reads_the_share(env, log):
    call = PowerShellConsole().invoke(env, log, "Get-PSDrive", {"host": "MER-WS-001", "name": "S:"})
    assert call.ok and "MER-FS-01" in call.rendered


def test_powershell_rejects_unknown_cmdlet(env, log):
    call = PowerShellConsole().invoke(env, log, "Invoke-Magic", {"host": "MER-WS-001"})
    assert call.ok is False and "not recognized" in call.rendered.lower()


def test_all_seven_tools_are_registered():
    assert {t.name for t in all_tools()} == {
        "ad", "net", "remote", "events", "print", "ps", "kb",
    }
    assert get_tool("net").name == "net"


def test_every_tool_advertises_its_commands():
    for tool in all_tools():
        assert tool.commands(), f"{tool.name} advertises no commands"
