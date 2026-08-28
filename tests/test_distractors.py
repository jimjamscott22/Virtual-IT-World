"""Conformance harness for the whole distractor catalog.

Mirrors `tests/test_catalog.py`, but proves a different contract. A fault has
to be solvable; a distractor has to be *honest*: real, visible, truthfully
reported, and never the cause of the ticket in front of you. The dangerous
failure mode here is a "distractor" that quietly fixes or breaks a fault, so
the first oddity a technician finds turns out to be the answer after all —
which would teach exactly the habit the drill exists to break.

Every distractor registered anywhere is proven here the moment it registers,
with no per-distractor test to write.
"""

from random import Random

import pytest

# Registration is triggered by `all_distractors()` itself, exactly as
# `all_faults()` does for the fault catalog — no import needed here.
from vitsc.distractors.registry import all_distractors
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.base import bind
from vitsc.faults.registry import all_faults
from vitsc.world.invariants import capture_baseline, check_invariants
from vitsc.world.seed import load_world


def cases():
    world = load_world()
    return [
        pytest.param(d, at, id=f"{d.id}@{at.key}")
        for d in all_distractors()
        for at in d.placements(world)
    ]


CASES = cases()


@pytest.mark.parametrize("distractor,at", CASES)
def test_distractor_never_flips_a_fault(distractor, at):
    """The honesty guarantee: a distractor is real, visible, and never a cause."""
    world = load_world()
    before = {
        (f.id, p.key): f.is_present(world, p)
        for f in all_faults()
        for p in f.placements(world)
    }
    distractor.apply(world, at, Random(0))
    for f in all_faults():
        for p in f.placements(world):
            key = (f.id, p.key)
            if key in before:
                assert f.is_present(world, p) == before[key], (
                    f"{distractor.id} at {at.key} changed {f.id} at {p.key}"
                )


@pytest.mark.parametrize("distractor,at", CASES)
def test_distractor_is_invariant_clean(distractor, at):
    """Seeded before the baseline, a distractor is inherited world state."""
    world = load_world()
    distractor.apply(world, at, Random(0))
    assert check_invariants(world, capture_baseline(world)) == []


@pytest.mark.parametrize("distractor,at", CASES)
def test_distractor_is_visible_through_a_tool(distractor, at):
    """An invisible distractor distracts nobody."""
    clean = SimulatedEnvironment(load_world())
    world = load_world()
    distractor.apply(world, at, Random(0))
    dirty = SimulatedEnvironment(world)

    seen = [
        (dirty.read(q).rendered, clean.read(q).rendered)
        for q in distractor.visible_through(at)
    ]
    assert seen, f"{distractor.id} declares no visible query"
    assert any(d != c for d, c in seen), f"{distractor.id} at {at.key} shows nothing"


@pytest.mark.parametrize("distractor,at", CASES)
def test_distractor_does_not_break_a_canonical_fix(distractor, at):
    """A seeded anomaly must not make a legitimate repair fail."""
    world = load_world()
    distractor.apply(world, at, Random(0))
    env = SimulatedEnvironment(world)
    for fault in all_faults():
        for p in fault.placements(env.world):
            if fault.is_present(env.world, p):
                continue
            snapshot = env.snapshot()
            fault.apply(env.world, p, Random(0))
            baseline = capture_baseline(env.world)
            # One resolution per fault is enough here: every path is already
            # proven in tests/test_catalog.py, and what this asserts is that
            # the distractor did not get in the way of a repair. The full
            # cross-product would multiply the suite for no extra signal.
            for resolution in fault.canonical_resolutions()[:1]:
                for action in bind(resolution, p, env.world).actions:
                    env.execute(action)
                assert not fault.is_present(env.world, p)
                assert check_invariants(env.world, baseline) == []
            env.restore(snapshot)
