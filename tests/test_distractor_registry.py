"""Unit coverage for the distractor protocol and registry.

The conformance harness in `test_distractors.py` is parametrized over the
catalog, which is deliberately empty until Task 4 — so without this file the
registry and the protocol would ship with nothing exercising them at all.

Every test here registers into an isolated registry via monkeypatch. Writing
into the real module dict would leak a fake distractor into the conformance
harness, whose results would then depend on test import order.
"""

from random import Random

import pytest

from vitsc.distractors import registry
from vitsc.distractors.base import Distractor
from vitsc.env.base import Query
from vitsc.faults.base import Placement
from vitsc.world.models import World


class StubDistractor:
    id = "stub.example"
    note = "A stub that does nothing at all."

    def placements(self, world: World) -> list[Placement]:
        return [Placement(kind="machine", key=sorted(world.machines)[0])]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        pass

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.state", target=at.key)]


@pytest.fixture
def clean_registry(monkeypatch):
    monkeypatch.setattr(registry, "_REGISTRY", {})
    return registry


def test_a_conforming_class_satisfies_the_protocol():
    """`Distractor` is runtime_checkable, so this is a real structural check."""
    assert isinstance(StubDistractor(), Distractor)


def test_a_class_missing_a_member_does_not_satisfy_the_protocol():
    class NotADistractor:
        id = "stub.incomplete"
        note = "Has no placements()."

    assert not isinstance(NotADistractor(), Distractor)


def test_register_returns_the_distractor(clean_registry):
    stub = StubDistractor()
    assert clean_registry.register_distractor(stub) is stub


def test_a_registered_distractor_is_retrievable(clean_registry):
    stub = StubDistractor()
    clean_registry.register_distractor(stub)
    assert clean_registry.get_distractor("stub.example") is stub


def test_duplicate_ids_are_rejected(clean_registry):
    """Two distractors sharing an id would make one of them unreachable."""
    clean_registry.register_distractor(StubDistractor())
    with pytest.raises(ValueError, match="duplicate distractor id"):
        clean_registry.register_distractor(StubDistractor())


def test_all_distractors_is_sorted_by_id(clean_registry):
    class Later(StubDistractor):
        id = "stub.zzz"

    clean_registry.register_distractor(Later())
    clean_registry.register_distractor(StubDistractor())
    assert [d.id for d in clean_registry.all_distractors()] == [
        "stub.example",
        "stub.zzz",
    ]


def test_the_catalog_is_not_empty():
    """Task 3 shipped the mechanism with an empty catalog on purpose; Task 4
    fills it. An empty catalog would silently skip every case in the
    conformance harness, so its non-emptiness is asserted out loud here."""
    assert registry.all_distractors() != []
