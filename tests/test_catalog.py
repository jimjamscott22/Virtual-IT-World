"""Conformance harness for the whole fault catalog.

The failure mode of this design is an unsolvable or unfair ticket. Every
fault registered anywhere is proven here — placeable, discoverable, solvable
by each canonical path, and free of jargon in its symptoms — the moment it
registers, with no per-fault test to write.
"""

from random import Random

import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.base import bind, bind_query
from vitsc.faults.registry import all_faults
from vitsc.world.invariants import capture_baseline, check_invariants
from vitsc.world.seed import load_world

JARGON = {
    "dns", "dhcp", "active directory", "group policy", "spooler", "smart",
    "driver", "subnet", "apipa", "lockout", "gpo", "registry", "wmi",
}


def fault_cases():
    for fault in all_faults():
        for placement in fault.placements(load_world()):
            yield pytest.param(fault, placement, id=f"{fault.id}@{placement.key}")


CASES = list(fault_cases())


def test_the_catalog_is_not_empty():
    assert all_faults()


@pytest.mark.parametrize("fault,placement", CASES)
def test_fault_conforms(fault, placement):
    world = load_world()

    # 1. Absent before, present after.
    assert fault.is_present(world, placement) is False
    fault.apply(world, placement, Random(0))
    assert fault.is_present(world, placement) is True

    # 2. Discoverable: the declared diagnostic path reports something.
    env = SimulatedEnvironment(world)
    path = fault.diagnostic_path(placement)
    assert path, f"{fault.id} declares no diagnostic path"
    assert any(env.read(bind_query(q, placement, world)).rendered for q in path)

    # 3. Every canonical resolution clears it, invariants intact.
    if fault.escalation_is_correct and not fault.canonical_resolutions():
        return  # escalate-only faults have no technician fix by design
    assert fault.canonical_resolutions(), f"{fault.id} declares no resolution"
    for resolution in fault.canonical_resolutions():
        broken = load_world()
        fault.apply(broken, placement, Random(0))
        scoped = SimulatedEnvironment(broken)
        baseline = capture_baseline(broken)
        for action in bind(resolution, placement, broken).actions:
            result = scoped.execute(action)
            assert result.ok, (
                f"{fault.id}: resolution '{resolution.label}' action "
                f"{action.kind} failed: {result.rendered}"
            )
        assert fault.is_present(scoped.world, placement) is False, (
            f"{fault.id}: resolution '{resolution.label}' did not clear the fault"
        )
        assert check_invariants(scoped.world, baseline) == [], (
            f"{fault.id}: resolution '{resolution.label}' caused collateral damage"
        )


@pytest.mark.parametrize("fault,placement", CASES)
def test_symptoms_do_not_leak(fault, placement):
    world = load_world()
    fault.apply(world, placement, Random(0))
    symptoms = fault.symptoms(world, placement)
    blob = " ".join(
        filter(None, [symptoms.opening, symptoms.onset, symptoms.error_text, symptoms.scope])
    ).lower()
    for term in fault.leak_terms:
        assert term.lower() not in blob, f"{fault.id} symptoms leak '{term}'"
    for term in JARGON:
        assert term not in blob, f"{fault.id} symptoms contain jargon '{term}'"


@pytest.mark.parametrize("fault,placement", CASES)
def test_discoverability_actually_differs(fault, placement):
    """A fault must change at least one observation, or it is invisible."""
    clean = SimulatedEnvironment(load_world())
    broken_world = load_world()
    fault.apply(broken_world, placement, Random(0))
    broken = SimulatedEnvironment(broken_world)
    path = fault.diagnostic_path(placement)
    assert any(
        clean.read(bind_query(q, placement, clean.world)).rendered
        != broken.read(bind_query(q, placement, broken.world)).rendered
        for q in path
    ), f"{fault.id}@{placement.key} is not observable via its diagnostic path"


def test_fault_ids_are_unique_and_namespaced():
    ids = [f.id for f in all_faults()]
    assert len(ids) == len(set(ids))
    assert all("." in fault_id for fault_id in ids)


def test_every_fault_declares_a_backend_and_a_difficulty():
    for fault in all_faults():
        assert fault.supported_backends, f"{fault.id} supports no backend"
        assert 1 <= fault.difficulty <= 5, f"{fault.id} has an out-of-range difficulty"


def test_v1_catalog_is_complete():
    """The ten v1 faults, plus Task 7's cascade fault — the first Phase 2a
    addition to this set."""
    ids = {f.id for f in all_faults()}
    assert ids == {
        "ad.account_locked", "ad.password_expired", "ad.offboarded_reactivation",
        "share.group_membership_removed", "print.spooler_stopped", "print.wrong_driver",
        "print.server_spooler_stopped",
        "net.static_dns_misconfig", "net.no_dhcp_lease",
        "endpoint.disk_full", "endpoint.failing_disk",
    }


def test_exactly_two_faults_are_escalate_correct():
    escalate = {f.id for f in all_faults() if f.escalation_is_correct}
    assert escalate == {"ad.offboarded_reactivation", "endpoint.failing_disk"}
