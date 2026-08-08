import pytest

from vitsc.env.base import Action, Query
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.world.models import ServiceState
from vitsc.world.seed import load_world


@pytest.fixture
def env():
    return SimulatedEnvironment(load_world())


def test_read_ad_user_returns_attributes(env):
    obs = env.read(Query(kind="ad.user", target="m.alvarez"))
    assert obs.ok
    assert obs.data["LockedOut"] is False
    assert "m.alvarez" in obs.rendered


def test_read_unknown_user_is_not_ok(env):
    obs = env.read(Query(kind="ad.user", target="nobody"))
    assert obs.ok is False
    assert "cannot be found" in obs.rendered.lower()


def test_unknown_query_kind_does_not_raise(env):
    assert env.read(Query(kind="quantum.flux", target="x")).ok is False
    assert env.execute(Action(kind="quantum.flux", target="x")).ok is False


def test_unlock_action_clears_lockout(env):
    env.world.org.users["m.alvarez"].locked_out = True
    result = env.execute(Action(kind="ad.unlock", target="m.alvarez"))
    assert result.ok
    assert env.world.org.users["m.alvarez"].locked_out is False


def test_reset_password_pushes_expiry_forward(env):
    user = env.world.org.users["m.alvarez"]
    user.pwd_expires = env.world.clock
    env.execute(Action(kind="ad.reset_password", target="m.alvarez"))
    assert user.pwd_expires > env.world.clock


def test_ping_by_hostname_resolves_when_dns_is_correct(env):
    obs = env.read(Query(kind="net.ping", target="MER-FS-01", args={"from": "MER-WS-001"}))
    assert obs.ok
    assert obs.data["resolved"] is True


def test_ping_by_hostname_fails_when_dns_is_wrong(env):
    env.world.machines["MER-WS-001"].dns_servers = ["10.20.10.99"]
    obs = env.read(Query(kind="net.ping", target="MER-FS-01", args={"from": "MER-WS-001"}))
    assert obs.ok is False
    assert obs.data["resolved"] is False


def test_ping_by_ip_still_works_with_wrong_dns(env):
    env.world.machines["MER-WS-001"].dns_servers = ["10.20.10.99"]
    obs = env.read(Query(kind="net.ping", target="10.20.10.6", args={"from": "MER-WS-001"}))
    assert obs.ok


def test_nslookup_times_out_against_a_dead_resolver(env):
    env.world.machines["MER-WS-001"].dns_servers = ["10.20.10.99"]
    obs = env.read(Query(kind="net.nslookup", target="MER-FS-01", args={"from": "MER-WS-001"}))
    assert obs.ok is False
    assert "timed-out" in obs.rendered


def test_ipconfig_reports_apipa_without_a_lease(env):
    env.world.machines["MER-WS-001"].ip = None
    obs = env.read(Query(kind="net.ipconfig", target="MER-WS-001"))
    assert obs.data["Autoconfigured"] is True
    assert "169.254." in obs.rendered


def test_renew_dhcp_restores_the_seeded_lease(env):
    env.world.machines["MER-WS-001"].ip = None
    result = env.execute(Action(kind="machine.renew_dhcp", target="MER-WS-001"))
    assert result.ok
    assert env.world.machines["MER-WS-001"].ip == "10.20.10.41"


def test_renew_dhcp_fails_on_a_static_machine(env):
    env.world.machines["MER-WS-001"].dhcp_enabled = False
    assert env.execute(Action(kind="machine.renew_dhcp", target="MER-WS-001")).ok is False


def test_share_access_requires_group_membership(env):
    ok_before = env.read(Query(kind="share.access", target="S:", args={"from": "MER-WS-001"}))
    assert ok_before.ok
    env.world.org.groups["ACC-Share-RW"].members.remove("m.alvarez")
    denied = env.read(Query(kind="share.access", target="S:", args={"from": "MER-WS-001"}))
    assert denied.ok is False
    assert "denied" in denied.rendered.lower()


def test_share_access_fails_on_broken_dns_before_permissions(env):
    env.world.machines["MER-WS-001"].dns_servers = ["10.20.10.99"]
    obs = env.read(Query(kind="share.access", target="S:", args={"from": "MER-WS-001"}))
    assert obs.data["reason"] == "dns"


def test_restart_service_sets_running(env):
    env.world.machines["MER-WS-001"].services["Spooler"] = ServiceState.STOPPED
    env.execute(
        Action(kind="machine.restart_service", target="MER-WS-001", args={"service": "Spooler"})
    )
    assert env.world.machines["MER-WS-001"].services["Spooler"] is ServiceState.RUNNING


def test_printer_state_reports_installed_versus_correct_driver(env):
    env.world.machines["MER-WS-001"].printer_drivers["PRT-ACC-01"] = "Generic / Text Only"
    obs = env.read(Query(kind="printer.state", target="PRT-ACC-01", args={"from": "MER-WS-001"}))
    assert obs.data["InstalledDriver"] == "Generic / Text Only"
    assert obs.data["CorrectDriver"] == "HP LaserJet M507 PCL-6"


def test_reinstall_driver_restores_the_correct_one(env):
    env.world.machines["MER-WS-001"].printer_drivers["PRT-ACC-01"] = "Generic / Text Only"
    env.execute(
        Action(kind="printer.reinstall_driver", target="PRT-ACC-01", args={"from": "MER-WS-001"})
    )
    assert (
        env.world.machines["MER-WS-001"].printer_drivers["PRT-ACC-01"]
        == "HP LaserJet M507 PCL-6"
    )


def test_clear_disk_caps_at_total_and_repairs_temp_profile(env):
    machine = env.world.machines["MER-WS-001"]
    machine.disk_free_gb = 0.3
    env.execute(Action(kind="machine.clear_disk", target="MER-WS-001", args={"gb": "9999"}))
    assert machine.disk_free_gb == machine.disk_total_gb


def test_snapshot_and_restore_round_trip(env):
    snap = env.snapshot()
    env.world.org.users["m.alvarez"].locked_out = True
    env.restore(snap)
    assert env.world.org.users["m.alvarez"].locked_out is False
