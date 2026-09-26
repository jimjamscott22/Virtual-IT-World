from random import Random

import pytest

from vitsc.env.base import Action
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import get_fault
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


# --- the mail pair, deferred from Phase 2a ------------------------------------


def test_deleting_a_mailbox_is_collateral_damage():
    world = load_world()
    baseline = capture_baseline(world)
    env = SimulatedEnvironment(world)
    env.execute(Action(kind="mail.remove_mailbox", target="m.alvarez"))
    assert check_invariants(env.world, baseline) == ["mailbox for m.alvarez was deleted"]


def test_setting_a_quota_below_current_usage_is_collateral_damage():
    world = load_world()
    baseline = capture_baseline(world)
    env = SimulatedEnvironment(world)
    used = world.mail.mailboxes["d.okafor"].used_mb
    env.execute(
        Action(kind="mail.set_quota", target="d.okafor", args={"quota_mb": str(used - 1)})
    )
    assert check_invariants(env.world, baseline) == [
        "mailbox quota for d.okafor was set below its current usage"
    ]


def test_an_over_quota_mailbox_in_the_baseline_is_never_reported_as_damage():
    """The capture-after-apply guarantee, for the mail pair specifically.

    `mail.mailbox_full` leaves its victim over quota *before* the baseline is
    taken. If the invariant compared quota against usage unconditionally, the
    fault would report itself as the technician's collateral damage the moment it
    landed — the exact defect `capture_baseline`'s `allowed_dns` field was fixed
    for in Phase 2a.
    """
    world = load_world()
    fault = get_fault("mail.mailbox_full")
    placement = fault.placements(world)[0]
    fault.apply(world, placement, Random(0))
    baseline = capture_baseline(world)
    assert check_invariants(world, baseline) == []


def test_raising_a_quota_to_clear_the_fault_is_not_damage():
    """One of `mail.mailbox_full`'s two canonical fixes moves a quota. Neither
    the movement nor its direction is what the invariant watches."""
    world = load_world()
    fault = get_fault("mail.mailbox_full")
    placement = fault.placements(world)[0]
    fault.apply(world, placement, Random(0))
    baseline = capture_baseline(world)
    env = SimulatedEnvironment(world)
    env.execute(
        Action(kind="mail.set_quota", target=placement.key, args={"quota_mb": "999999"})
    )
    assert fault.is_present(env.world, placement) is False
    assert check_invariants(env.world, baseline) == []
