import pytest

from vitsc.world.invariants import capture_baseline, check_invariants
from vitsc.world.models import ServiceState
from vitsc.world.seed import load_world


@pytest.fixture
def world():
    return load_world()


def test_untouched_world_has_no_violations(world):
    assert check_invariants(world, capture_baseline(world)) == []


def test_disabling_an_account_is_a_violation(world):
    baseline = capture_baseline(world)
    world.org.users["m.alvarez"].enabled = False
    violations = check_invariants(world, baseline)
    assert any("m.alvarez" in v and "disabled" in v for v in violations)


def test_stopping_a_baseline_service_is_a_violation(world):
    baseline = capture_baseline(world)
    world.machines["MER-WS-001"].services["Spooler"] = ServiceState.STOPPED
    violations = check_invariants(world, baseline)
    assert any("Spooler" in v and "MER-WS-001" in v for v in violations)


def test_removing_group_membership_is_a_violation(world):
    baseline = capture_baseline(world)
    world.org.groups["ACC-Share-RW"].members.remove("m.alvarez")
    violations = check_invariants(world, baseline)
    assert any("ACC-Share-RW" in v and "m.alvarez" in v for v in violations)


def test_foreign_dns_is_a_violation(world):
    baseline = capture_baseline(world)
    world.machines["MER-WS-001"].dns_servers = ["1.1.1.1"]
    violations = check_invariants(world, baseline)
    assert any("1.1.1.1" in v for v in violations)


def test_dns_the_fault_already_set_is_not_a_violation(world):
    """The capture-after-apply guarantee has to hold for DNS like everything else.

    `net.static_dns_misconfig` points a machine at a server the network config
    does not list. If the baseline only trusted `network.dns_servers`, the
    fault would show up as the technician's own collateral damage.
    """
    world.machines["MER-WS-001"].dns_servers = ["10.20.10.99"]
    baseline = capture_baseline(world)
    assert check_invariants(world, baseline) == []
    world.machines["MER-WS-002"].dns_servers = ["1.1.1.1"]
    assert any("1.1.1.1" in v for v in check_invariants(world, baseline))


def test_restarting_a_service_the_fault_stopped_is_not_a_violation(world):
    world.machines["MER-WS-001"].services["Spooler"] = ServiceState.STOPPED
    baseline = capture_baseline(world)
    world.machines["MER-WS-001"].services["Spooler"] = ServiceState.RUNNING
    assert check_invariants(world, baseline) == []
