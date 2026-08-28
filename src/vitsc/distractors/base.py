"""Honest distractors.

A distractor is a real, truthfully-reported anomaly that is never the cause of
a ticket (spec §4). It exists so the first oddity a technician finds is not
automatically the answer — a real queue is full of harmless noise, and the
skill being drilled is telling noise from cause.

Note what is *absent* compared to `Fault`: no `is_present`, no `symptoms`, no
`canonical_resolutions`, no `escalation_is_correct`. A distractor is never
diagnosed, never reported, never graded and never fixed — so it needs none of
that, and having none of it is what keeps the scheduler, grading and the
after-action from having to special-case it. A `Fault` with an
`is_ticketable = False` flag would have to be excluded in five separate
places, each of which could forget.

The whole contract is the non-interference guarantee, and it is enforced
mechanically in `tests/test_distractors.py` rather than by convention: a
distractor may never change whether any registered fault is present, and must
be visible through at least one query that a clean world answers differently.
"""

from random import Random
from typing import Protocol, runtime_checkable

from vitsc.env.base import Query
from vitsc.faults.base import Placement
from vitsc.world.models import World


@runtime_checkable
class Distractor(Protocol):
    id: str
    note: str  # plain-English description, for the after-action

    def placements(self, world: World) -> list[Placement]: ...
    def apply(self, world: World, at: Placement, rng: Random) -> None: ...
    def visible_through(self, at: Placement) -> list[Query]: ...
