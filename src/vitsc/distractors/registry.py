"""Distractor registration, mirroring `faults/registry.py`.

Kept separate from the fault registry rather than sharing one: the two have
different contracts and different conformance harnesses, and a single registry
would invite code that has to ask "is this one a real fault?" — which is the
special-casing the separate protocol exists to avoid.
"""

from vitsc.distractors.base import Distractor

_REGISTRY: dict[str, Distractor] = {}


def register_distractor(distractor: Distractor) -> Distractor:
    if distractor.id in _REGISTRY:
        raise ValueError(f"duplicate distractor id: {distractor.id}")
    _REGISTRY[distractor.id] = distractor
    return distractor


def all_distractors() -> list[Distractor]:
    # pylint: disable=import-outside-toplevel,unused-import
    import vitsc.distractors.catalog  # noqa: F401  — triggers registration

    return sorted(_REGISTRY.values(), key=lambda d: d.id)


def get_distractor(distractor_id: str) -> Distractor:
    all_distractors()
    return _REGISTRY[distractor_id]
